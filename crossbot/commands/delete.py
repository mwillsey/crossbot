import sqlite3

import crossbot

def init(client):

    parser = client.parser.subparsers.add_parser('delete', help='Delete a time.')
    parser.set_defaults(command=delete)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to delete a score for.')

    # TODO add a command-line only --user parameter

def delete(client, request):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        DELETE FROM {}
        WHERE userid=? AND date=date(?)
        '''.format(request.args.table)

        cur = con.cursor()
        cur.execute(query, (request.userid, request.args.date))

        if cur.rowcount == 0:
            request.reply("You didn't have an entry for this date.",
                         direct=True)
        else:
            request.react('x')
