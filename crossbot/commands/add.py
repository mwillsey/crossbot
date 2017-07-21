import sqlite3
import math

import crossbot


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


# (fast_time, slow_time) for each day
MINI_TIMES = [
    (15, 2 * 60 + 30), # Sunday
    (15, 2 * 60 + 30), # Monday
    (15, 2 * 60 + 30), # Tuesday
    (15, 2 * 60 + 30), # Wednesday
    (15, 2 * 60 + 30), # Thursday
    (15, 2 * 60 + 30), # Friday
    (30, 4 * 60 + 30), # Saturday
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
    'poop',
]


def emoji(time, table, day_of_week):

    if table == crossbot.tables['mini']:
        times_list = MINI_TIMES
    elif table == crossbot.tables['regular']:
        times_list = REGULAR_TIMES
    else:
        raise RuntimeError('Unknown table {}'.format(table))

    fast_time, slow_time = times_list[day_of_week]
    assert fast_time < slow_time

    if time < 0:
        return 'facepalm'
    if time < fast_time:
        return SPEED_EMOJI[0]

    speed = time - fast_time
    time_range = slow_time - fast_time
    index = speed / time_range * len(SPEED_EMOJI)
    index = int(math.ceil(index))

    if index >= len(SPEED_EMOJI):
        index = len(SPEED_EMOJI) - 1

    assert index in range(len(SPEED_EMOJI))

    return SPEED_EMOJI[index]
