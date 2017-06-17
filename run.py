from slackbot.bot import Bot, default_reply

import crossbot
from crossbot import ParsePrintException

# no API_TOKEN
# use environment variable SLACKBOT_API_TOKEN instead

# no @ needed
ERRORS_TO = 'mwillsey'

@default_reply
def my_default_hanlder(message):

    client = crossbot.SlackClient(message)

    try:
        args = parser.parse_args(message.body['text'].split())

        if not hasattr(args, 'command'):
            show_help(args)
        else:
            args.command(client, args)

    except ParsePrintException as e:
        message.send(str(e))

if __name__ == "__main__":
    parser, subparsers = crossbot.mk_parser()

    # hopefully the plugins will add themselves to subparsers
    for mod in crossbot.load_plugins('commands'):
        if hasattr(mod, 'init'):
            mod.init(subparsers)
        else:
            print('WARNING: plugin "{}" has no init()'.format(mod.__name__))

    bot = Bot()

    print('crossbot is up and running!')

    bot.run()
