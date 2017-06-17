import sqlite3

import crossbot
import util

def init(subparsers):

    parser = subparsers.add_parser('times', help='show times')
    parser.set_defaults(command= times)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = util.get_date,
        help    = 'Date to get times for.')


def times(client, args):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    response = ''
    failures = ''

    with sqlite3.connect(crossbot.db_path) as con:
        cursor = con.execute('''
        SELECT userid, seconds
        FROM crossword_time
        WHERE date = date(?)
        ORDER BY seconds''', (args.date,))

        for userid, seconds in cursor:
            name = client.user(userid)
            if seconds < 0:
                failures += '0{} - :facepalm:\n'.format(name)
            else:
                minutes, seconds = divmod(seconds, 60)
                response += '0{} - {}:{:02d}\n'.format(name, minutes, seconds)

    # append now so failures at the end
    response += failures

    if len(response) == 0:
        if args.date == 'now':
            response = 'No times yet for today, be the first!'
        else:
            response = 'No times for this date.'

    client.send(response)
