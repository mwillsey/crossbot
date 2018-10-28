
from .parser import Parser, ParserException
from . import commands
from .handler import SlashCommandResponse, Attachment

PARSER = Parser()

for mod_name in commands.COMMANDS:
    mod = getattr(commands, mod_name)
    mod.init(PARSER)


def handle_request(request):
    """ Parses the request and calls the right command. """

    try:
        command, args = PARSER.parser.parse(request.text)
        request.args = args

        response = command(request)

    except ParserException as exn:
        response = SlashCommandResponse()
        response.text = str(exn)

    return response
