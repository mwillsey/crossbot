"""Methods for sending requests directly to Slack."""

import requests
import settings
import logging

logger = logging.getLogger(__name__)

SLACK_URL = 'https://slack.com/api/'

# TODO: clean up the kind-of funky args/kwargs flows


def _slack_api(endpoint='',
               method='POST',
               base_url=None,
               headers=None,
               **kwargs):
    assert method in ['GET', 'POST']

    headers = headers if headers is not None else {}
    headers['Authorization'] = 'Bearer ' + settings.SLACK_OAUTH_ACCESS_TOKEN

    url = base_url if base_url is not None else SLACK_URL
    url += endpoint

    if method == 'GET':
        func = requests.get
    elif method == 'POST':
        func = requests.post
    else:
        raise ValueError('invalid method: ' + method)

    return func(url, headers=headers, **kwargs)


def _slack_api_ok(key, *args, **kwargs):
    resp = _slack_api(*args, **kwargs).json()
    if resp.get('ok'):
        return resp[key]

    logger.error('bad response: %s', resp)
    raise ValueError('bad response: ' + resp.get('error'))


def slack_users():
    return _slack_api_ok('members', endpoint='users.list', method='GET')


def post_message(channel, **kwargs):
    kwargs['channel'] = channel
    return _slack_api_ok('ts', endpoint='chat.postMessage', params=kwargs)


def post_response(response_url, json):
    # For some bizarre reason, response_url doesn't work the same as postMessage
    resp = _slack_api(base_url=response_url, data=json)
    return resp.text == 'ok'
