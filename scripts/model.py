#!/usr/bin/env python3
from __future__ import print_function

import pystan
import sqlite3
from datetime import datetime, timedelta
import time
import matplotlib, matplotlib.dates, matplotlib.figure, matplotlib.ticker
from scipy.signal import savgol_filter
from scipy.stats import norm
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
         uids, dates, dows, secs, ts = zip(*cursor.execute("select userid, date, strftime('%w', date), seconds, case when timestamp is null then date else timestamp end from mini_crossword_time"))
         return { 'uids': uids, 'dates': dates, 'dows': dows, 'secs': secs, 'ts': ts }

def nth(uids, dates, ts):
    uid_dates = { the_uid: sorted([t for uid, t in zip(uids, ts) if uid == the_uid])
                  for the_uid in set(uids) }
    return [ bisect.bisect(uid_dates[uid], ts) + 1
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
    fm = sm.sampling(data=munge_data(**data), iter=1000, chains=4, pars=[
        'date_effect', 'skill_effect', 'predictions', 'residuals',
        'beginner_gain', 'beginner_decay', 'sat_effect', 'mu',
        'skill_dev', 'date_dev', 'sigma'
    ])
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
        'sigma': params['sigma'].mean(), "lp": params["lp__"].mean(),
        'when_run': time.time()
    }

def sqlsave(cursor, table, models, fields):
    cursor.executemany("insert into {} values({})".format(table, ",".join("?" for f in fields)), [
        [model[f] for f in fields] for model in models])

def sqldefs(*fields):
    return ", ".join(f + " real not null" for f in fields)

def save(model):
    with sqlite3.connect("crossbot.db") as cursor:
        cursor.executemany("replace into mini_crossword_model values(?, ?, ?, ?)", [
            (rec["uid"], rec["date"], rec["prediction"], rec["residual"])
            for rec in model["historic"]])
        
        user_fields = ["skill", "skill_25", "skill_75"]
        cursor.execute("drop table if exists model_users")
        cursor.execute("CREATE TABLE model_users (uid text not null primary key, nth integer not null, {});"
                       .format(sqldefs(*user_fields)))
        sqlsave(cursor, "model_users", model["users"], ["uid", "nth"] + user_fields)

        date_fields = ["difficulty", "difficulty_25", "difficulty_75"]
        cursor.execute("drop table if exists model_dates")
        cursor.execute("CREATE TABLE model_dates (date integer not null primary key, {});"
                       .format(sqldefs(*date_fields)))
        cursor.executemany("insert into model_dates values(?,?,?,?)", [
            (time.mktime(datetime.strptime(date["date"], "%Y-%m-%d").timetuple()), date["difficulty"], date["difficulty_25"], date["difficulty_75"])
            for date in model["dates"]])

        param_fields = ["time", "time_25", "time_75", "satmult", "satmult_25", "satmult_75",
                        "bgain", "bgain_25", "bgain_75", "bdecay", "bdecay_25", "bdecay_75",
                        "skill_dev", "date_dev", "sigma", "lp", "when_run"]
        cursor.execute("drop table if exists model_params")
        cursor.execute("CREATE TABLE model_params ({});".format(sqldefs(*param_fields)))
        sqlsave(cursor, "model_params", [model], param_fields)

def sqlload(cursor, table, *fields):
    return [{f: v for f, v in zip(fields, rec)} for rec in cursor.execute("select * from " + table)]

def load():
    with sqlite3.connect("crossbot.db") as cursor:
        model, = sqlload(cursor, "model_params;",
                         "time", "time_25", "time_75", "satmult", "satmult_25", "satmult_75",
                         "bgain", "bgain_25", "bgain_75", "bdecay", "bdecay_25", "bdecay_75",
                         "skill_dev", "date_dev", "sigma", "lp")

        model["dates"] = sqlload(cursor, "model_dates",
                                 "date", "difficulty", "difficulty_25", "difficulty_75")
        for d in model["dates"]:
            d["date"] = datetime.fromtimestamp(d["date"]).strftime("%Y-%m-%d")
        model["users"] = sqlload(cursor, "model_users",
                                 "uid", "nth", "skill", "skill_25", "skill_75")
        model["historic"] = sqlload(cursor, "mini_crossword_model",
                                    "uid", "date", "prediction", "residual")
        return model

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
    pts = sorted([(rec['date'], rec['residual']) for rec in model['historic'] if rec['date'] >= '2017'])

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    gs = matplotlib.gridspec.GridSpec(1, 2, width_ratios=[3, 1]) 
    gs.update(wspace=0.025)

    ax = fig.add_subplot(gs[0])
    ax.xaxis_date(None)
    dates = [datetime.strptime(d, "%Y-%m-%d") for d, r in pts]
    dates_ = matplotlib.dates.date2num(dates)
    color = [(0, 0, 1, 1.0 / list(dates_).count(d)) for d in dates_]
    ax.scatter(dates_, [r for d, r in pts], c=color, marker='o')
    yhat = savgol_filter([r for d, r in pts], 101, 1)
    ax.plot(dates_, yhat, 'red')
    ax.plot(dates_, [ 0 for n, r in pts ], 'black')

    ax2 = fig.add_subplot(gs[1], sharey=ax)
    ax2.tick_params('both', left=False, labelleft=False, bottom=False, labelbottom=False)
    ax2.hist([r for d, r in pts], orientation="horizontal")

    return fig

def plot_rnth(data, model, user=None):
    nths = nth(data['uids'], data['dates'], data['ts'])
    pts = sorted([(d, rec['residual']) for d, rec in zip(nths, model['historic'])
                  if user is None or rec["uid"] == user])
    nths_ = [d for d, r in pts]

    fig = matplotlib.figure.Figure(figsize=(11, 8.5))
    gs = matplotlib.gridspec.GridSpec(1, 2, width_ratios=[3, 1]) 
    gs.update(wspace=0.025)

    color = [(0, 0, 1, 1.0 / nths_.count(d)) for d, r in pts]
    ax = fig.add_subplot(gs[0])
    ax.scatter([d for d, r in pts], [r for d, r in pts], c=color, marker='o')
    window = 101 if not user else (len(pts) // 10 * 2 + 1)
    yhat = savgol_filter([r for d, r in pts], window, 1)
    ax.plot([d for d, r in pts], yhat, 'red')
    ax.plot([d for d, r in pts], [ 0 for n, r in pts ], 'black')

    ax2 = fig.add_subplot(gs[1], sharey=ax)
    ax2.tick_params('both', left=False, labelleft=False, bottom=False, labelbottom=False)
    ax2.hist([r for d, r in pts], orientation="horizontal")

    return fig

def plots(data, model, nameuser=lambda x: x):
    agg.FigureCanvasAgg(plot_dates(model)).print_figure("dates.pdf")
    agg.FigureCanvasAgg(plot_users(model, nameuser=nameuser)).print_figure("users.pdf")
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
    z_diff = diff_means / (math.sqrt(stdev**2 / len(play) + stdev**2 / len(dont)))
    return norm.cdf(z_diff)

def selsubs(data, model, alpha=0.01):
    info = {user['uid']: selsub(data, model, user['uid']) for user in model['users']}
    # Two-tailed test, but no Bonferroni correction since we want all outputs
    alpha /= 2
    for u, p in sorted(info.items(), key=lambda x: x[1], reverse=True):
        if p > 1 - alpha or 0 < p < alpha: print(u, p)

if __name__ == "__main__":
    DATA = data()
    FIT = fit(DATA)
    MODEL = extract_model(DATA, FIT)
    save(MODEL)
