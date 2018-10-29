import logging
import math

from datetime import datetime

from . import models

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser('model', help='Run a saved query')
    parser.set_defaults(command=model)
    parser.add_argument(
        'cmd',
        default='details',
        help="What information to print about the model",
        nargs='?')


def model(request):
    if request.args.cmd == 'details':
        latest_run_time = models.ModelParams.objects.latest('when_run')
        model_params = models.ModelParams.objects.get(when_run=latest_run_time)
        request.reply(
            "*Last model run*: {:%Y-%m-%d %H:%M}\n*log(P)* = {}".format(
                datetime.fromtimestamp(model_params.when_run),
                model_params.lp))

    elif request.args.cmd == 'validate':
        # TODO: make these queries more efficient, figure out how to join
        #       properly
        lsecs = []
        predictions = []
        for model in models.MiniCrosswordModel.all():
            try:
                time = models.MiniCrosswordTime.all_times().get(
                    user__slackid=model.uid, date=model.date)
            except models.MiniCrosswordTime.DoesNotExist:
                logger.warning("Couldn't find time for %s on %s", model.uid,
                               model.date)
                continue

            lsecs.append(
                math.log(time.seconds if 0 < time.seconds < 300 else 300))
            predictions.append(model.prediction)

        avg = sum(lsecs) / len(lsecs)
        baseline = sum((s - avg)**2 for s in lsecs) / len(lsecs)
        model = sum(
            (s - p)**2 for s, p in zip(lsecs, predictions)) / len(lsecs)
        request.reply("*Mean squared error*: {:.3f} vs {:.3f} baseline".format(
            model, baseline))

    else:
        request.reply("Error: no known model command `{}`".format(
            request.args.cmd))
