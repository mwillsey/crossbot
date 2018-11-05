import logging
import math

from datetime import datetime

from . import models, SlashCommandResponse

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser(
        'predictor', help='Get information on the Crossbot predictor'
    )
    parser.set_defaults(command=model)
    parser.add_argument(
        'cmd',
        default='details',
        help="What information to print about the model",
        nargs='?'
    )


def model(request):
    if request.args.cmd == 'details':
        params = models.PredictionParameter.objects.order_by('when_run'
                                                             )[:1].get()
        return SlashCommandResponse(
            text="*Last model run*: {:%Y-%m-%d %H:%M}\n*log(P)* = {}"
            .format(params.when_run, params.lp)
        )

    elif request.args.cmd == 'validate':
        # TODO: make these queries more efficient, figure out how to join
        #       properly
        lsecs = []
        predictions = []
        for prediction in models.Prediction.objects.all():
            try:
                time = models.MiniCrosswordTime.all_times().get(
                    user=prediction.user, date=prediction.date
                )
            except models.MiniCrosswordTime.DoesNotExist:
                logger.warning(
                    "Couldn't find time for %s on %s", prediction.uid,
                    prediction.date
                )
                continue

            lsecs.append(
                math.log(time.seconds if 0 < time.seconds < 300 else 300)
            )
            predictions.append(prediction.prediction)

        avg = sum(lsecs) / len(lsecs)
        baseline = sum((s - avg)**2 for s in lsecs) / len(lsecs)
        model = sum((s - p)**2
                    for s, p in zip(lsecs, predictions)) / len(lsecs)
        return SlashCommandResponse(
            text="*Mean squared error*: {:.3f} vs {:.3f} baseline"
            .format(model, baseline)
        )

    else:
        return SlashCommandResponse(
            text="Error: no known model command `{}`".format(request.args.cmd)
        )
