import sqlite3

import crossbot

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

    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT userid, seconds
        FROM {}
        WHERE date = date(?)
        ORDER BY seconds'''.format(request.args.table)

        cursor = con.execute(query, (request.args.date,))

        for userid, seconds in cursor:
            name = client.user(userid)
            if seconds < 0:
                failures += '{} - :facepalm:\n'.format(name)
            else:
                minutes, seconds = divmod(seconds, 60)
                response += '{} - {}:{:02d}\n'.format(name, minutes, seconds)

    # append now so failures at the end
    response += failures

    if len(response) == 0:
        if request.args.date == 'now':
            response = 'No times yet for today, be the first!'
        else:
            response = 'No times for this date.'

    request.reply(response)
