from .handler import Handler, SlashCommandRequest

_HANDLER = Handler()


def handle_slash_command(request):
    """Convenience methods used to handle slash commands.

    Args:
        slash_command: str

    Returns:
        A Response object or None. (??)
    """
    slash_command_request = SlashCommandRequest(request)
    _HANDLER.handle_request(slash_command_request)
    return slash_command_request.response_json()
