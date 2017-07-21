
import os
import traceback

import crossbot.commands

from crossbot.parser import Parser, ParserException

class Request:
    pass

class CommandLineRequest(Request):
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

class SlackRequest(Request):

    def __init__(self, message):
        self.message = message
        self.text    = message.body['text']
        self.userid  = message._get_user_id()

    def react(self, emoji):
        # TODO handle not present emoji
        self.message.react(emoji)

    def reply(self, msg, direct=False):

        if direct:
            self.message.reply(msg)
        else:
            self.message.send(msg)

    def upload(self, name, path):
        self.message.channel.upload_file(name, path)


class Client():
    '''Client objects are passed around crossbot to allow it to behave
    similarly on the command line and on Slack'''

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

    def handle_request(self, request):
        '''Tries to parse string, running the command if successful. Otherwise, it
        sends the error back to the client'''

        try:
            command, args = self.parser.parse(request.text)
            request.args = args
            command(self, request)

        except ParserException as e:
            request.reply(str(e))

class CommandLineClient(Client):
    def user(self, userid):
        '''A dumb user lookup that should be overridden if you have access to
        Slack.'''
        return userid

class SlackClient(Client):

    def __init__(self, bot, **kwargs):
        self.bot = bot
        super().__init__(kwargs)

    def user(self, userid):
        users = self.bot._client.users

        if userid in users:
            return users[userid]['name']
        else:
            print('WARNING: userid "{}" not found'.format(userid))
            return str(userid)
