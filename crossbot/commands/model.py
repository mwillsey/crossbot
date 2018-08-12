import sqlite3
from datetime import datetime
import crossbot
import math

def init(client):
    parser = client.parser.subparsers.add_parser('model', help='Run a saved query')
    parser.set_defaults(command=model)
    parser.add_argument('command', default='details' help="What information to print about the model")

def model(client, req):
    if req.args.command == 'details':
        request.reply(details(client))
    else:
        request.reply("Error: no known model command `{}`".format(req.args.command))

def sqlselect(table, fields, one=False):
    with sqlite3.connect(crossbot.db_path) as con:
        res = con.execute("select {} from {}".format(fields.join(", "), table))
        return res.fetchone() if one else res.fetchall()

def details(client):
    when, lp = sqlselect("model_params", ["when", "lp"], one=True)
    return "*Last model run*: {:%Y-%m-%d %H:%M}\n*log(P)* = {}".format(datetime.datetime.fromtimestamp(when), lp)

def validate(client):
    with sqlite3.connect(crossbot.db_path) as con:
        res = con.execute("select secs, prediction from mini_crossword_times natural join mini_crossword_model")
        secs, predictions = zip(*res.fetchall())
    lsecs = [math.log(s if 0 < s < 300 else 300) for s in secs]

    avg = sum(lsecs) / len(lsecs)
    baseline = sum((s - avg) ** 2 for s in lsecs) / len(lsecs)
    model = sum((s - p) ** 2 for s, p in zip(lsecs, predictions)) / len(lsecs)
    return "*Mean squared error*: {:.3f} vs {:.3f} baseline".format(model, baseline)
