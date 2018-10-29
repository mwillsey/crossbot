import json

from .parser import Parser, ParserException
from . import commands
from .handler import SlashCommandRequest, Message
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

        # If we have a direct message, go ahead and send it
        # TODO: make sure it's okay to send this before the first reply
        if response.direct_message:
            post_response(request.response_url,
                          json.dumps(response.direct_message.asdict()))

        # Send the ephemeral reply if it exists
        if response.ephemeral_message:
            return response.ephemeral_message.asdict()

        return None

    except ParserException as exn:
        message = Message(ephemeral=True)
        message.text = str(exn)
        return message.asdict()
