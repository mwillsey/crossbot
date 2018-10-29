from django.utils import timezone

from . import parse_date, SlashCommandResponse


def init(parser):
    parser = parser.subparsers.add_parser(
        'announce', help='Announce any streaks.'
    )
    parser.set_defaults(command=announce)

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to announce for.'
    )


def announce(request):
    '''Report who won the previous day and if they're on a streak.
    Optionally takes a date.'''
    message = request.args.table.announcement_message(request.args.date)
    return SlashCommandResponse(message,
                                ephemeral=False, ephemeral_command=False)
