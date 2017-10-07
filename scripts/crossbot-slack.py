#!/usr/bin/env python3

import os
import re
from threading import Thread
from slackclient import SlackClient
from slackeventsapi import SlackEventAdapter

import crossbot

import logging
log = logging.getLogger(__name__)

# grab the necessary slack secrets from the environment
client_id = os.environ.get("SLACK_CLIENT_ID")
client_secret = os.environ.get("SLACK_CLIENT_SECRET")
verification = os.environ.get("SLACK_VERIFICATION_TOKEN")
api_token = os.environ.get("SLACK_API_TOKEN")
api_bot_token = os.environ.get("SLACK_API_BOT_TOKEN")

slack_client = SlackClient(api_token)
slack_bot_client = SlackClient(api_bot_token)


def api(endpoint, response_key=None, as_bot=True, **kwargs):
    sc = slack_bot_client if as_bot else slack_client
    response = sc.api_call(endpoint, **kwargs)
    if response.get('ok'):
        if response_key:
            return response[response_key]
    else:
        log.error('API failure')
        log.error(response)


# SlackEventAdapter is just a thin shim on top of a Flask app that does special
# stuff with requests to the "/slack" endpoint
app = SlackEventAdapter(verification, "/slack")


class SlackCrossbot(crossbot.Crossbot):

    def __init__(self, userid, **kwargs):
        self.userid = userid
        self.users = {}
        self.update_users()
        super().__init__(self, **kwargs)

    def update_users(self):
        # need real api access for this, not bot
        users_list = api('users.list', 'members', as_bot=False)
        self.users.update((u['id'], u) for u in users_list)

    def user(self, userid):
        """ Returns the username associated with the given id"""
        try:
            return self.users[userid]['name']
        except KeyError:
            log.warning('userid "{}" not found'.format(userid))
            return str(userid)


# FIXME get bot user id from somewhere
bot = SlackCrossbot("U7CC1KX70")

# recognize commands prefixed by cb, crossbot, or @-mention
re_prog = re.compile(r'(cb|crossbot|<@{}>)(?:$| +)(.*)'.format(bot.userid))


class SlackRequest(crossbot.Request):

    def __init__(self, message):
        self.message = message
        self.text    = message['text']
        self.userid  = message['user']

    def react(self, emoji):
        api(
            "reactions.add",
            name = emoji,
            channel = self.message['channel'],
            timestamp = self.message['ts']
        )

    def reply(self, msg, direct=False):

        if direct:
            api(
                "chat.postEphemeral",
                user = self.message['user'],
                channel = self.message['channel'],
                text = msg
            )
        else:
            api(
                "chat.postMessage",
                channel = self.message['channel'],
                text = msg
            )

    def upload(self, name, path):
        with open(path, 'rb') as f:
            api(
                "files.upload",
                filename=name,
                channels=self.message['channel'],
                file=f)
        os.remove(path)


@app.server.route("/hello", methods=["GET"])
def thanks():
    return "hello from crossbot"


# Using the Slack Events Adapter, when we receive a message event
@app.on("message")
def handle_message_event(event_data):
    # Grab the message from the event payload
    message = event_data["event"]
    thread = Thread(target=handle_message, args=(message,))
    thread.start()

def handle_message(message):
    # if the user says hello
    match = re_prog.match(message.get("text"))
    if match:
        log.info("Crossbot message: " + message.get("text"))
        # get rid of the mention of the app
        message["text"] = match[2]
        # have our bot respond to the message
        slack_request = SlackRequest(message)
        try:
            bot.handle_request(slack_request)
        except crossbot.ParserException as exn:
            slack_request.reply(str(exn), direct=True)
    else:
        log.info("Not a crossbot message: " + message.get("text"))


@app.server.before_first_request
def before_first_request():
    if not client_id:
        log.error("Can't find Client ID, did you set this env variable?")
    if not client_secret:
        log.error("Can't find Client Secret, did you set this env variable?")
    if not verification:
        log.error("Can't find Verification Token, did you set this env variable?")


if __name__ == '__main__':
    # log everything to stdout and to a file
    logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(message)s',
            handlers = [
                logging.FileHandler("crossbot.log"),
                logging.StreamHandler()
                ],
            )

    app.server.run(debug=True, host='0.0.0.0', port=51234)
