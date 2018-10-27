import hashlib
import hmac
import time
import logging

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.gzip import gzip_page
from django.views.decorators.cache import cache_control
from django.contrib.auth.decorators import login_required

import settings

from .slack import handle_slash_command
from .models import MiniCrosswordTime, CrosswordTime, EasySudokuTime

logger = logging.getLogger(__name__)


# taken from https://api.slack.com/docs/verifying-requests-from-slack#a_recipe_for_security
def validate_slack_request(request):
    timestamp = request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP']

    if abs(time.time() - float(timestamp)) > 60 * 5:
        # The request timestamp is more than five minutes old.
        # It could be a replay attack, so let's ignore it.
        return False

    my_signature = 'v0=' + hmac.new(
        key=settings.SLACK_SECRET_SIGNING_KEY,
        msg=b'v0:' + bytes(timestamp, 'utf8') + b':' + request.body,
        digestmod=hashlib.sha256).hexdigest()

    slack_signature = request.META['HTTP_X_SLACK_SIGNATURE']

    return my_signature == slack_signature


@csrf_exempt
def slash_command(request):
    logger.debug('Request: %s', request)
    if request.method == 'POST':
        if not validate_slack_request(request):
            return HttpResponseBadRequest("Failed to validate")

        response = handle_slash_command(request)
        logger.debug('Slash command response: %s', response)
        if response:
            return JsonResponse(response)
        return HttpResponse('OK: ' + request.POST['text'])

    return HttpResponse('this is the slack endpoint')


TIME_MODELS = {
    'minicrossword': MiniCrosswordTime,
    'crossword': CrosswordTime,
    'easysudoku': EasySudokuTime
}


@login_required
@gzip_page
@cache_control(max_age=3600)
def times_rest_api(request, time_model='minicrossword'):
    if request.method != 'GET':
        return HttpResponseBadRequest("Bad method")

    # end_date = datetime.date.today()
    # if 'end' in request.GET:
    #     end_date = datetime.datetime.strptime(request.GET['end'], '%Y-%m-%d').date()

    # start_date = end_date - datetime.timedelta(days=10)
    # if 'start' in request.GET:
    #     start_date = datetime.datetime.strptime(request.GET['start'], '%Y-%m-%d').date()

    times = (TIME_MODELS[time_model].all_times().order_by('date').
             select_related('user'))

    return JsonResponse({
        'times': [{
            'user': str(t.user),
            'date': t.date,
            'seconds': t.seconds
        } for t in times],
        'timemodel':
        time_model,
        'start':
        times[0].date,
        'end':
        times[len(times) - 1].date,
    })
