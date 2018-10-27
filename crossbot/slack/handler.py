import logging
import traceback

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
            request.reply(str(exn), direct=True)


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


class SlashCommandRequest:
    def __init__(self, post_data, in_channel=False):
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

    def reply(self, msg, direct=False):
        self.replies.append(msg)

    # note, this one is not delayed
    def message_and_react(self, msg, emoji, as_user=None):
        if as_user:
            name = as_user.slack_fullname or as_user.slackname or 'crossbot'
            kwargs = {
                'as_user': 'false',
                'icon_url': as_user.image_url,
                'username': name,
            }
        else:
            kwargs = {}

        timestamp = post_message(self.channel, text=msg, **kwargs)
        react(emoji, self.channel, timestamp)

    def attach(self, name, path):
        self.attachments.append({
            'fallback': 'its a picture',
            'pretext': name,
            'image_url': path
        })

    def response_json(self):
        return {
            'response_type': 'in_channel' if self.in_channel else 'ephemeral',
            'text': '\n'.join(self.replies),
            'attachments': self.attachments,
        }

_HANDLER = Handler()


def handle_slash_command(slash_command):
    """Convenience methods used to handle slash commands.

    Args:
        slash_command: str

    Returns:
        A Response object or None. (??)
    """
    request = SlashCommandRequest(slash_command)

    _HANDLER.handle_request(request)
    return request.response_json()
    
