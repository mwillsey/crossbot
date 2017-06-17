#!/usr/bin/env python

import argparse
import os
import re
import importlib
import traceback

import pytz

bot_name = 'crossbot'
db_path  = 'crossbot.db'

nyt_timezone = pytz.timezone('US/Eastern')

class ParsePrintException(Exception):
    pass

# subclass ArgumentParser so it doesn't just exit the program on error
# also we want the help messages to go to slack if we are using slack
class ArgumentParser(argparse.ArgumentParser):

    def print_help(self):  raise ParsePrintException(self.format_help())
    def print_usage(self): raise ParsePrintException(self.format_usage())

    def error(self, message):
        raise ParsePrintException('Parse Error:\n' + message)

    def exit(self, status=0, message=None):
        if status != 0:
            raise ParsePrintException('Parse Error:\n' + message)


class Client():
    pass

class SlackClient(Client):
    def __init__(self, message):
        self.message = message
        self.userid  = message._get_user_id()

    def react(self, emoji): self.message.react(emoji)
    def send (self, msg):   self.message.send(msg)
    def reply(self, msg):   self.message.reply(msg)

    def user(self, userid):
        users = self.message._client.users

        if userid in users:
            return users[userid]['name']
        else:
            print('WARNING: userid "{}" not found'.format(userid))
            return str(userid)

    def upload(self, name, path):
        self.message.channel.upload_file(name, path)

class CommandLineClient(Client):
    userid = 'command-line-user'

    def react(self, emoji): print('react :{}:'.format(emoji))
    def send (self, msg):   print(msg)
    def reply(self, msg):   print('@user - ' + msg)

    def user(self, userid):
        return userid
    def upload(self, name, path):
        print('Uploaded {} as "{}"'.format(path, name))


def load_plugins(plugin_dir):

    plugin_path = os.path.join(os.path.dirname(__file__), plugin_dir)

    modules = (
        plugin_dir + '.' + os.path.basename(path)
        for path, ext in map(os.path.splitext, os.listdir(plugin_path))
        if ext == '.py' and '__' not in path
    )

    imported = []
    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
            imported.append(mod)
        except:
            print('ERROR: Something went wrong when importing "{}"'.format(mod_name))
            traceback.print_exc()

    return imported

def mk_parser():

    parser = ArgumentParser(
        prog='crossbot',
        description = '''
        You can either @ me in a channel or just DM me to give me a command.
        Play here: https://www.nytimes.com/crosswords/game/mini
        I live here: https://github.com/mwillsey/crossbot
        Times look like this `1:30` or this `:32` (the `:` is necessary).
        Dates look like this `2017-05-05` or simply `now` for today.
        `now` or omitted dates will automatically become tomorrow if the
        crossword has already been released (10pm weekdays, 6pm weekends).
        Here are my commands:\n\n
        '''
    )
    subparsers = parser.add_subparsers(help = 'subparsers help')

    def show_help(client, args):
        if args.help_command:
            for cmd in args.help_command:
                try:
                    parser.parse_args([cmd, '--help'])
                except ParsePrintException as e:
                    client.send(str(e))
        else:
            client.send(parser.format_help())

    help_parser = subparsers.add_parser('help')
    help_parser.set_defaults(command = show_help)
    help_parser.add_argument('help_command', nargs='*')

    return parser, subparsers


if __name__ == '__main__':

    client = CommandLineClient()

    parser, subparsers = mk_parser()

    # hopefully the plugins will add themselves to subparsers
    for mod in load_plugins('commands'):
        if hasattr(mod, 'init'):
            mod.init(subparsers)
        else:
            print('WARNING: plugin "{}" has no init()'.format(mod.__name__))

    try:
        args = parser.parse_args()

        if not hasattr(args, 'command'):
            show_help(args)
        else:
            args.command(client, args)

    except ParsePrintException as e:
        print(str(e))
