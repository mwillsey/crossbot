#!/usr/bin/env python

import sys

# this script is the same name as a the library, so we need to bump the first
# the directory in the path (which is the directory the interpreter was invoked
# from) to the end of the list so the import actually finds the library
interpeter_dir = sys.path[0]
sys.path = sys.path[1:]
sys.path.append(interpeter_dir)

from crossbot.client import *

# no API_TOKEN
# use environment variable SLACKBOT_API_TOKEN instead

# no @ needed
ERRORS_TO = 'mwillsey'


if __name__ == "__main__":
    if sys.argv[1] == 'slack':
        from slackbot.bot import Bot, default_reply

        bot = Bot()
        client = SlackClient(bot)

        @default_reply
        def handle(message):
            request = SlackRequest(message)
            client.handle_request(request)

        print('crossbot is up and listening to Slack!')
        bot.run()
        exit(1)

    client  = CommandLineClient()
    request = CommandLineRequest(' '.join(sys.argv[1:]))
    client.handle_request(request)
