import json
import logging
import traceback

from django.contrib.staticfiles.templatetags.staticfiles import static

from . import commands
from .commands import COMMANDS
from .parser import Parser, ParserException
from .api import *
from ..models import CBUser

logger = logging.getLogger(__name__)


class Handler:
    def __init__(self, limit_commands=False):
        self.parser = Parser(limit_commands)
        self.init_plugins()

    def init_plugins(self):
        for mod_name in COMMANDS:
            try:
                mod = getattr(commands, mod_name)

                # hopefully the plugins will add themselves to subparsers
                if hasattr(mod, 'init'):
                    mod.init(self)
                else:
                    logger.warning('plugin "%s" has no init()', mod.__name__)
            except:
                logger.error('Something went wrong when importing "%s"',
                             mod_name)
                traceback.print_exc()

    def handle_request(self, request, parse=True):
        """ Parses the request and calls the right command.

        If parsing fails, this raises crossbot.parser.ParserException.
        """

        try:
            if parse:
                command, args = self.parser.parse(request.text)
                request.args = args
            else:

                command = request.command

            return command(request)
        except ParserException as exn:
            request.reply(str(exn))


# XXX: why is this even here?
class Request:
    userid = 'command-line-user'

    def __init__(self, text):
        self.text = text

    def react(self, emoji):
        logger.debug('react :{}:'.format(emoji))

    def reply(self, msg, direct=False):
        prefix = '@user - ' if direct else ''
        logger.debug(prefix + msg)

    def attach(self, name, path):
        logger.debug(path)


# TODO: this class and related classes/api methods need refactoring
class SlashCommandRequest:
    def __init__(self, request, in_channel=False):
        self._django_request = request

        post_data = request.POST

        self.text = post_data['text']
        self.response_url = post_data['response_url']
        self.trigger_id = post_data['trigger_id']
        self.channel = post_data['channel_id']

        self.slackid = post_data['user_id']
        self.user = CBUser.from_slackid(
            slackid=post_data['user_id'], slackname=post_data['user_name'])

        self.in_channel = in_channel
        self.replies = []
        self.attachments = []

        self.as_user_image = False

    def build_absolute_uri(self, location):
        return self._django_request.build_absolute_uri(location)

    def reply(self, msg):
        self.replies.append(msg)

    # note, this one is not delayed
    def message_and_react(self, msg, emoji, as_user=None, send_hat=False):
        kwargs = {}

        if as_user:
            name = as_user.slack_fullname or as_user.slackname or 'crossbot'
            kwargs['as_user'] = 'false'
            kwargs['icon_url'] = as_user.image_url
            kwargs['username'] = name

        timestamp = post_message(self.channel, text=msg, **kwargs)
        react(emoji, self.channel, timestamp)

    def attach(self, attachment):
        self.attachments.append(attachment)

    def attach_image(self, name, path):
        self.attachments.append({
            'fallback': 'its a picture',
            'pretext': name,
            'image_url': path,
        })

    def add_field(self, title, value, short=True):
        """Adds a field to the first attachment of the reply."""
        if not self.attachments:
            self.attachments.append({})
        attachment = self.attachments[0]
        if not 'fields' in attachment:
            attachment['fields'] = []
        attachment['fields'].append({
            'title': title,
            'value': value,
            'short': short,
        })

    def response_json(self):
        response = {}
        if self.replies:
            response['text'] = '\n'.join(self.replies)
        if self.attachments:
            response['attachments'] = json.dumps(self.attachments)
        if self.user.hat:
            response['as_user'] = json.dumps(False)
            response['username'] = 'crossbot'
            response['icon_url'] = self.build_absolute_uri(
                self.user.hat.image_url())
        post_message(self.channel, **response)

        return {'text': 'ok'}
