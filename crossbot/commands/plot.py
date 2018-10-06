
import datetime
import sqlite3
import statistics
import numpy as np

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

    parser = client.parser.subparsers.add_parser('plot', help='plot something')
    parser.set_defaults(
        command   = plot,
        smooth    = 0.7,
        alpha     = 0.7,
        num_days  = 7,
        scale     = 'linear',
        score_function = get_normalized_scores,
    )

    ptype = parser.add_argument_group('Plot type')\
                    .add_mutually_exclusive_group()

    ptype.add_argument(
        '--times',
        action = 'store_const',
        dest   = 'score_function',
        const  = get_times,
        help   = 'Plot the raw times.')

    ptype.add_argument(
        '--normalized',
        action  = 'store_const',
        dest    = 'score_function',
        const   = get_normalized_scores,
        help    = 'Plot smoothed, normalized scores.'
        ' Higher is better. (Default)')

    ptype.add_argument(
        '--streaks',
        action  = 'store_const',
        dest    = 'score_function',
        const   = get_streaks,
        help    = 'Plot completion streaks')

    ptype.add_argument(
        '--win-streaks',
        action  = 'store_const',
        dest    = 'score_function',
        const   = get_win_streaks,
        help    = 'Plot win streaks')

    appearance = parser.add_argument_group('Plot appearance')
    scales = appearance.add_mutually_exclusive_group()

    scales.add_argument(
        '--log',
        action = 'store_const',
        dest   = 'scale',
        const  = 'symlog')
    scales.add_argument(
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

    appearance.add_argument(
        '--alpha',
        type = float,
        help = 'Transparency for plotted points.'
        ' Default %(default)s.')

    dates = parser.add_argument_group('Date range')

    def date_none(date_str): return crossbot.date(date_str, default=None)

    dates.add_argument(
        '--start-date',
        type    = date_none,
        metavar = 'START',
        help    = 'Date to start plotting from.')
    dates.add_argument(
        '--end-date',
        type    = date_none,
        metavar = 'END',
        help    = 'Date to end plotting at. Defaults to today.')
    dates.add_argument(
        '-n', '--num-days',
        type    = int,
        metavar = 'N',
        help    = 'Number of days since today to plot.'
        ' Ignored if both start-date and end-date given.'
        ' Default %(default)s.')

    parser.add_argument(
        '-f', '--focus',
        action  = 'append',
        type    = str,
        metavar = 'USER',
        help    = 'Slack name of player to focus the plot on. Can be used multiple times.')


# a nice way to convert db entries into objects
Entry = namedtuple('Entry', ['userid', 'date', 'seconds'])


def fmt_min(sec, pos):
    minutes, seconds = divmod(int(sec), 60)
    return '{}:{:02}'.format(minutes, seconds)


# "date" means a date string, "dt" means a datetime object
def date_dt(date):
    return datetime.datetime.strptime(date, date_fmt).date()


def plot(client, request):
    '''Plot everyone's times in a date range.
    `smoothing` is between 0 (no smoothing) and 1 exclusive. .6 default
    You can provide either `num_days` or `start_date` and `end_date`.
    `plot` plots the last 5 days by default.
    The scale can be `log` or `linear` (default).'''

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

    if not 0 <= args.smooth <= 0.95:
        request.reply('smooth should be between 0 and 0.95', direct=True)
        return

    if not 0 <= args.alpha <= 1:
        request.reply('alpha should be between 0 and 1', direct=True)
        return

    if start_dt > end_dt:
        request.reply('start date should be before end_date', direct=True)
        return

    dt_range = [ start_dt + datetime.timedelta(days=i)
                 for i in range(args.num_days + 1) ]
    date_range = [dt.strftime(date_fmt) for dt in dt_range]

    # For normalized, once date_range is already made, bump the start date
    # back. Normalized uses smoothing, so we don't want the initial point
    # plotted to be "overweighted" because there's no history
    if args.score_function is get_normalized_scores:
        start_dt -= datetime.timedelta(days=int(1 / (1 - args.smooth)))
        start_date = start_dt.strftime(date_fmt)

    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT userid, date, seconds
        FROM {}
        WHERE date
          BETWEEN date(?)
          AND     date(?)
        ORDER BY date, userid'''.format(args.table)

        cur = con.execute(query, (start_date, end_date))
        entries = [Entry._make(tup) for tup in cur]

    scores_by_user, ticker, formatter = args.score_function(entries, args)

    # find contiguous sequences of dates
    user_seqs = [
        (userid, [
            list(g)
            for k, g in groupby((
                (date, date_scores.get(date))
                for date in date_range
            ), lambda ds: ds[1] is not None)
            if k
        ])
        for userid, date_scores in scores_by_user.items()
    ]

    # sort by actual username
    user_seqs.sort(key=lambda tup: client.user(tup[0]))

    width, height, dpi = (120*args.num_days), 600, 100
    width = max(400, min(width, 1000))

    fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
    ax = fig.add_subplot(1,1,1)

    cmap = plt.get_cmap('nipy_spectral')
    markers = cycle(['-o', '-X', '-s', '-^'])

    n_users = len(user_seqs)
    colors = [cmap(i / n_users) for i in range(n_users)]

    if args.score_function in [get_streaks, get_win_streaks]:
        thickness = 1
        # sort by first date appeared
        user_seqs.sort(key=lambda x: min(x[1][0]))

        for (userid, date_seqs), i, color in zip(user_seqs, count(), colors):
            name = client.user(userid)
            label = name
            starts_and_lens = [
                ((date_dt(min(seq)[0]) - start_dt).days, len(seq))
                for seq in date_seqs
            ]
            starts, lens = zip(*starts_and_lens)
            ax.barh(i, lens, thickness, starts, tick_label=name)

        plt.yticks(
            np.arange(len(user_seqs)) * thickness,
            [
                client.user(userid)
                for userid, seq in user_seqs
            ],
            size = 6,
        )

    else:
        max_score = -100000

        for (userid, date_seqs), color, marker in zip(user_seqs, colors, markers):
            name = client.user(userid)
            label = name
            alpha = args.alpha

            if args.focus:
                if name in args.focus:
                    alpha = 1.0
                else:
                    color = 'gray'
                    alpha = 0.3

            for date_seq in date_seqs:
                dates, scores = zip(*date_seq)
                max_score = max(max_score, max(scores))
                dates = [datetime.datetime.strptime(d, date_fmt).date() for d in dates]

                ax.plot_date(mdates.date2num(dates), scores, marker, label=label, color=color, alpha=alpha)

                # make sure that we don't but anyone in the legend twice
                label = '_nolegend_'


        ax.set_yscale(args.scale)
        ax.yaxis.set_major_locator(ticker)
        ax.yaxis.set_major_formatter(formatter)

    fig.autofmt_xdate()
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %-d')) # May 3

    # hack to prevent crashes on the regular crosswords
    ax.xaxis.get_major_locator().MAXTICKS = 10000

    ax.legend(fontsize=6, loc='upper left')

    temp = NamedTemporaryFile(suffix='.pdf', delete=False)
    fig.savefig(temp, format='pdf', bbox_inches='tight')
    temp.close()
    plt.close(fig)

    request.upload('plot', temp.name)


#########################
### Scoring Functions ###
#########################


# these should all take a list of Entry objects and the args object, and a
# return a dict that looks like this:
#   scores[userid][date] = score
# and also a ticker and a formatter


def get_normalized_scores(entries, args):
    """Generate smoothed scores based on mean, stdev of that days times. """

    times_by_date = defaultdict(dict)
    for e in entries:
        x = e.seconds
        # if x > 0:
        #     x = np.log(x)
        times_by_date[e.date][e.userid] = x

    sorted_dates = sorted(times_by_date.keys())

    # failures come with a heaver ranking penalty
    MAX_SCORE = 1.5
    FAILURE_PENALTY = -2

    def mk_score(mean, t, stdev):
        if t < 0:
            return FAILURE_PENALTY
        if stdev == 0:
            return 0

        score = (mean - t) / stdev
        return np.clip(score, -MAX_SCORE, MAX_SCORE)

    # scores are the stdev away from mean of that day
    scores = {}
    for date, user_times in times_by_date.items():
        times = [t for t in user_times.values() if t is not None]
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
            if t is not None
        }

    new_score_weight = 1 - args.smooth
    running = defaultdict(list)

    weighted_scores = defaultdict(dict)
    for date in sorted_dates:
        for user, score in scores[date].items():

            old_score = running.get(user)

            new_score = score * new_score_weight + old_score * (1 - new_score_weight) \
                        if old_score is not None else score

            weighted_scores[user][date] = running[user] = new_score

    ticker = matplotlib.ticker.MultipleLocator(base=0.25)
    formatter = matplotlib.ticker.ScalarFormatter(useOffset=False)

    return weighted_scores, ticker, formatter


def get_times(entries, args):
    """Just get the times, removing any failures."""

    times = defaultdict(dict)
    for e in entries:
        if e.seconds >= 0:
            # don't add failures to the times plot
            times[e.userid][e.date] = e.seconds

    # Set base to 30s for mini crossword, 5 min for regular or sudoku
    sec = 30 if args.table == crossbot.models.MiniCrosswordTime else 60 * 5
    ticker = matplotlib.ticker.MultipleLocator(base=sec)
    formatter = matplotlib.ticker.FuncFormatter(fmt_min) # 1:30

    return times, ticker, formatter

def get_win_streaks(entries, args):
    """Just get the times, keeping failures because we're just going for completion"""

    best_time = defaultdict(lambda: 99999999999999)
    for e in entries:
        if e.seconds >= 0:
            best_time[e.date] = min(best_time[e.date], e.seconds)

    times = defaultdict(dict)
    for e in entries:
        if e.seconds == best_time[e.date]:
            times[e.userid][e.date] = e.seconds

    ticker = None
    formatter = None

    return times, ticker, formatter

def get_streaks(entries, args):
    """Just get the times, keeping failures because we're just going for completion"""

    times = defaultdict(dict)
    for e in entries:
        times[e.userid][e.date] = e.seconds

    ticker = None
    formatter = None

    return times, ticker, formatter
