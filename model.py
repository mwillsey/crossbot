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
    sm = pystan.StanModel(file="crossbot.stan", pars=[
        'date_effect', 'skill_effect', 'predictions', 'residuals',
        'beginner_gain', 'beginner_decay', 'sat_effect', 'mu',
        'skill_dev', 'date_dev', 'sigma'
    ])
    fm = sm.sampling(data=munge_data(**data), iter=1000, chains=4)
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
        dates.append({
            'date': date, 'difficulty': mult_mean,
            'difficulty_25': mult_25, 'difficulty_75': mult_75
        })

    users = []
    for i, multiplier in enumerate(params["skill_effect"].transpose()):
        uid = unindex(data['uids'], i + 1)
        nth = len([date for date, uid_ in zip(data['dates'], data['uids']) if uid == uid_])
        mult_mean, mult_25, mult_75 = drange(multiplier)
        users.append({
            'uid': uid, 'nth': nth, 'skill': mult_mean,
            'skill_25': mult_25, 'skill_75': mult_75,
        })

    recs = []
    for date, uid, prediction, residual in zip(
            data["dates"],
            data["uids"],
            params["predictions"].transpose(),
            params["residuals"].transpose()):
        recs.append({
            'date': date, 'uid': uid,
            'prediction': prediction.mean(), 'residual': residual.mean()
        })
        

    bgain_mean, bgain_25, bgain_75 = drange(params['beginner_gain'])
    bdecay_mean, bdecay_25, bdecay_75 = drange(params['beginner_decay'])
    time_mean, time_25, time_75 = drange(params['mu'])
    satmult_mean, satmult_25, satmult_75 = drange(params['sat_effect'])
    return {
        'dates': dates, 'users': users, 'historic': recs,
        'time': time_mean, 'time_25': time_25, 'time_75': time_75,
        'satmult': satmult_mean, 'satmult_25': satmult_25, 'satmult_75': satmult_75,
        'bgain': bgain_mean, 'bgain_25': bgain_25, 'bgain_75': bgain_75,
        'bdecay': bdecay_mean, 'bdecay_25': bdecay_25, 'bdecay_75': bdecay_75,
        'skill_dev': params['skill_dev'].mean(), 'date_dev': params['date_dev'].mean(),
        'sigma': params['sigma'].mean(),
    }

def save(MODEL):
    with sqlite3.connect("crossbot.db") as cursor:
        cursor.executemany("replace into model values(?, ?, ?, ?)", [
            (rec["uid"], rec["date"], rec["prediction"], rec["residual"])
            for rec in model["historic"]])
        
        cursor.execute("drop table if exists model_users")
        cursor.execute("""
CREATE TABLE IF NOT EXISTS model_users (
  uid text not null primary key,
  skill real not null,
  skill_25 real not null,
  skill_75 real not null,
); """)
        cursor.executemany("insert into model_user values(?,?,?,?)", [
            (user["uid"], user["skill"], user["skill_25"], user["skill_75"])
            for user in model["users"]])

        cursor.execute("drop table if exists model_dates")
        cursor.execute("""
CREATE TABLE IF NOT EXISTS model_dates (
  date integer not null primary key,
  difficulty real not null,
  difficulty_25 real not null,
  difficulty_75 real not null,
); """)
        cursor.execute("insert into model_dates values(?,?,?,?)", [
            (date["date"], date["difficulty"], date["difficulty_25"], date["difficulty_75"])
            for dates in model["dates"]])

        cursor.execute("drop table if exists model_params")
        cursor.execute("""
CREATE TABLE IF NOT EXISTS model_params (
  time real, time_25 real, time_75 real,
  satmult real, satmult_25 real, satmult_75 real,
  bgain real, bgain_25 real, bgain_75 real,
  bdecay real, bdecay_25 real, bdecay_75 real,
  skill_dev real, date_dev real, sigma real,
); """)
        cursor.execute("insert into model_params values(?,?,?,?,?,?,?,?,?)", (
            model["time"], model["time_25"], model["time_75"],
            model["satmult"], model["satmult_25"], model["satmult_75"],
            model['bgain'], model['bgain_25'], model['bgain_75'],
            model['bdecay'], model['bdecay_25'], model['bdecay_75'],
            model["skill_dev"], model["date_dev"], model["sigma"]))

def residuals(data, model):
    from math import log, exp
    for uid, date, dow, sec, n \
        in zip(data["uids"], data["dates"], data["dows"], data["secs"],
               nth(data["uids"], data["dates"], data["ts"])):
        user = [rec for rec in model["users"] if rec["uid"] == uid][0]
        day = [rec for rec in model["dates"] if rec["date"] == date][0]

        # Quick and dirty
        mean = model["time"] \
            + user["skill"] \
            + day["difficulty"] \
            + (model["satmult"] if dow == '6' else 1) \
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
    return fig

def plot_rdates(model):
    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    ax = fig.add_subplot(1, 1, 1)
    ax.xaxis_date(None)
    pts = sorted([(rec['date'], rec['residual']) for rec in model['historic'] if rec['date'] >= '2017'])
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
    pts = sorted([(d, rec['residual']) for d, rec in zip(nths, model['historic'])])
    ax.plot([d for d, r in pts], [r for d, r in pts], 'o')
    yhat = savgol_filter([r for d, r in pts], 101, 1)
    ax.plot([d for d, r in pts], yhat, 'red')
    ax.plot([d for d, r in pts], [ 0 for n, r in pts ], 'black')
    return fig

def plots(data, model, nameuser=lambda x: x):
    agg.FigureCanvasAgg(plot_dates(model)).print_figure("dates.pdf")
    agg.FigureCanvasAgg(plot_users(model, nameuser=nameuser)).print_figure("users.pdf")
    agg.FigureCanvasAgg(plot_rdates(model)).print_figure("res-dates.pdf")
    agg.FigureCanvasAgg(plot_rnth(data, model)).print_figure("res-nth.pdf")

def lookup_user(model, uid):
    return [u for u in model["users"] if u["uid"] == uid][0]

def judge_time(model, day, todays, person, time):
    from math import log, exp
    is_sat = datetime.strptime(day, "%Y-%m-%d").strftime("%w") == '6'

    nths = {u: [u_ for u_ in model["users"] if u_["uid"] == u][0]["nth"] for u in todays}
    ynth = [u_ for u_ in model["users"] if u_["uid"] == person][0]["nth"]

    csecs = [log(secs)
             - model["time"]
             - lookup_user(model, user)["skill"]
             - (model["satmult"] if is_sat else 1)
             - model['bgain'] * exp(-nths[user] / model['bdecay']) \
             for user, secs in todays.items()]
    difficulty = sum(csecs) / len(csecs)

    ysecs = log(time) - model["time"] - lookup_user(model, person)["skill"] \
        - (model["satmult"] if is_sat else 1) - difficulty \
        - model['bgain'] * exp(-ynth / model['bdecay'])
    return ysecs / model["sigma"]
        
def print_judgement(model, todays, date=None):
    today = date or datetime.today().strftime("%Y-%m-%d")
    judgements = { u: (t, judge_time(model, today, TEST, u, t)) for u, t in todays.items() }
    print("TEST = {")
    for u, (t, d) in sorted(judgements.items(), key=lambda x: x[1][0]):
        print("    \"{}\": {:>3}, # {:+.2f}".format(u, t, d))
    print("}")

DATA = data()
FIT = fit(DATA)
MODEL = extract_model(DATA, FIT)
summarize(MODEL)
plots(DATA, MODEL)
