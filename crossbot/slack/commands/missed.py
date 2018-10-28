from django.utils.timezone import timedelta

from . import parse_date
from crossbot.slack import SlashCommandResponse

MINI_URL = "https://www.nytimes.com/crosswords/game/mini/{:04}/{:02}/{:02}"


def init(parser):

    parser = parser.subparsers.add_parser(
        'missed',
        help='Get mini crossword link for the most recent day you missed.')
    parser.set_defaults(command=get_missed)

    parser.add_argument(
        'n',
        nargs='?',
        default='1',
        type=int,
        help='Show the nth most recent ones you missed')


def get_missed(request):

    completed = set(
        request.user.times(request.args.table).values_list('date', flat=True))

    # find missed day
    date = parse_date('now')
    n = request.args.n
    missed = []
    for i in range(n):
        while date in completed:
            date -= timedelta(days=1)
        missed.append(date)
        date -= timedelta(days=1)

    urls = [
        MINI_URL.format(date.year, date.month, date.day) for date in missed
    ]

    return SlashCommandResponse(text='\n'.join(urls))
