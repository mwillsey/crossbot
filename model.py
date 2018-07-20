from __future__ import print_function

import pystan
import sqlite3
from datetime import datetime, timedelta
import matplotlib, matplotlib.dates, matplotlib.figure, matplotlib.ticker
from scipy.signal import savgol_filter
import matplotlib.backends.backend_agg as agg
import bisect
import math

def index(l):
    x = list(sorted(set(l)))
    return [x.index(i) + 1 for i in l]

def unindex(l, i):
    return list(sorted(set(l)))[i - 1]

def data():
    with sqlite3.connect("crossbot.db") as cursor:
         uids, dates, dows, secs, ts = zip(*cursor.execute("select userid, date, strftime('%w', date), seconds, timestamp from mini_crossword_time"))
         return { 'uids': uids, 'dates': dates, 'dows': dows, 'secs': secs, 'ts': ts }

def nth(uids, dates, ts):
    uid_dates = { the_uid: sorted([date for uid, date in zip(uids, dates) if uid == the_uid])
                 for the_uid in set(uids)}
    return [ bisect.bisect(uid_dates[uid], ts.split(" ")[0] if ts else date) + 1
             for uid, date, ts in zip(uids, dates, ts) ]

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

def fit(data):
    sm = pystan.StanModel(file="crossbot.stan")
    fm = sm.sampling(data=munge_data(**data), pars=[
        'avg_time', 'avg_sat', 'avg_skill', 'avg_date', 'skill_dev', 'date_dev', 'sigma',
        'beginner_gain', 'beginner_decay',
    ], iter=1000, chains=4)
    return fm

def drange(data):
    data.sort()
    mu = data.mean()
    return mu, mu - data[len(data) // 4], data[len(data) * 3 // 4] - mu

def extract_model(fm):
    params = fm.extract()
    
    dates = []
    for i, multiplier in enumerate(params["avg_date"].transpose()):
        date = unindex(DATA['dates'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        dates.append({'date': date, 'difficulty': mult_mean, 'difficulty_25': mult_25, 'difficulty_75': mult_75})

    users = []
    for i, multiplier in enumerate(params["avg_skill"].transpose()):
        uid = unindex(DATA['uids'], i + 1)
        mult_mean, mult_25, mult_75 = drange(multiplier)
        #rate_mean, rate_25, rate_75 = drange(rate)
        users.append({ 'uid': uid,
                       'skill': mult_mean, 'skill_25': mult_25, 'skill_75': mult_75,
                       #'rate': rate_mean, 'rate_25': rate_25, 'rate_75': rate_75,
        })

    bgain_mean, bgain_25, bgain_75 = drange(params['beginner_gain'])
    bdecay_mean, bdecay_25, bdecay_75 = drange(params['beginner_decay'])
    time_mean, time_25, time_75 = drange(params['avg_time'])
    satmult_mean, satmult_25, satmult_75 = drange(params['avg_sat'])
    return { 'dates': dates, 'users': users, 'time': time_mean, 'time_25': time_25, 'time_75': time_75,
             'satmult': satmult_mean, 'satmult_25': satmult_25, 'satmult_75': satmult_75,
             'bgain': bgain_mean, 'bgain_25': bgain_25, 'bgain_75': bgain_75,
             'bdecay': bdecay_mean, 'bdecay_25': bdecay_25, 'bdecay_75': bdecay_75,
             'skill_dev': params['skill_dev'].mean(), 'date_dev': params['date_dev'].mean(), 'sigma': params['sigma'].mean(),
    }

MODEL_SQL = """
CREATE TABLE IF NOT EXISTS model_users (
  uid text not null primary key,
  skill real not null,
  skill_25 real not null,
  skill_75 real not null,
);

CREATE TABLE IF NOT EXISTS model_dates (
  date integer not null primary key,
  difficulty real not null,
  difficulty_25 real not null,
  difficulty_75 real not null,
);

CREATE TABLE IF NOT EXISTS model_params (
  time real, time_25 real, time_75 real,
  satmult real, satmult_25 real, satmult_75 real,
  skill_dev real, date_dev real, sigma real
);
"""

def save(MODEL):
    with sqlite3.connect("crossbot.db") as cursor:
        cursor.execute("drop table if exists model_users")
        cursor.execute("drop table if exists model_dates")
        cursor.execute("drop table if exists model_params")
        cursor.execute(MODEL_SQL)

        cursor.executemany(
            "insert into model_user(uid, skill, skill_25, skill_75) values(?,?,?,?)",
            [(user["uid"], user["skill"], user["skill_25"], user["skill_75"])
             for user in model["users"]])

        cursor.execute(
            "insert into model_dates(date, difficulty, difficulty_25, difficulty_75) values(?,?,?,?)",
            [(date["date"], date["difficulty"], date["difficulty_25"], date["difficulty_75"])
             for dates in model["dates"]])

        cursor.execute(
            "insert into model_params(time, time_25, time_75, satmult, satmult_25, satmult_75, skill_dev, date_dev, sigma) values(?,?,?,?,?,?,?,?,?)",
            (model["time"], model["time_25"], model["time_75"],
             model["satmult"], model["satmult_25"], model["satmult_75"],
             model["skill_dev"], model["date_dev"], model["sigma"]))

def residuals(data, model):
    from math import log, exp
    for uid, date, dow, sec, n \
        in zip(data["uids"], data["dates"], data["dows"], data["secs"],
               nth(data["uids"], data["dates"], data["ts"])):
        user = [rec for rec in model["users"] if rec["uid"] == uid][0]
        day = [rec for rec in model["dates"] if rec["date"] == date][0]

        # Quick and dirty
        mean = log(model["time"]) \
            + log(user["skill"]) \
            + log(day["difficulty"]) \
            + log(model["satmult"] if dow == '6' else 1) \
            + model['bgain'] * exp(-n / model['bdecay']) \

        yield (log(sec if sec >= 0 else 300) - mean) / model["sigma"]

def summarize(model, nameuser=lambda x: x):
    for date in model['dates']:
        print("{0[date]:>10}: {0[difficulty]: 6.3f} (-{0[difficulty_25]: 4.3f} {0[difficulty_75]:=+.3f})".format(date))
    print("")

    for user in sorted(model['users'], key=lambda x: x['skill']):
        name = nameuser(user['uid'])
        print(("{0:>20}: {1[skill]: 6.3f} (-{1[skill_25]: 4.3f} {1[skill_75]:=+6.3f})"
               #+ " {1[rate]:=+9.05f} t"
        ).format(name, user))

def plot_dates(model):
    field = lambda f: [x[f] for x in model['dates'] if x['date'] >= '2017']
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    ax.set_yscale('log')
    ax.set_yticks([.33, .4, .5, .6, .7, .85, 1, 1.2, 1.4, 1.66, 2, 2.5, 3, 3.5, 4])
    ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in field('date')]
    dates_ = matplotlib.dates.date2num(dates)
    ax.errorbar(dates_, field('difficulty'), yerr=(field('difficulty_25'), field('difficulty_75')), fmt='o')
    yhat = savgol_filter(field('difficulty'), 51, 3)
    ax.plot(dates_, yhat, 'red')
    return fig

def plot_users(model, nameuser=lambda x: x):
    users = sorted(model['users'], key=lambda x: x['skill'])
    field = lambda f: [x[f] for x in users]
    fig = matplotlib.figure.Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Crossword Skill of User")
    ax.errorbar(field('skill'), range(len(users)), xerr=(field('skill_25'), field('skill_75')), fmt='o')
    ax.set_yticks(range(len(users)))
    ax.set_yticklabels(map(nameuser, field('uid')))
    ax.set_xscale('log')
    ax.set_xticks([.33, .4, .5, .6, .7, .85, 1, 1.2, 1.4, 1.66, 2, 2.5, 3, 4])
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    return fig

def plot_rdates(data, model):
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    pts = sorted([(d, r) for d, r in zip(data['dates'], residuals(data, model)) if d >= '2017'])
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, r in pts]
    dates_ = matplotlib.dates.date2num(dates)
    ax.plot(dates_, [r for d, r in pts], 'o')
    yhat = savgol_filter([r for d, r in pts], 101, 1)
    ax.plot(dates_, yhat, 'red')
    ax.plot(dates_, [ 0 for n, r in pts ], 'black')
    return fig

def plot_rnth(data, model):
    nths = nth(data['uids'], data['dates'], data['ts'])
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    pts = sorted([(d, r) for d, r in zip(nths, residuals(data, model))])
    ax.plot([d for d, r in pts], [r for d, r in pts], 'o')
    yhat = savgol_filter([r for d, r in pts], 101, 1)
    ax.plot([d for d, r in pts], yhat, 'red')
    ax.plot([d for d, r in pts], [ 0 for n, r in pts ], 'black')
    return fig


def plots(data, model, nameuser=lambda x: x):
    agg.FigureCanvasAgg(plot_dates(model)).print_figure("dates.pdf")
    agg.FigureCanvasAgg(plot_users(model, nameuser=nameuser)).print_figure("users.pdf")
    agg.FigureCanvasAgg(plot_rdates(data, model)).print_figure("res-dates.pdf")
    agg.FigureCanvasAgg(plot_rnth(data, model)).print_figure("res-nth.pdf")

def lookup_user(model, uid):
    return [u for u in model["users"] if u["uid"] == uid][0]

def judge_time(data, model, day, todays, person, time):
    from math import log, exp
    is_sat = datetime.strptime(day, "%Y-%m-%d").strftime("%w") == '6'

    nths = {u: data["uids"].count(u) for u in todays}
    ynth = data["uids"].count(person)

    csecs = [log(secs)
             - log(model["time"])
             - log(lookup_user(model, user)["skill"])
             - log(model["satmult"] if is_sat else 1)
             - model['bgain'] * exp(-nths[user] / model['bdecay']) \
             for user, secs in todays.items()]

    difficulty = sum(csecs) / len(csecs)
    ysecs = log(time) - log(model["time"]) - log(lookup_user(model, person)["skill"]) \
        - log(model["satmult"] if is_sat else 1) - difficulty \
        - model['bgain'] * exp(-ynth / model['bdecay'])
    return ysecs / model["sigma"]
        

TEST = {
    "U0GRSVAJU": 32,  # -0.96
    "U0G3G2L9L": 35,  # -0.40
    "U0G3HALFR": 36,  # -2.14
    "U0G3FKDSS": 47,  # -1.13
    "U57492YFJ": 100, # +1.50
    "U0G3RR3EF": 101, # +1.45
    "U8D4CK7NC": 113, # +0.37
    "U0G6V794M": 136, # +1.31
}

DATA = data()
FIT = fit(DATA)
MODEL = extract_model(FIT)
summarize(MODEL)
plots(DATA, MODEL)
