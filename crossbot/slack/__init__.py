from .handler import Handler, SlashCommandRequest

_HANDLER = Handler()

def handle_slash_command(slash_command):
    """Convenience methods used to handle slash commands.

    Args:
        slash_command: str

    Returns:
        A Response object or None. (??)
    """
    request = SlashCommandRequest(slash_command)

    _HANDLER.handle_request(request)
    return request.response_json()
