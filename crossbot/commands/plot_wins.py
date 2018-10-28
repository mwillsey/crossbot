import datetime
import sqlite3
import statistics
import numpy as np
import html, re

from collections import defaultdict, namedtuple
from itertools import cycle, groupby, count
from tempfile import NamedTemporaryFile

# don't use matplotlib gui
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import crossbot

from crossbot.parser import date_fmt


def init(client):

    parser = client.parser.subparsers.add_parser('plot-wins', help='plot wins')
    parser.set_defaults(
        command=plot_wins,
        alpha=0.7,
        num_days=7,
    )

    appearance = parser.add_argument_group('Plot appearance')

    appearance.add_argument(
        '--alpha',
        type=float,
        help='Transparency for plotted points.'
        ' Default %(default)s.'
    )

    dates = parser.add_argument_group('Date range')

    def date_none(date_str):
        return crossbot.date(date_str, default=None)

    dates.add_argument(
        '--start-date',
        type=date_none,
        metavar='START',
        help='Date to start plotting from.'
    )
    dates.add_argument(
        '--end-date',
        type=date_none,
        metavar='END',
        help='Date to end plotting at. Defaults to today.'
    )
    dates.add_argument(
        '-n',
        '--num-days',
        type=int,
        metavar='N',
        help='Number of days since today to plot.'
        ' Ignored if both start-date and end-date given.'
        ' Default %(default)s.'
    )

    parser.add_argument('users', nargs='+', help='Slack names of player')


# a nice way to convert db entries into objects
Entry = namedtuple('Entry', ['userid', 'date', 'seconds', 'timestamp'])


def plot_wins(client, request):
    '''Plot wins

    example: cb plot-wins @mwillsey @doug -n 500
    '''

    args = request.args

    start_date = args.start_date
    end_date = args.end_date

    delta = datetime.timedelta(days=args.num_days)

    # if we have both dates, use them and correct num days
    # if we have one, use that and num_days
    # otherwise, end_date is today and use num_days
    if start_date:
        start_dt = date_dt(start_date)
        if end_date:
            end_dt = date_dt(end_date)
            args.num_days = (end_dt - start_dt).days
        else:
            end_dt = start_dt + delta
    else:
        end_dt = date_dt(end_date if end_date else crossbot.date('now'))
        start_dt = end_dt - delta

    # reformat the dates based on the above dt calculations
    start_date = start_dt.strftime(date_fmt)
    end_date = end_dt.strftime(date_fmt)

    if len(args.users) < 2:
        request.reply('I need 2 or more users', direct=True)
        return

    # get the users
    def replace_with_id(match):
        return match.group(1)

    userids = []
    for u in args.users:
        s = html.unescape(u)
        uid = re.sub(r'<@(\w+)>', replace_with_id, s)
        # check user id
        client.user(uid)
        userids.append(uid)

    dt_range = [
        start_dt + datetime.timedelta(days=i)
        for i in range(args.num_days + 1)
    ]
    date_range = [dt.strftime(date_fmt) for dt in dt_range]

    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT userid, date, seconds, timestamp
        FROM {}
        WHERE '''.format(args.table)

        query += ' OR '.join('userid = "{}"'.format(u) for u in userids)

        cur = con.execute(query)
        entries = [Entry._make(tup) for tup in cur]

    # sort by timestamp if present, else date
    entries.sort(key=lambda e: e.timestamp or e.date)

    wins = {u: 0 for u in userids}
    points = []

    def add_point(dt):
        points.append((dt, dict(wins)))

    by_date = defaultdict(dict)
    for e in entries:
        if e.timestamp:
            ts = datetime.datetime.strptime(
                e.timestamp, '%Y-%m-%d %H:%M:%S.%f'
            )
        else:
            ts = datetime.datetime.strptime(e.date, '%Y-%m-%d')
        this_date = by_date[e.date]
        assert e.userid not in this_date
        this_date[e.userid] = e.seconds

        if len(this_date) != len(userids):
            add_point(ts)
            continue

        times = [t for t in this_date.values() if t != -1]
        if not times:
            # everyone failed, skip
            add_point(ts)
            continue

        best_time = min(times)
        winners = [u for u in userids if this_date[u] == best_time]

        for w in winners:
            wins[w] += 1

        add_point(ts)

    width, height, dpi = (120 * args.num_days), 600, 100
    width = max(400, min(width, 1000))

    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax = fig.add_subplot(1, 1, 1)

    x, ys = zip(
        *((dt, wins)
          for dt, wins in points
          if start_dt <= dt.date() and dt.date() <= end_dt)
    )

    for u in userids:
        name = client.user(u)
        ax.plot_date(
            mdates.date2num(x), [y[u] for y in ys],
            linestyle='-',
            marker=None,
            label=name
        )

    ax.legend(fontsize=6, loc='upper left')

    temp = NamedTemporaryFile(suffix='.pdf', delete=False)
    fig.savefig(temp, format='pdf', bbox_inches='tight')
    temp.close()
    plt.close(fig)

    request.upload('plot', temp.name)
