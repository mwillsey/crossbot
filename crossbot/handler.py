import traceback

import crossbot.commands
from crossbot.parser import Parser


class Request:
    userid = 'command-line-user'

    def __init__(self, text):
        self.text = text

    def react(self, emoji):
        print('react :{}:'.format(emoji))

    def reply(self, msg, direct=False):
        prefix = '@user - ' if direct else ''
        print(prefix + msg)

    def upload(self, name, path):
        print(path)


class Handler:

    def __init__(self, limit_commands=False):
        self.parser = Parser(limit_commands)
        self.init_plugins()

    def init_plugins(self):
        for mod_name in crossbot.commands.__all__:
            try:
                mod = getattr(crossbot.commands, mod_name)

                # hopefully the plugins will add themselves to subparsers
                if hasattr(mod, 'init'):
                    mod.init(self)
                else:
                    print('WARNING: plugin "{}" has no init()'.format(mod.__name__))
            except:
                print('ERROR: Something went wrong when importing "{}"'.format(mod_name))
                traceback.print_exc()

    def handle_request(self, request, parse=True):
        """ Parses the request and calls the right command.

        If parsing fails, this raises crossbot.parser.ParserException.
        """

        if parse:
            command, args = self.parser.parse(request.text)
            request.args = args
        else:
            command = request.command

        return command(request)
