import sqlite3
import json
import os

# don't use matplotlib gui
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from collections import defaultdict
from datetime import datetime
from tempfile import NamedTemporaryFile

from slackbot.bot import respond_to, default_reply

BOT_NAME = 'crossbot'
DB_NAME = 'crossbot.db'

time_rx = r'(\d*):(\d\d)'
date_rx = r'(\d\d\d\d-\d\d-\d\d)|now'

def opt(rx):
    '''Returns a regex that optionally accepts the input with leading
    whitespace.'''
    return '(?: +{})?'.format(rx)

@respond_to('help *$')
def help(message):
    '''Get help.'''
    s = [
        'You can either @ me in a channel or just DM me to give me a command.',
        'Play here: https://www.nytimes.com/crosswords/game/mini',
        'I live here: https://github.com/mwillsey/crossbot',
        'Times look like this `1:30` or this `:32` (the `:` is necessary).',
        'Dates look like this `2017-05-05` or simply `now` for today.',
        'Here are my commands:\n\n',
    ]
    message.send('\n'.join(s) + message.docs_reply())


@respond_to('add {}{} *$'.format(time_rx, opt(date_rx)))
def add(message, minutes, seconds, date):
    '''Add entry for today (`add 1:07`) or given date (`add :32 2017-05-05`).'''

    if minutes is None or minutes == '':
        minutes = 0
    if date is None:
        date = 'now'

    total_seconds = int(minutes) * 60 + int(seconds)
    userid = message._get_user_id()

    # try to add an entry, report back to the user if they already have one
    with sqlite3.connect(DB_NAME) as con:
        try:
            con.execute('''
            INSERT INTO crossword_time(userid, date, seconds)
            VALUES(?, date(?, 'start of day'), ?)
            ''', (userid, date, total_seconds))

        except sqlite3.IntegrityError:
            seconds = con.execute('''
            SELECT seconds
            FROM crossword_time
            WHERE userid = ? and date = date(?, 'start of day')
            ''', (userid, date)).fetchone()

            minutes, seconds = divmod(seconds[0], 60)

            message.reply('I could not add this to the database, '
                          'because you already have an entry '
                          '({}:{:02d}) for this date.'.format(minutes, seconds))
            return

    if total_seconds < 30:
        emoji = 'fire'
    elif total_seconds < 90:
        emoji = 'ok'
    else:
        emoji = 'slowpoke'

    message.react(emoji)


@respond_to('delete{} *$'.format(opt(date_rx)))
def delete(message, date):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    if date is None:
        date = 'now'

    userid = message._get_user_id()

    with sqlite3.connect(DB_NAME) as con:
        con.execute('''
        DELETE FROM crossword_time
        WHERE userid=? AND date=date(?, 'start of day')
        ''', (userid, date))

    message.react('x')

@respond_to('times{}'.format(opt(date_rx)))
def times(message, date):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    if date is None:
        date = 'now'

    response = ''

    with sqlite3.connect(DB_NAME) as con:
        cursor = con.execute('''
        SELECT userid, seconds
        FROM crossword_time
        WHERE date = date(?, 'start of day')
        ORDER BY seconds''', (date,))

        users = message._client.users
        for userid, seconds in cursor:
            minutes, seconds = divmod(seconds, 60)
            name = users[userid]['name']
            response += '{} - {}:{:02d}\n'.format(name, minutes, seconds)

    if len(response) == 0:
        if date == 'now':
            response = 'No times yet for today, be the first!'
        else:
            response = 'No times for this date.'
    message.send(response)

@respond_to('announce{}'.format(opt(date_rx)))
def send_daily_message(message, date):
    if date is None:
        date = 'now'

    with sqlite3.connect(DB_NAME) as con:
        cursor = con.execute('''
        SELECT userid, seconds
        FROM crossword_time
        WHERE date = date(?, 'start of day', '-1 days')
        ORDER BY seconds
        LIMIT 1''', (date,));

        try:
            userid, seconds = next(cursor)
        except StopIteration:
            return message.send("No one played the minicrossword yesterday. Why not?")

        username = message._client.users[userid]["name"]

        cursor = con.execute('''
        SELECT userid, date
        FROM crossword_time
        WHERE userid != ?
        ORDER BY date DESC
        LIMIT 1''', (userid,))

        try:
            previous, when = next(cursor)
        except StopIteration:
            return message.send("Looks like only {} has been fastest at the minicrossword. The rest of y'all gotta step up your game!".format(username))

        # Formatting the response
        m_winner = "Yesterday, {} solved the minicrossword fastest. ".format(username)

        streak = datetime.now().date() - datetime.strptime(when, "%Y-%m-%d").date()

        if streak.days > 1:
            m_streak = "They're on a {}-day streak!".format(username, streak.days)
        else:
            m_streak = "But {} won the day before. Can they retake the top spot?".format(message._client.users[previous]["name"])

        m_url = "Play today's minicrossword at https://www.nytimes.com/crosswords/game/mini and tell me how you do :)"

        message.send(m_winner + "\n" + m_streak + "\n" + m_url)

@respond_to('plot{}{}'.format(opt(date_rx), opt(date_rx)))
def plot(message, start_date, end_date):
    '''Plot everyone's times in a date range. `plot` plots the last week.
    `plot [start date]` and `plot [start date] [end date]` do the obvious thing.'''

    if end_date is None:
        end_date = 'now'

    start_modifer = ''
    if start_date is None:
        start_date = 'now'
        start_modifer = '-7 days'


    with sqlite3.connect(DB_NAME) as con:
        cursor = con.execute('''
        SELECT userid, date, seconds
        FROM crossword_time
        WHERE date
          BETWEEN date(?, 'start of day', ?)
          AND     date(?, 'start of day')
        ORDER BY date''', (start_date, start_modifer, end_date))

        times = defaultdict(list)
        for userid, date, seconds in cursor:
            times[userid].append((date, seconds))

    users = message._client.users

    width, height, dpi = 400, 300, 100
    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax = fig.add_subplot(1,1,1)

    def fmt_min(sec, pos):
        minutes, seconds = divmod(int(sec), 60)
        return '{}:{:02}'.format(minutes, seconds)

    for userid, entries in times.items():

        dates, seconds = zip(*entries)
        dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
        name = users[userid]['name']
        ax.plot_date(mdates.date2num(dates), seconds, '-o', label=name)

    fig.autofmt_xdate()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %-d')) # May 3
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt_min)) # 1:30
    ax.set_ylim(ymin=0)
    ax.legend()

    temp = NamedTemporaryFile(suffix='.png', delete=False)
    fig.savefig(temp, format='png')
    temp.close()

    message.channel.upload_file('plot', temp.name)

    os.remove(temp.name)
