import requests
import keys

SLACK_URL = 'https://slack.com/api/'

def slack_api(endpoint, method, **kwargs):
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

def slack_api_ok(endpoint, method, key, **kwargs):
    resp = slack_api(endpoint, method).json()
    if resp.get('ok'):
        return resp[key]
    else:
        raise ValueError('bad response: ' + resp.get('error'))

def slack_users():
    return slack_api_ok('users.list', 'GET', 'members')
