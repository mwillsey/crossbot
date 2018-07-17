from __future__ import print_function

import pystan
import sqlite3
from datetime import datetime, timedelta
import matplotlib, matplotlib.dates, matplotlib.figure, matplotlib.ticker

def index(l):
    x = list(sorted(set(l)))
    return [x.index(i) + 1 for i in l]

def unindex(l, i):
    return list(sorted(set(l)))[i - 1]

def data():
    with sqlite3.connect("crossbot.db") as cursor:
         uids, dates, dows, secs = zip(*cursor.execute("select userid, date, strftime('%w', date), seconds from mini_crossword_time"))
         return { 'uids': uids, 'dates': dates, 'dows': dows, 'secs': secs }

def ago(uids, dates):
    uid_dates = { the_uid: sorted([date for uid, date in zip(uids, dates) if uid == the_uid])
                 for the_uid in set(uids)}
    return [ len(uid_dates[uid]) - uid_dates[uid].index(date) for uid, date in zip(uids, dates) ]

def munge_data(uids, dates, dows, secs):
    return {
        'uids': index(uids),
        'dates': index(dates),
        'ago': map(float, ago(uids, dates)),
        'dows': [int(dow) + 1 for dow in dows],
        'secs': secs,
        'Us': len(set(uids)),
        'Ss': len(secs),
        'Ds': len(set(dates)),
    }

def fit(data):
    sm = pystan.StanModel(file="crossbot.stan")
    fm = sm.sampling(data=munge_data(**data), pars=['avg_time', 'avg_sat', 'avg_skill', 'avg_date', 'skill_dev', 'date_dev', 'sigma', 'improvement_rate'], iter=1000, chains=4)
    return fm

def drange(data):
    data.sort()
    mu = data.mean()
    return mu, mu - data[len(data) // 4], data[len(data) * 3 // 4] - mu

def pi(n, l):
    return map(lambda x: x[n], l)

USERS = {}

def summarize(fm, userdict=USERS):
    params = fm.extract(['avg_time', 'avg_sat', 'avg_skill', 'avg_date', 'skill_dev', 'date_dev', 'sigma', 'improvement_rate'])
    print("Dates")
    out = []
    for i, multiplier in enumerate(params["avg_date"].transpose()):
        date = unindex(DATA['dates'], i + 1)
        mult = drange(multiplier * 100)
        if int(date[:4]) >= 2017: out.append((date, mult))
        print("{:>10}: {: 6.1f} ({: 6.1f} {:+.1f})".format(date, mult[0], -mult[1], mult[2]))
    print("")

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    ax.set_yscale('log')
    ax.set_yticks([40, 50, 60, 75, 100, 133, 166, 200, 250, 300, 350, 400, 500])
    ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, t in out]
    dates_ = matplotlib.dates.date2num(dates)
    ax.errorbar(dates_, pi(0, pi(1, out)), yerr=(pi(1, pi(1, out)), pi(2, pi(1, out))), fmt='o')
    import matplotlib.backends.backend_agg as agg
    agg.FigureCanvasAgg(fig).print_figure("dates.pdf")

    print("Users")
    out = []
    for i, (multiplier, rate) in enumerate(zip(params["avg_skill"].transpose(), params["improvement_rate"].transpose())):
        uid = unindex(DATA['uids'], i + 1)
        user = USERS.get(uid, uid)
        mult = drange(multiplier * 100)
        growth = drange(rate * 100)
        out.append((user, mult, growth))
    out.sort(key=lambda x: x[1])
    for uid, skill, rate in out:
        print("{:>20}: {: 6.1f} ({: 6.1f} {:+6.1f}) {:=+7.03f} t".format(uid, skill[0], -skill[1], skill[2], rate[0]))

    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Crossword Skill of User")
    ax.errorbar(pi(0, pi(1, out)), range(len(out)), xerr=(pi(1, pi(1, out)), pi(2, pi(1, out))), fmt='o')
    ax.set_yticks(range(len(out)))
    ax.set_yticklabels(pi(0, out))
    ax.set_xscale('log')
    ax.set_xticks([50, 75, 100, 133, 200, 300, 500])
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    agg.FigureCanvasAgg(fig).print_figure("users.pdf")

    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Improvement per Crossword")
    ax.errorbar(pi(0, pi(2, out)), range(len(out)), xerr=(pi(1, pi(2, out)), pi(2, pi(2, out))), fmt='o')
    ax.set_yticks(range(len(out)))
    ax.set_yticklabels(pi(0, out))
    agg.FigureCanvasAgg(fig).print_figure("rate.pdf")

DATA = data()
FIT = fit(DATA)
summarize(FIT)
