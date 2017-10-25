import sqlite3

import crossbot
from crossbot.commands.add import emoji

def init(client):

    parser = client.parser.subparsers.add_parser('times', help='show times')
    parser.set_defaults(command= times)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to get times for.')


def times(client, request):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    response = ''
    failures = ''

    args = request.args

    with sqlite3.connect(crossbot.db_path) as con:
        cursor = con.execute("select strftime('%w', ?)", (args.date,))
        day_of_week = int(cursor.fetchone()[0])

    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT userid, seconds
        FROM {}
        WHERE date = date(?)
        ORDER BY seconds'''.format(args.table)

        cursor = con.execute(query, (args.date,))

        for userid, seconds in cursor:
            name = client.user(userid)
            if seconds < 0:
                failures += ':facepalm: - {}\n'.format(name)
            else:
                emj = emoji(seconds, args.table, day_of_week)
                minutes, seconds = divmod(seconds, 60)
                response += ':{}: - {}:{:02d} - {}\n'.format(
                    emj, minutes, seconds, name)

    # append now so failures at the end
    response += failures

    if len(response) == 0:
        if args.date == 'now':
            response = 'No times yet for today, be the first!'
        else:
            response = 'No times for this date.'

    request.reply(response)
