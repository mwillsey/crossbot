"""Stan-based statistical model for user skill"""

import pickle
import pystan
from django.utils import timezone
import bisect
import os
from hashlib import md5

from . import models


def index(l):
    x = list(sorted(set(l), key=id))
    return [x.index(i) + 1 for i in l]


def unindex(l, i):
    return list(sorted(set(l), key=id))[i - 1]


def data():
    all_times = models.MiniCrosswordTime.all_times()
    return {
        'uids': [t.user for t in all_times],
        'dates': [t.date for t in all_times],
        'dows': [(t.date.weekday() + 1) % 7 for t in all_times],
        'secs': [t.seconds for t in all_times],
        'ts': [t.timestamp or t.date for t in all_times],
    }


def nth(uids, dates, ts):
    uid_dates = {
        the_uid: sorted([t for uid, t in zip(uids, ts) if uid == the_uid])
        for the_uid in set(uids)
    }
    return [
        bisect.bisect(uid_dates[uid], ts) + 1
        for uid, date, ts in zip(uids, dates, ts)
    ]


def munge_data(uids, dates, dows, secs, ts):
    return {
        'uids': index(uids),
        'dates': index(dates),
        'nth': nth(uids, dates, ts),
        'dows': [int(dow) + 1 for dow in dows],
        'secs': secs,
        'Us': len(set(uids)),
        'Ss': len(secs),
        'Ds': len(set(dates)),
    }


class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    '''

    def __init__(self, quiet=True):
        self.quiet = quiet
        if quiet:
            # Open a pair of null files
            self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
            # Save the actual stdout (1) and stderr (2) file descriptors.
            self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        if self.quiet:
            # Assign the null pointers to stdout and stderr.
            os.dup2(self.null_fds[0], 1)
            os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        if self.quiet:
            # Re-assign the real stdout/stderr back to (1) and (2)
            os.dup2(self.save_fds[0], 1)
            os.dup2(self.save_fds[1], 2)
            # Close the null files
            for fd in self.null_fds + self.save_fds:
                os.close(fd)


def fit(data, quiet=False):
    path = os.path.join(os.path.dirname(__file__), 'predictor.stan')
    with open(path, "r") as f:
        code = f.read()
    hash = md5(code.encode("ascii")).hexdigest()
    try:
        os.makedirs(os.path.expanduser("~/.cache/crossbot/"))
    except FileExistsError:
        pass

    cache_path = os.path.expanduser(
        '~/.cache/crossbot/predictor.' + hash + '.model'
    )
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            sm = pickle.load(f)
    else:
        print("Compiling model, please wait")
        sm = pystan.StanModel(model_code=code)
        with open(cache_path, "wb") as f:
            pickle.dump(sm, f)

    with suppress_stdout_stderr(quiet=quiet):
        fm = sm.sampling(
            data=munge_data(**data),
            iter=1000,
            chains=4,
            n_jobs=2,
            pars=[
                'date_effect', 'skill_effect', 'predictions', 'residuals',
                'beginner_gain', 'beginner_decay', 'sat_effect', 'mu',
                'skill_dev', 'date_dev', 'sigma'
            ],
        )
    return fm


def drange(data):
    data.sort()
    mu = data.mean()
    return mu, mu - data[len(data) // 4], data[len(data) * 3 // 4] - mu


def extract_model(data, fm):
    params = fm.extract()

    dates = []
    for i, multiplier in enumerate(params["date_effect"].transpose()):
        date = unindex(data['dates'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        dates.append(
            models.PredictionDate(
                date=date,
                difficulty=mult_mean,
                difficulty_25=mult_25,
                difficulty_75=mult_75
            )
        )

    users = []
    for i, multiplier in enumerate(params["skill_effect"].transpose()):
        uid = unindex(data['uids'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        users.append(
            models.PredictionUser(
                user=uid,
                skill=mult_mean,
                skill_25=mult_25,
                skill_75=mult_75,
            )
        )

    recs = []
    for date, uid, prediction, residual in zip(
            data["dates"], data["uids"], params["predictions"].transpose(),
            params["residuals"].transpose()):
        recs.append(
            models.Prediction(
                date=date,
                user=uid,
                prediction=prediction.mean(),
                residual=residual.mean()
            )
        )

    bgain_mean, bgain_25, bgain_75 = drange(params['beginner_gain'])
    bdecay_mean, bdecay_25, bdecay_75 = drange(params['beginner_decay'])
    time_mean, time_25, time_75 = drange(params['mu'])
    satmult_mean, satmult_25, satmult_75 = drange(params['sat_effect'])
    params = models.PredictionParameter(
        time=time_mean,
        time_25=time_25,
        time_75=time_75,
        satmult=satmult_mean,
        satmult_25=satmult_25,
        satmult_75=satmult_75,
        bgain=bgain_mean,
        bgain_25=bgain_25,
        bgain_75=bgain_75,
        bdecay=bdecay_mean,
        bdecay_25=bdecay_25,
        bdecay_75=bdecay_75,
        skill_dev=params['skill_dev'].mean(),
        date_dev=params['date_dev'].mean(),
        sigma=params['sigma'].mean(),
        lp=params["lp__"].mean(),
        when_run=timezone.now(),
    )
    return recs, dates, users, params


def save(model):
    recs, dates, users, params = model
    models.Prediction.objects.all().delete()
    models.PredictionUser.objects.all().delete()
    models.PredictionDate.objects.all().delete()
    models.PredictionParameter.objects.all().delete()

    for rec in recs:
        rec.save()
    for date in dates:
        date.save()
    for user in users:
        user.save()
    params.save()


def load():
    recs = list(models.Prediction.objects.all())
    dates = list(models.PredictionDate.objects.all())
    user = list(models.PredictionUser.objects.all())
    params = models.PredictionParameter.objects.all()[:1].get()
    return recs, dates, user, params


### TODO: The below do not use the new model format

import math
from datetime import datetime
import matplotlib, matplotlib.dates, matplotlib.figure, matplotlib.ticker
import matplotlib.backends.backend_agg as agg


def plot_dates(model):
    field = lambda f: [x[f] for x in model['dates'] if x['date'] >= '2017']
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in field('date')]
    dates_ = matplotlib.dates.date2num(dates)
    ax.errorbar(
        dates_,
        field('difficulty'),
        yerr=(field('difficulty_25'), field('difficulty_75')),
        fmt='o'
    )
    #yhat = savgol_filter(field('difficulty'), 51, 3)
    #ax.plot(dates_, yhat, 'red')
    return fig


def plot_users(model, nameuser=lambda x: x):
    users = sorted(model['users'], key=lambda x: x['skill'])
    field = lambda f: [x[f] for x in users]
    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Crossword Skill of User")
    ax.errorbar(
        field('skill'),
        range(len(users)),
        xerr=(field('skill_25'), field('skill_75')),
        fmt='o'
    )
    ax.set_yticks(range(len(users)))
    ax.set_yticklabels(map(nameuser, field('uid')))
    return fig


def plot_rdates(model):
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    pts = sorted([(rec['date'], rec['residual'])
                  for rec in model['historic']
                  if rec['date'] >= '2017'])

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    gs = matplotlib.gridspec.GridSpec(1, 2, width_ratios=[3, 1])
    gs.update(wspace=0.025)

    ax = fig.add_subplot(gs[0])
    ax.xaxis_date(None)
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, r in pts]
    dates_ = matplotlib.dates.date2num(dates)
    color = [(0, 0, 1, 1.0 / list(dates_).count(d)) for d in dates_]
    ax.scatter(dates_, [r for d, r in pts], c=color, marker='o')
    #yhat = savgol_filter([r for d, r in pts], 101, 1)
    #ax.plot(dates_, yhat, 'red')
    ax.plot(dates_, [0 for n, r in pts], 'black')

    ax2 = fig.add_subplot(gs[1], sharey=ax)
    ax2.tick_params(
        'both', left=False, labelleft=False, bottom=False, labelbottom=False
    )
    ax2.hist([r for d, r in pts], orientation="horizontal")

    return fig


def plot_rnth(data, model, user=None):
    nths = nth(data['uids'], data['dates'], data['ts'])
    pts = sorted([(d, rec['residual'])
                  for d, rec in zip(nths, model['historic'])
                  if user is None or rec["uid"] == user])
    nths_ = [d for d, r in pts]

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    gs = matplotlib.gridspec.GridSpec(1, 2, width_ratios=[3, 1])
    gs.update(wspace=0.025)

    color = [(0, 0, 1, 1.0 / nths_.count(d)) for d, r in pts]
    ax = fig.add_subplot(gs[0])
    ax.scatter([d for d, r in pts], [r for d, r in pts], c=color, marker='o')
    window = 101 if not user else (len(pts) // 10 * 2 + 1)
    #yhat = savgol_filter([r for d, r in pts], window, 1)
    #ax.plot([d for d, r in pts], yhat, 'red')
    ax.plot([d for d, r in pts], [0 for n, r in pts], 'black')

    ax2 = fig.add_subplot(gs[1], sharey=ax)
    ax2.tick_params(
        'both', left=False, labelleft=False, bottom=False, labelbottom=False
    )
    ax2.hist([r for d, r in pts], orientation="horizontal")

    return fig


def plots(data, model, nameuser=lambda x: x):
    agg.FigureCanvasAgg(plot_dates(model)).print_figure("dates.pdf")
    agg.FigureCanvasAgg(plot_users(model, nameuser=nameuser)
                        ).print_figure("users.pdf")
    agg.FigureCanvasAgg(plot_rdates(model)).print_figure("res-dates.pdf")
    agg.FigureCanvasAgg(plot_rnth(data, model)).print_figure("res-nth.pdf")


def urange(data, user):
    dates = {d for d, u in zip(data['dates'], data['uids']) if u == user}
    mi, ma = min(dates), max(dates)
    out = []
    since_good = 0
    for d in sorted(set(data['dates'])):
        if mi < d < ma:
            if d in dates: since_good = 0
            else: since_good += 1
            if since_good <= 7:
                out.append((d, d in dates))
    return out


def selsub(data, model, user):
    play, dont = set(), set()

    date_diff = {}
    for d in model["dates"]:
        date_diff[d["date"]] = d["difficulty"]

    for date, played in urange(data, user):
        (play if played else dont).add(date_diff[date])

    if len(dont) == 0 or len(play) == 0: return 0

    diff_means = sum(dont) / len(dont) - sum(play) / len(play)
    stdev = model['date_dev']
    z_diff = diff_means / (
        math.sqrt(stdev**2 / len(play) + stdev**2 / len(dont))
    )
    return (math.erf(z_diff / math.sqrt(2)) + 1) / 2


def selsubs(data, model):
    info = {
        user['uid']: selsub(data, model, user['uid'])
        for user in model['users']
    }
    for u, p in sorted(info.items(), key=lambda x: x[1], reverse=True):
        if p < .99: break
        print(u, p)


if __name__ == "__main__":
    DATA = data()
    FIT = fit(DATA)
    MODEL = extract_model(DATA, FIT)
    save(MODEL)
