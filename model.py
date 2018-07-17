from __future__ import print_function

import pystan
import sqlite3
from datetime import datetime, timedelta
import matplotlib, matplotlib.dates, matplotlib.figure, matplotlib.ticker
from scipy.signal import savgol_filter
import matplotlib.backends.backend_agg as agg

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

def extract_model(fm):
    params = fm.extract(['avg_time', 'avg_sat', 'avg_skill', 'avg_date', 'skill_dev', 'date_dev', 'sigma', 'improvement_rate'])
    
    dates = []
    for i, multiplier in enumerate(params["avg_date"].transpose()):
        date = unindex(DATA['dates'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        dates.append({'date': date, 'difficulty': mult_mean, 'difficulty_25': mult_25, 'difficulty_75': mult_75})

    users = []
    for i, (multiplier, rate) in enumerate(zip(params["avg_skill"].transpose(), params["improvement_rate"].transpose())):
        uid = unindex(DATA['uids'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        rate_mean, rate_25, rate_75 = drange(rate)
        users.append({ 'uid': uid, 'skill': mult_mean, 'skill_25': mult_25, 'skill_75': mult_75,
                       'rate': rate_mean, 'rate_25': rate_25, 'rate_75': rate_75 })

    time_mean, time_25, time_75 = drange(params['avg_time'])
    satmult_mean, satmult_25, satmult_75 = drange(params['avg_sat'])
    return { 'dates': dates, 'users': users, 'time': time_mean, 'time_25': time_25, 'time_75': time_75,
             'satmult': satmult_mean, 'satmult_25': satmult_25, 'satmult_75': satmult_75,
             'skill_dev': params['skill_dev'].mean(), 'date_dev': params['date_dev'].mean(), 'sigma': params['sigma'].mean(),
    }

def summarize(model, nameuser=lambda x: x):
    for date in model['dates']:
        print("{0[date]:>10}: {0[difficulty]: 6.3f} (-{0[difficulty_25]: 4.3f} {0[difficulty_75]:=+.3f})".format(date))
    print("")

    for user in sorted(model['users'], key=lambda x: x['skill']):
        name = nameuser(user['uid'])
        print("{0:>20}: {1[skill]: 6.3f} (-{1[skill_25]: 4.3f} {1[skill_75]:=+6.3f}) {1[rate]:=+9.05f} t".format(name, user))

def plot_dates(model):
    field = lambda f: [x[f] for x in model['dates'] if x['date'][:4] >= '2017']

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    ax.set_yscale('log')
    ax.set_yticks([.4, .5, .6, .7, .85, 1, 1.2, 1.4, 1.66, 2, 2.5, 3, 3.5, 4, 5])
    ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in field('date')]
    dates_ = matplotlib.dates.date2num(dates)
    ax.errorbar(dates_, field('difficulty'), yerr=(field('difficulty_25'), field('difficulty_75')), fmt='o')
    yhat = savgol_filter(field('difficulty'), 51, 3)
    ax.plot(dates_, yhat, 'red')
    return fig

def plot_users(model, nameuser=lambda x: x):
    field = lambda f: [x[f] for x in model['users']]

    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Crossword Skill of User")
    ax.errorbar(field('skill'), range(len(model['users'])), xerr=(field('skill_25'), field('skill_75')), fmt='o')
    ax.set_yticks(range(len(model['users'])))
    ax.set_yticklabels(map(nameuser, field('uid')))
    ax.set_xscale('log')
    ax.set_xticks([.4, .5, .6, .7, .85, 1, 1.2, 1.4, 1.66, 2, 2.5, 3, 4, 5])
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    return fig

def plot_rates(model, nameuser=lambda x: x):
    field = lambda f: [x[f] for x in model['users']]

    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Improvement per Crossword")
    ax.errorbar(field('rate'), range(len(model['users'])), xerr=(field('rate_25'), field('rate_75')), fmt='o')
    ax.set_yticks(range(len(model['users'])))
    ax.set_yticklabels(map(nameuser, field('uid')))
    return fig

def plots(model, nameuser=lambda x: x):
    agg.FigureCanvasAgg(plot_dates(model)).print_figure("dates.pdf")
    agg.FigureCanvasAgg(plot_users(model, nameuser=nameuser)).print_figure("users.pdf")
    agg.FigureCanvasAgg(plot_rates(model, nameuser=nameuser)).print_figure("rates.pdf")

DATA = data()
FIT = fit(DATA)
MODEL = extract_model(FIT)
summarize(MODEL)
plots(MODEL)
