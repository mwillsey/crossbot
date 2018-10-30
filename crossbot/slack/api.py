"""Methods for sending requests directly to Slack."""

import json
import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

SLACK_URL = 'https://slack.com/api/'


def _slack_api(
        *, endpoint='', method='POST', base_url=None, headers=None, **kwargs
):
    assert method in ['GET', 'POST']

    headers = headers if headers is not None else {}
    headers['Authorization'] = (
        'Bearer ' + settings.SLACK_OAUTH_BOT_ACCESS_TOKEN
    )

    url = base_url if base_url is not None else SLACK_URL
    url += endpoint

    if method == 'GET':
        func = requests.get
    elif method == 'POST':
        func = requests.post
    else:
        raise ValueError('invalid method: ' + method)

    return func(url, headers=headers, **kwargs)


def _slack_api_ok(key, **kwargs):
    resp = _slack_api(**kwargs).json()
    if resp.get('ok'):
        return resp[key]

    logger.error('bad response: %s', resp)
    raise ValueError('bad response: ' + resp.get('error'))


def slack_user(user_id):
    return _slack_api_ok(
        'user', endpoint='users.info', method='GET', params={'user': user_id}
    )


def slack_users():
    return _slack_api_ok('members', endpoint='users.list', method='GET')


def post_message(channel, message_dict):
    message_dict['channel'] = channel
    return _slack_api_ok(
        'ts',
        endpoint='chat.postMessage',
        data=json.dumps(message_dict),
        headers={'Content-Type': 'application/json'},
    )


def post_response(response_url, message_dict):
    # For some bizarre reason, response_url doesn't work the same as postMessage
    resp = _slack_api(
        base_url=response_url,
        data=json.dumps(message_dict),
        headers={'Content-Type': 'application/json'}
    )
    return resp.text == 'ok'


def react(emoji, channel, timestamp):
    return _slack_api_ok(
        'ok',
        endpoint='reactions.add',
        params={
            'name': emoji,
            'channel': channel,
            'timestamp': timestamp,
        }
    )
