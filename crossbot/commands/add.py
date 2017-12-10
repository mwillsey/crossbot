import sqlite3
import math

from random import choice
from datetime import datetime, timedelta

import crossbot
from crossbot.parser import date_fmt


def init(client):

    parser = client.parser.subparsers.add_parser('add', help='Add a time.')
    parser.set_defaults(command=add)

    parser.add_argument(
        'time',
        type    = crossbot.time,
        help    = 'Score to add. eg. ":32", "2:45", "fail"')

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to add a score for.')

    # TODO add a command-line only --user parameter


def add(client, request):
    '''Add entry for today (`add 1:07`) or given date (`add :32 2017-05-05`).
       A zero second time will be interpreted as a failed attempt.'''

    args = request.args

    # try to add an entry, report back to the user if they already have one
    with sqlite3.connect(crossbot.db_path) as con:
        try:
            query = '''
            INSERT INTO {}(userid, date, seconds)
            VALUES(?, date(?), ?)
            '''.format(args.table)

            con.execute(query, (request.userid, args.date, args.time))

        except sqlite3.IntegrityError:
            query = '''
            SELECT seconds
            FROM {}
            WHERE userid = ? and date = date(?)
            '''.format(args.table)
            seconds = con.execute(query, (request.userid, args.date)).fetchone()

            minutes, seconds = divmod(args.time, 60)

            request.reply('I could not add this to the database, '
                          'because you already have an entry '
                          '({}:{:02d}) for this date.'.format(minutes, seconds),
                          direct=True)
            return

    with sqlite3.connect(crossbot.db_path) as con:
        cur = con.execute("select strftime('%w', ?)", (args.date,))
        day_of_week = int(cur.fetchone()[0])

    request.react(emoji(args.time, args.table, day_of_week))

    # get all the entries for this person
    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT date
        FROM {}
        WHERE userid = ?
        '''.format(args.table)

        result = con.execute(query, (request.userid,))

        dates_completed = set(tup[0] for tup in result)

    # calculate the backwards streak
    check_date = datetime.strptime(args.date, date_fmt)
    back_streak_count = 0
    while check_date.strftime(date_fmt) in dates_completed:
        back_streak_count += 1
        check_date -= timedelta(days=1)

    # calculate the forwards streak
    check_date = datetime.strptime(args.date, date_fmt)
    forward_streak_count = 0
    while check_date.strftime(date_fmt) in dates_completed:
        forward_streak_count += 1
        check_date += timedelta(days=1)

    # the previous streak count this user had was the max of the forward and back
    # the new one is the sum - 1 (this date is double counted)
    # so give them every streak award between the two
    old_sc = max(back_streak_count, forward_streak_count)
    new_sc = back_streak_count + forward_streak_count
    for streak_count in range(old_sc, new_sc):
        streak_messages = STREAKS.get(streak_count)
        if streak_messages:
            name = client.user(request.userid)
            msg = choice(streak_messages).format(name=name)
            try:
                # try here because we might fail if the reaction already exists.
                request.react("achievement")
            except:
                print("Achievement reaction failed!")
            request.reply(msg)

# STREAKS[streak_num] = list of messages with {name} format option
STREAKS = {
    1:   ["First one in a while, {name}.",
          "Try it every day, {name}." ],
    3:   ["3 entries in a row! Keep it up {name}!",
          "Nice work, 3 in a row!"],
    10:  ["{name}'s on a streak of 10 entries, way to go!"],
    25:  [":open_mouth:, 25 days in a row!"],
    50:  ["50 in a row, here's a medal :sports_medal:!"],
    100: ["{name}'s done 100 crosswords in a row! They deserve a present :present:!"],
    150: ["{name}'s on a streak of 150 days... impressive!"],
    200: ["200 days in a row!?! Wow! Great work {name}!"],
}


# (fast_time, slow_time) for each day
MINI_TIMES = [
    (15, 3 * 60 + 30), # Sunday
    (15, 3 * 60 + 30), # Monday
    (15, 3 * 60 + 30), # Tuesday
    (15, 3 * 60 + 30), # Wednesday
    (15, 3 * 60 + 30), # Thursday
    (15, 3 * 60 + 30), # Friday
    (30, 5 * 60 + 30), # Saturday
]


REGULAR_TIMES = [
    (45 * 60, 120 * 60), # Sunday
    ( 5 * 60,  15 * 60), # Monday
    (10 * 60,  30 * 60), # Tuesday
    (15 * 60,  45 * 60), # Wednesday
    (30 * 60,  60 * 60), # Thursday
    (30 * 60,  60 * 60), # Friday
    (45 * 60, 120 * 60), # Saturday
]


SUDOKU_TIMES = [
    (60, 10 * 60), # Sunday
    (60, 10 * 60), # Monday
    (60, 10 * 60), # Tuesday
    (60, 10 * 60), # Wednesday
    (60, 10 * 60), # Thursday
    (60, 10 * 60), # Friday
    (60, 10 * 60), # Saturday
]


# possible reactions sorted by speed
# if these aren't in Slack, crossbot will crash
SPEED_EMOJI = [
    'fire',
    'hot_pepper',
    'rockon',
    'rocket',
    'nicer',
    'fastparrot',
    'fistv',
    'thumbsup',
    'ok',
    'slowparrot',
    'slow',
    'slowpoke',
    'waiting',
    'turtle',
    'snail',
    'zzz',
    'rip',
    'poop',
]


def emoji(time, table, day_of_week):

    if table == crossbot.tables['mini']:
        times_list = MINI_TIMES
    elif table == crossbot.tables['regular']:
        times_list = REGULAR_TIMES
    elif table == crossbot.tables['sudoku']:
        times_list = SUDOKU_TIMES
    else:
        raise RuntimeError('Unknown table {}'.format(table))

    fast_time, slow_time = times_list[day_of_week]
    assert fast_time < slow_time

    if time < 0:
        return 'facepalm'
    if time < fast_time:
        return SPEED_EMOJI[0]
    if time > slow_time:
        return SPEED_EMOJI[-1]

    last_emoji = len(SPEED_EMOJI) - 2

    speed = time - fast_time
    time_range = slow_time - fast_time
    ratio = (speed / time_range) ** 0.8
    index = int(math.ceil(ratio * last_emoji))

    index = min(index, last_emoji)

    assert index in range(len(SPEED_EMOJI))

    return SPEED_EMOJI[index]
