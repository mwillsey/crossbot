import hmac
import hashlib
import time
import keys
import re

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

import crossbot
import crossbot.handler

# taken from https://api.slack.com/docs/verifying-requests-from-slack#a_recipe_for_security
def validate_slack_request(request):
    timestamp = request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP']

    if abs(time.time() - float(timestamp)) > 60 * 5:
        # The request timestamp is more than five minutes old.
        # It could be a replay attack, so let's ignore it.
        return False

    my_signature = 'v0=' + hmac.new(
        key = keys.SLACK_SECRET_SIGNING_KEY,
        msg = b'v0:' + bytes(timestamp, 'utf8') + b':' + request.body,
        digestmod = hashlib.sha256
    ).hexdigest()

    slack_signature = request.META['HTTP_X_SLACK_SIGNATURE']

    return my_signature == slack_signature


re_prog = re.compile(r'(cb|crossbot)(?:$| +)(.*)')
cb = crossbot.handler.Handler()

@csrf_exempt
def event(request):
    if request.method == 'POST':
        if not validate_slack_request(request):
            return HttpResponseBadRequest("Failed to validate")

        # respond the to slack events challenge
        if request.POST.get('type') == 'url_verification':
            return HttpResponse(request.POST['challenge'])

        assert request.POST['type'] == 'event_callback'
        data = request.POST['event']

        match = re_prog.match(data.get("text"))
        if match:
            # get rid of the mention of the app
            data["text"] = match[2]

            cbreq = crossbot.slack.SlackEventRequest(data)
            cb.handle_request(cbreq)
            print(response)
            return JsonResponse(response)

@csrf_exempt
def slash_command(request):
    if request.method == 'POST':
        if not validate_slack_request(request):
            return HttpResponseBadRequest("Failed to validate")

        print(request.POST)
        cbreq = crossbot.slack.SlackRequest(request.POST)
        cb.handle_request(cbreq)

        response = cbreq.response_json()

        print(response)
        if response:
            return JsonResponse(response)
        else:
            return HttpResponse('OK: ' + request.POST['text'])


        return HttpResponse('OK: ' + request.POST['text'])

    return HttpResponse('this is the slack endpoint')
