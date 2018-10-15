"""Methods for sending requests directly to Slack."""

import requests
import keys

SLACK_URL = 'https://slack.com/api/'

def _slack_api(endpoint, method, **kwargs):
    assert method in ['GET', 'POST']
    headers = {'Authorization': 'Bearer ' + keys.SLACK_OAUTH_ACCESS_TOKEN}
    url = SLACK_URL + endpoint

    if method == 'GET':
        func = requests.get
    elif method == 'POST':
        func = requests.post
    else:
        raise ValueError('invalid method: ' + method)

    return func(url, headers=headers, params=kwargs)

def _slack_api_ok(endpoint, method, key, **kwargs):
    resp = _slack_api(endpoint, method, **kwargs).json()
    if resp.get('ok'):
        return resp[key]

    raise ValueError('bad response: ' + resp.get('error'))

def slack_users():
    return _slack_api_ok('users.list', 'GET', 'members')

def react(emoji, channel, timestamp):
    return _slack_api_ok('reactions.add', 'POST', 'ok', name=emoji, channel=channel, timestamp=timestamp)

def post_message(channel, **kwargs):
    return _slack_api_ok('chat.postMessage', 'POST', 'ts', channel=channel, **kwargs)
