import sqlite3
from datetime import datetime, timedelta

import crossbot
import crossbot.parser

def init(client):

    parser = client.parser.subparsers.add_parser(
            'missed',
            help='Get mini crossword link for the most recent day you missed.')
    parser.set_defaults(command=get_missed)

def parse_date(d):
    return datetime.strptime(d, crossbot.parser.date_fmt)

mini_url = "https://www.nytimes.com/crosswords/game/mini/{:04}/{:02}/{:02}"

def get_missed(client, request):

    # get all the entries for this person
    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT date
        FROM {}
        WHERE userid = ?
        '''.format(request.args.table)

        result = con.execute(query, (request.userid,))

    # sort dates completed from most recent to oldest
    completed = set(parse_date(tup[0]) for tup in result)

    # find missed day
    missed = parse_date(crossbot.parser.date('now'))
    while True:
        if missed not in completed:
            break
        missed -= timedelta(days=1)

    url = mini_url.format(missed.year, missed.month, missed.day)
    request.reply(url)
