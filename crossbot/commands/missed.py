import sqlite3
from datetime import datetime, timedelta

import crossbot
import crossbot.parser

def init(client):

    parser = client.parser.subparsers.add_parser(
            'missed',
            help='Get mini crossword link for the most recent day you missed.')
    parser.set_defaults(command=get_missed)

    parser.add_argument(
        'n',
        nargs   = '?',
        default = '1',
        type    = int,
        help    = 'Show the nth most recent ones you missed')

mini_url = "https://www.nytimes.com/crosswords/game/mini/{:04}/{:02}/{:02}"

def get_missed(request):

    all_entries = request.args.table.objects.filter(user = request.user)
    completed = set(e.date for e in all_entries)

    # find missed day
    date = crossbot.parser.date('now')
    n = request.args.n
    missed = []
    for i in range(n):
        while date in completed:
            date -= timedelta(days=1)
        missed.append(date)
        date -= timedelta(days=1)

    urls = [
        mini_url.format(d.year, d.month, d.day)
        for d in missed
    ]
    request.reply('\n'.join(urls))
