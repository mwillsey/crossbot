import sqlite3
import json
import os
import statistics

# don't use matplotlib gui
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import datetime, pytz
from collections import defaultdict
from itertools import takewhile, cycle
from tempfile import NamedTemporaryFile

from slackbot.bot import respond_to, default_reply

BOT_NAME = 'crossbot'
DB_NAME = 'crossbot.db'

time_rx = r'(\d*):(\d\d)'
date_rx = r'(?:(\d\d\d\d-\d\d-\d\d)|now)'

def opt(rx):
    '''Returns a regex that optionally accepts the input with leading
    whitespace.'''
    return '(?: +{})?'.format(rx)

TZ_US_EAST = pytz.timezone('US/Eastern')

def get_date(date):
    '''If date is a date, this does nothing. If it's 'now' or None, then this
    gets either today's date or tomorrow's if the crossword has already come
    out (10pm on weekdays, 6pm on weekends)'''

    if date is None or date == 'now':

        e_dt = datetime.datetime.now(TZ_US_EAST)
        dt = datetime.datetime.now()

        release_hour = 22 if e_dt.weekday() < 5 else 18

        # if it's already been released (with a small buffer), use tomorrow
        if e_dt.time() > datetime.time(hour=release_hour, minute=5):
            dt += datetime.timedelta(days=1)

        date = dt.strftime("%Y-%m-%d")

    return date


@respond_to('help *$')
def help(message):
    '''Get help.'''
    s = [
        'You can either @ me in a channel or just DM me to give me a command.',
        'Play here: https://www.nytimes.com/crosswords/game/mini',
        'I live here: https://github.com/mwillsey/crossbot',
        'Times look like this `1:30` or this `:32` (the `:` is necessary).',
        'Dates look like this `2017-05-05` or simply `now` for today.',
        '`now` or omitted dates will automatically become tomorrow if the'
        'crossword has already been released (10pm weekdays, 6pm weekends).'
        'Here are my commands:\n\n',
    ]
    message.send('\n'.join(s) + message.docs_reply())


@respond_to('add {}{} *$'.format(time_rx, opt(date_rx)))
def add(message, minutes, seconds, date):
    '''Add entry for today (`add 1:07`) or given date (`add :32 2017-05-05`).'''

    if minutes is None or minutes == '':
        minutes = 0
    date = get_date(date)

    total_seconds = int(minutes) * 60 + int(seconds)
    userid = message._get_user_id()

    # try to add an entry, report back to the user if they already have one
    with sqlite3.connect(DB_NAME) as con:
        try:
            con.execute('''
            INSERT INTO crossword_time(userid, date, seconds)
            VALUES(?, date(?), ?)
            ''', (userid, date, total_seconds))

        except sqlite3.IntegrityError:
            seconds = con.execute('''
            SELECT seconds
            FROM crossword_time
            WHERE userid = ? and date = date(?)
            ''', (userid, date)).fetchone()

            minutes, seconds = divmod(seconds[0], 60)

            message.reply('I could not add this to the database, '
                          'because you already have an entry '
                          '({}:{:02d}) for this date.'.format(minutes, seconds))
            return

    with sqlite3.connect(DB_NAME) as con:
        cur = con.execute("select strftime('%w', ?)", (date,))
        day_of_week = int(cur.fetchone()[0])

    if day_of_week == 6: # Saturday is longer
        fast_time = 90
        ok_time = 150
    else:
        fast_time = 30
        ok_time = 90

    if total_seconds < fast_time:
        emoji = 'fire'
    elif total_seconds < ok_time:
        emoji = 'ok'
    else:
        emoji = 'slowpoke'

    message.react(emoji)


@respond_to('delete{} *$'.format(opt(date_rx)))
def delete(message, date):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    date = get_date(date)

    userid = message._get_user_id()

    with sqlite3.connect(DB_NAME) as con:
        con.execute('''
        DELETE FROM crossword_time
        WHERE userid=? AND date=date(?)
        ''', (userid, date))

    message.react('x')

@respond_to('times{} *$'.format(opt(date_rx)))
def times(message, date):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    date = get_date(date)

    response = ''

    with sqlite3.connect(DB_NAME) as con:
        cursor = con.execute('''
        SELECT userid, seconds
        FROM crossword_time
        WHERE date = date(?)
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
def announce(message, date):
    '''Report who won the previous day and if they're on a streak.
    Optionally takes a date.'''
    date = get_date(date)

    m = ""

    users = message._client.users

    with sqlite3.connect(DB_NAME) as con:

        def best(offset):
            offset_s = '-{} days'.format(offset)
            result = con.execute('''
            SELECT userid
            FROM crossword_time
            WHERE date = date(?, ?)
            ORDER BY seconds ASC
            LIMIT 1''', (date, offset_s)).fetchone()

            return None if result is None else result[0]

        best1 = best(1)
        best2 = best(2)

        if best1 is None:
            m += 'No one played the minicrossword yesterday. Why not?\n'
        elif best1 != best2:
            # no streak
            m += 'Yesterday, {} solved the minicrossword fastest.\n'\
                 .format(users[best1]['name'])
            if best2 is not None:
                m += '{} won the day before.\n'\
                     .format(users[best2]['name'])
        else:
            n = 2
            while best(n+1) == best1: n += 1
            m += '{} is on a {}-day streak! {}\n'\
                 .format(users[best1]['name'], n, ':fire:' * n)

        m += "Play today's: https://www.nytimes.com/crosswords/game/mini"

        message.send(m)

@respond_to('plot{}{}{}{}{}'
            .format(opt(r'(normalized|times)'),
                    opt(r'(\d+)'), opt(r'(log|linear)'),
                    opt(date_rx), opt(date_rx)))
def plot(message, plot_type, num_days, scale, start_date, end_date):
    '''Plot everyone's times in a date range.
    `plot [plot_type] [num_days] [scale] [start date] [end date]`, all arguments optional.
    `plot_type` is either `normalized` (default) or `times` for a non-smoothed plot of actual times.
    You can provide either `num_days` or `start_date` and `end_date`.
    `plot` plots the last 5 days by default.
    The scale can be `log` (default) or `linear`.'''

    start_date = get_date(start_date)
    end_date   = get_date(end_date)

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt   = datetime.datetime.strptime(end_date,   "%Y-%m-%d").date()

    num_days = 5 if num_days is None else int(num_days)

    # we only use num_days if the other params weren't given
    # otherwise set num_days based the given range
    if start_date == end_date:
        start_dt -= datetime.timedelta(days=num_days)
        start_date = start_dt.strftime("%Y-%m-%d")
    else:
        num_days = (end_dt - start_dt).days

    if plot_type is None:
        plot_type = 'normalized'

    if scale is None:
        scale = 'linear' if plot_type == 'normalized' else 'log'

    with sqlite3.connect(DB_NAME) as con:
        cursor = con.execute('''
        SELECT userid, date, seconds
        FROM crossword_time
        WHERE date
          BETWEEN date(?)
          AND     date(?)
        ORDER BY date, userid''', (start_date, end_date))

        userids_present = set()

        times = defaultdict(list)
        times_by_date = defaultdict(dict)
        for userid, date, seconds in cursor:
            userids_present.add(userid)
            times[userid].append((date, seconds))
            times_by_date[date][userid] = seconds

    users = message._client.users

    if plot_type == 'normalized':
        sorted_dates = sorted(times_by_date.keys())

        def bracket(x):
            return max(-1.5, min(x, 1.5))

        # scores are the stdev away from mean of that day
        scores = {}
        for date, user_times in times_by_date.items():
            times = user_times.values()
            mean  = statistics.mean(times)
            stdev = statistics.pstdev(times)
            scores[date] = {
                userid: bracket((mean - t) / stdev)
                if stdev != 0 else 0
                for userid, t in user_times.items()
            }

        running = defaultdict(list)

        NUM_DAYS = 4
        weighted_scores = defaultdict(list)
        for date in sorted_dates:
            for user, score in scores[date].items():

                score_list = running[user]
                score_list.append(score)

                if len(score_list) == 0:
                    continue

                avg = statistics.mean(score_list[-NUM_DAYS:])
                weighted_scores[user].append((date, avg))


    width, height, dpi = (120*num_days), 400, 100
    width = max(400, min(width, 1000))

    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax = fig.add_subplot(1,1,1)
    ax.set_yscale(scale)

    def fmt_min(sec, pos):
        minutes, seconds = divmod(int(sec), 60)
        return '{}:{:02}'.format(minutes, seconds)

    cmap = plt.get_cmap('nipy_spectral')
    markers = cycle(['-o', '-X', '-s', '-^'])

    if plot_type == 'normalized':
        n_users = len(weighted_scores)
        colors = [cmap(i / n_users) for i in range(n_users)]
        for (userid, pairs), color in zip(weighted_scores.items(), colors):
            dates, scores = zip(*pairs)
            dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
            name = users[userid]['name']
            ax.plot_date(mdates.date2num(dates), scores, next(markers), label=name, color=color)

    elif plot_type == 'times':
        max_sec = 0
        n_users = len(times)
        colors = [cmap(i / n_users) for i in range(n_users)]
        for (userid, entries), color in zip(times.items(), colors):

            dates, seconds = zip(*entries)
            max_sec = max(max_sec, max(seconds))
            dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
            name = users[userid]['name']
            ax.plot_date(mdates.date2num(dates), seconds, next(markers), label=name, color=color)

        if scale == 'log':
            ticks = takewhile(lambda x: x <= max_sec, (30 * (2**i) for i in range(10)))
            ax.yaxis.set_ticks(list(ticks))
        else:
            ax.yaxis.set_ticks(range(0, max_sec+1, 30))

        ax.set_ylim(bottom=0)

    else:
        raise RuntimeError('invalid plot_type {}'.format(plot_type))

    fig.autofmt_xdate()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %-d')) # May 3
    if plot_type == 'times':
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt_min)) # 1:30
    ax.legend(fontsize=8, loc='upper left')

    temp = NamedTemporaryFile(suffix='.png', delete=False)
    fig.savefig(temp, format='png', bbox_inches='tight')
    temp.close()

    message.channel.upload_file('plot', temp.name)

    os.remove(temp.name)
