import json

from .parser import Parser, ParserException
from . import commands
from .message import SlashCommandRequest, Message
from .api import post_response

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
            post_response(
                request.response_url,
                json.dumps(response.ephemeral_message.asdict())
            )

            if response.ephemeral_message:
                post_response(
                    request.response_url,
                    json.dumps(response.direct_message.asdict())
                )
                return None
            return response.direct_message.asdict()

        if response.ephemeral_message:
            # If there's only an ephemeral message, command is always ephemeral
            return response.ephemeral_message.asdict()

        if response.direct_message:
            if response.ephemeral_command:
                post_response(
                    request.response_url,
                    json.dumps(response.direct_message.asdict())
                )
                return None
            return response.direct_message.asdict()

        return None

    except ParserException as exn:
        message = Message(ephemeral=True)
        message.text = str(exn)
        return message.asdict()
