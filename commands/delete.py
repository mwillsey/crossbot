import sqlite3

import crossbot
import util

def init(subparsers):

    parser = subparsers.add_parser('delete', help='Delete a time.')
    parser.set_defaults(command=delete)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = util.get_date,
        help    = 'Date to delete a score for.')

    # TODO add a command-line only --user parameter

def delete(client, args):
    '''Delete entry for today or given date (`delete 2017-05-05`).'''

    with sqlite3.connect(crossbot.db_path) as con:
        cur = con.cursor()
        cur.execute('''
        DELETE FROM crossword_time
        WHERE userid=? AND date=date(?)
        ''', (client.userid, args.date))

        if cur.rowcount == 0:
            client.reply("You didn't have an entry for this date.")
        else:
            client.react('x')
