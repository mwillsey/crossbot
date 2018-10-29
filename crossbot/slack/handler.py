import json

from django.conf import settings

from .parser import Parser, ParserException
from . import commands
from .message import SlashCommandRequest, Message
from .api import post_response, post_message, react

PARSER = Parser()

for mod_name in commands.COMMANDS:
    mod = getattr(commands, mod_name)
    mod.init(PARSER)


def handle_slash_command(django_request):
    """ Parses the request and calls the right command.

    Args:
        django_request: A Django request object.

    Returns:
        A dict describing the message to return, or None if the view should
        simply return an HTTP 200 response."""
    try:
        request = SlashCommandRequest(django_request)
        command, args = PARSER.parse(django_request.POST['text'])
        request.args = args
        response = command(request)  # returns a SlackCommandResponse

        if response.ephemeral_message and response.direct_message:
            # Send ephemeral instead of returning it so it appears first
            _send_message(request, response.ephemeral_message)

            if response.ephemeral_message:
                _send_message(request, response.direct_message)
                return None
            return _send_message(
                request, response.direct_message, should_return=True
            )

        if response.ephemeral_message:
            # If there's only an ephemeral message, command is always ephemeral
            return _send_message(
                request, response.ephemeral_message, should_return=True
            )

        if response.direct_message:
            if response.ephemeral_message:
                _send_message(request, response.direct_message)
                return None
            # TODO: what if we have to react to this message?
            #       we shouldn't return None then, should at least return with
            #       response_type: in_channel or something
            return _send_message(
                request, response.direct_message, should_return=True
            )

        return None

    except ParserException as exn:
        message = Message(ephemeral=True)
        message.text = str(exn)
        return message.asdict()


def _send_message(request, message, should_return=False):
    if not message.reactions or not _in_main_channel(request):
        if should_return:
            return message.asdict()
        post_response(request.response_url, json.dumps(message.asdict()))
        return None

    timestamp = post_message(request.channel, json.dumps(message.asdict()))
    for reaction in message.reactions:
        react(reaction, request.channel, timestamp)
    return None


def _in_main_channel(request):
    return request.channel == getattr(settings, 'CROSSBOT_MAIN_CHANNEL', None)
