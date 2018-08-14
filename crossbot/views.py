import hmac
import hashlib
import time
import secrets

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

# taken from https://api.slack.com/docs/verifying-requests-from-slack#a_recipe_for_security
def validate_slack_request(request):
    print(request.META)
    timestamp = request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP']

    if abs(time.time() - float(timestamp)) > 60 * 5:
        # The request timestamp is more than five minutes from local time.
        # It could be a replay attack, so let's ignore it.
        return False


    my_signature = 'v0=' + hmac.new(
        key = secrets.SLACK_SECRET_SIGNING_KEY,
        msg = b'v0:' + bytes(timestamp, 'utf8') + b':' + request.body,
        digestmod = hashlib.sha256
    ).hexdigest()

    slack_signature = request.META['HTTP_X_SLACK_SIGNATURE']

    return my_signature == slack_signature


@csrf_exempt
def slash_command(request):
    if request.method == 'POST':
        return HttpResponse(validate_slack_request(request))

    return HttpResponse("Hello, world. You're at my index.")
