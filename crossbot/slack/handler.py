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
        simply return an HTTP 200 response.
    """
    try:
        request = SlashCommandRequest(django_request)
        command, args = PARSER.parse(django_request.POST['text'])
        request.args = args
        response = command(request)  # returns a SlackCommandResponse

        dmsg, emsg = response.direct_message, response.ephemeral_message

        default_ret_val = None
        if not response.ephemeral_command:
            default_ret_val = Message(ephemeral=False).asdict()

        def send_message(msg, should_return=False):
            # If the message impersonates a user or has reactions, post it
            if msg.has_user() or msg.reactions:
                # You can't impersonate or react w/ ephemeral
                assert not msg.ephemeral

                # For now, simply let permissions errors bubble up. Each command
                # should properly check the request channel so that the bot has
                # correct permissions
                timestamp = post_message(
                    request.channel, msg.asdict(include_response_type=False)
                )
                for reaction in msg.reactions:
                    react(reaction, request.channel, timestamp)
            else:
                if should_return:
                    return msg.asdict()
                post_response(request.response_url, msg.asdict())
            return default_ret_val

        if emsg and dmsg:
            send_message(emsg)
            return send_message(
                dmsg, should_return=not response.ephemeral_command
            )

        if emsg:
            return send_message(emsg, should_return=response.ephemeral_command)

        if dmsg:
            return send_message(
                dmsg, should_return=not response.ephemeral_command
            )

        return default_ret_val

    except ParserException as exn:
        message = Message(ephemeral=True)
        message.text = str(exn)
        return message.asdict()
