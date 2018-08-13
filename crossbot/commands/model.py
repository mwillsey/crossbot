import sqlite3
from datetime import datetime
import crossbot
import math

def init(client):
    parser = client.parser.subparsers.add_parser('model', help='Run a saved query')
    parser.set_defaults(command=model)
    parser.add_argument('cmd', default='details', help="What information to print about the model", nargs = '?')

def model(client, request):
    if request.args.cmd == 'details':
        request.reply(details(client))
    elif request.args.cmd == 'validate':
        request.reply(validate(client))
    else:
        request.reply("Error: no known model command `{}`".format(request.args.cmd))

def sqlselect(table, fields, one=False):
    with sqlite3.connect(crossbot.db_path) as con:
        print("select {} from {}".format(', '.join(fields), table))
        res = con.execute("select {} from {}".format(', '.join(fields), table))
        return res.fetchone() if one else res.fetchall()

def details(client):
    when, lp = sqlselect("model_params", ["when_run", "lp"], one=True)
    return "*Last model run*: {:%Y-%m-%d %H:%M}\n*log(P)* = {}".format(datetime.fromtimestamp(when), lp)

def validate(client):
    with sqlite3.connect(crossbot.db_path) as con:
        res = con.execute("select seconds, prediction from mini_crossword_time natural join mini_crossword_model")
        secs, predictions = zip(*res.fetchall())
    lsecs = [math.log(s if 0 < s < 300 else 300) for s in secs]

    avg = sum(lsecs) / len(lsecs)
    baseline = sum((s - avg) ** 2 for s in lsecs) / len(lsecs)
    model = sum((s - p) ** 2 for s, p in zip(lsecs, predictions)) / len(lsecs)
    return "*Mean squared error*: {:.3f} vs {:.3f} baseline".format(model, baseline)
