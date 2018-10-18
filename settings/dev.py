#pylint: disable=wildcard-import,unused-wildcard-import
from settings.base import *

# django stuff
SECRET_KEY = 'my_django_secret_key'

# slack stuff
SLACK_SECRET_SIGNING_KEY = b'my_secret_slack_key'
SLACK_OAUTH_ACCESS_TOKEN = 'my_slack_oauth'
SLACK_OAUTH_BOT_ACCESS_TOKEN = 'my_slack_bot_oauth'

# Slack OAuth stuff
SOCIAL_AUTH_SLACK_KEY = 'slack-client-id'
SOCIAL_AUTH_SLACK_SECRET = 'slack-client-secret'

CROSSBOT_SOCIAL_AUTH_SLACK_ALLOWED_TEAMS = [] # Insert team IDs here
