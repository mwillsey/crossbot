import logging
import math

from django.utils import timezone
from . import models, SlashCommandResponse

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser(
        'predictor', help='Get information on the Crossbot predictor'
    )
    parser.set_defaults(command=predictor)
    parser.add_argument(
        'cmd',
        default='details',
        help="What information to print about the predictor",
        nargs='?'
    )


def predictor(request):
    if request.args.cmd == 'details':
        return SlashCommandResponse(text=details())
    elif request.args.cmd == 'validate':
        return SlashCommandResponse(text=validate())
    else:
        return SlashCommandResponse(
            text="Error: no known predictor command `{}`"
            .format(request.args.cmd)
        )


def details():
    params = models.PredictionParameter.objects.order_by('when_run')[:1].get()
    return "*Last model run*: {:%Y-%m-%d %H:%M}\n*log(P)* = {}".format(
        timezone.localtime(params.when_run), params.lp
    )


def validate():
    predictions = list(models.Prediction.objects.all())
    lsecs = []
    psecs = []

    for i, p in enumerate(predictions):
        secs = p.time.seconds
        lsecs.append(math.log(secs if 0 < secs < 300 else 300))
        psecs.append(p.prediction)

    avg = sum(lsecs) / len(lsecs)
    baseline = sum((s - avg)**2 for s in lsecs) / len(lsecs)
    model = sum((s - p)**2 for s, p in zip(lsecs, psecs)) / len(lsecs)
    return "*Mean squared error*: {:.3f} vs {:.3f} baseline".format(
        model, baseline
    )
