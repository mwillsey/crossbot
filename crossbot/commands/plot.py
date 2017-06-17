
import datetime
import os
import sqlite3
import statistics
import numpy as np

from collections import defaultdict, OrderedDict
from itertools import takewhile, cycle
from tempfile import NamedTemporaryFile

# don't use matplotlib gui
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import crossbot

def init(client):

    parser = client.parser.subparsers.add_parser('plot', help='plot something')
    parser.set_defaults(
        command   = plot,
        plot_type = 'normalized',
        smooth    = 0.6,
        num_days  = 7,
    )

    ptype = parser.add_argument_group('Plot type')\
                    .add_mutually_exclusive_group()

    ptype.add_argument(
        '--times',
        action = 'store_const',
        dest   = 'plot_type',
        const  = 'times',
        help   = 'Plot the raw times.')

    ptype.add_argument(
        '--normalized',
        action  = 'store_const',
        dest    = 'plot_type',
        const   = 'normalized',
        help    = 'Plot smoothed, normalized scores.'
        ' Higher is better. (Default)')


    appearance = parser.add_argument_group('Plot appearance')
    scales = appearance.add_mutually_exclusive_group()

    scales.add_argument(
        '--log',
        action = 'store_const',
        dest   = 'scale',
        const  = 'log')
    scales.add_argument (
        '--linear',
        action = 'store_const',
        dest   = 'scale',
        const  = 'linear')

    appearance.add_argument(
        '-s', '--smooth',
        type    = float,
        metavar = 'S',
        help = 'Smoothing factor between 0 and 0.95.'
        ' Default %(default)s.'
        ' Only applies to plot type `normalized`.')

    dates = parser.add_argument_group('Date range')

    dates.add_argument(
        '--start-date',
        type    = crossbot.date,
        metavar = 'START',
        help    = 'Date to start plotting from.')
    dates.add_argument(
        '--end-date',
        type    = crossbot.date,
        metavar = 'END',
        help    = 'Date to end plotting at. Defaults to today.')
    dates.add_argument(
        '-n', '--num-days',
        type    = int,
        metavar = 'N',
        help    = 'Number of days since today to plot.'
        ' Ignored if both start-date and end-date given.'
        ' Default %(default)s.')


def plot(client, request):
    '''Plot everyone's times in a date range.
    `plot [plot_type] [num_days] [smoothing] [scale] [start date] [end date]`, all arguments optional.
    `plot_type` is either `normalized` (default) or `times` for a non-smoothed plot of actual times.
    `smoothing` is between 0 (no smoothing) and 1 exclusive. .6 default
    You can provide either `num_days` or `start_date` and `end_date`.
    `plot` plots the last 5 days by default.
    The scale can be `log` or `linear`.'''

    args = request.args

    start_date = crossbot.date(args.start_date)
    end_date   = crossbot.date(args.end_date)

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt   = datetime.datetime.strptime(end_date,   "%Y-%m-%d").date()

    # we only use num_days if the other params weren't given
    # otherwise set num_days based the given range
    if start_date == end_date:
        start_dt -= datetime.timedelta(days=args.num_days)
        start_date = start_dt.strftime("%Y-%m-%d")
    else:
        args.num_days = (end_dt - start_dt).days

    if not 0 <= args.smooth <= 0.95:
        request.reply('smooth should be between 0 and 0.95', direct=True)

    if args.scale is None:
        args.scale = 'linear' if args.plot_type == 'normalized' else 'log'

    with sqlite3.connect(crossbot.db_path) as con:
        cursor = con.execute('''
        SELECT userid, date, seconds
        FROM crossword_time
        WHERE date
          BETWEEN date(?)
          AND     date(?)
        ORDER BY date, userid''', (start_date, end_date))

        userids_present = set()

        times = defaultdict(list)
        times_by_date = defaultdict(dict)
        for userid, date, seconds in cursor:
            userids_present.add(userid)
            if seconds >= 0:
                # don't add failures to the times plot
                times[userid].append((date, seconds))
            times_by_date[date][userid] = seconds

    if args.plot_type == 'normalized':
        sorted_dates = sorted(times_by_date.keys())

        # failures come with a heaver ranking penalty
        MAX_PENALTY = -1.5
        FAILURE_PENALTY = -2

        def mk_score(mean, t, stdev):
            if t < 0:
                return FAILURE_PENALTY
            if stdev == 0:
                return 0

            score = (mean - t) / stdev
            return max(MAX_PENALTY, score)

        # scores are the stdev away from mean of that day
        scores = {}
        for date, user_times in times_by_date.items():
            times = user_times.values()
            # make failures 1 minute worse than the worst time
            times = [t if t >= 0 else max(times) + 60 for t in times]
            q1, q3 = np.percentile(times, [25,75])
            stdev  = statistics.pstdev(times)
            o1, o3 = q1 - stdev, q3 + stdev
            times  = [t for t in times if o1 <= t <= o3]
            mean  = statistics.mean(times)
            stdev  = statistics.pstdev(times, mean)
            scores[date] = {
                userid: mk_score(mean, t, stdev)
                for userid, t in user_times.items()
            }

        new_score_weight = 1 - args.smooth
        running = defaultdict(list)

        MAX_PLOT_SCORE =  1.0
        MIN_PLOT_SCORE = -1.0
        weighted_scores = defaultdict(list)
        for date in sorted_dates:
            for user, score in scores[date].items():

                old_score = running.get(user)

                new_score = score * new_score_weight + old_score * (1 - new_score_weight) \
                            if old_score is not None else score

                running[user] = new_score
                plot_score = max(MIN_PLOT_SCORE, min(new_score, MAX_PLOT_SCORE))
                weighted_scores[user].append((date, plot_score))


    width, height, dpi = (120*args.num_days), 600, 100
    width = max(400, min(width, 1000))

    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax = fig.add_subplot(1,1,1)
    ax.set_yscale(args.scale)

    def fmt_min(sec, pos):
        minutes, seconds = divmod(int(sec), 60)
        return '{}:{:02}'.format(minutes, seconds)

    cmap = plt.get_cmap('nipy_spectral')
    markers = cycle(['-o', '-X', '-s', '-^'])

    if args.plot_type == 'normalized':
        weighted_scores = OrderedDict(sorted(weighted_scores.items()))
        n_users = len(weighted_scores)
        colors = [cmap(i / n_users) for i in range(n_users)]
        for (userid, pairs), color in zip(weighted_scores.items(), colors):
            dates, scores = zip(*pairs)
            dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
            name = client.user(userid)
            ax.plot_date(mdates.date2num(dates), scores, next(markers), label=name, color=color)

    elif args.plot_type == 'times':
        max_sec = 0
        n_users = len(times)
        colors = [cmap(i / n_users) for i in range(n_users)]
        times = OrderedDict(sorted(times.items()))
        for (userid, entries), color in zip(times.items(), colors):

            dates, seconds = zip(*entries)
            max_sec = max(max_sec, max(seconds))
            dates = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
            name = client.user(userid)
            ax.plot_date(mdates.date2num(dates), seconds, next(markers), label=name, color=color)

        if args.scale == 'log':
            ticks = takewhile(lambda x: x <= max_sec, (30 * (2**i) for i in range(10)))
            ax.yaxis.set_ticks(list(ticks))
        else:
            ax.yaxis.set_ticks(range(0, max_sec+1, 30))

        ax.set_ylim(bottom=0)

    else:
        raise RuntimeError('invalid plot_type {}'.format(args.plot_type))

    fig.autofmt_xdate()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %-d')) # May 3
    if args.plot_type == 'times':
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt_min)) # 1:30
    ax.legend(fontsize=6, loc='upper left')

    temp = NamedTemporaryFile(suffix='.png', delete=False)
    fig.savefig(temp, format='png', bbox_inches='tight')
    temp.close()
    plt.close(fig)

    request.upload('plot', temp.name)

    # don't renome temp files if using command line client,
    # let the user see them
    if not isinstance(request, crossbot.client.CommandLineRequest):
        os.remove(temp.name)
