from django.utils import timezone

from . import parse_date
from .add import emoji


def init(client):

    parser = client.parser.subparsers.add_parser('times', help='show times')
    parser.set_defaults(command=times)

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to get times for.'
    )


def times(request):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    response = ''
    failures = ''

    args = request.args

    day_of_week = timezone.now().weekday()

    for item in args.table.times_for_date(args.date).order_by('seconds'):
        name = str(item.user)
        if item.seconds < 0:
            failures += ':facepalm: - {}\n'.format(name)
        else:
            emj = emoji(item.seconds, args.table, day_of_week)
            minutes, seconds = divmod(item.seconds, 60)
            response += ':{}: - {}:{:02d} - {}\n'.format(
                emj, minutes, seconds, name
            )

    # append now so failures at the end
    response += failures

    date_str = args.date.strftime('%a, %b %d, %Y')

    if len(response) == 0:
        if args.date == parse_date('now'):
            response = 'No times yet today. Be the first!'
        else:
            response = 'No times for ' + date_str
    else:
        response = '*Times for {}*\n'.format(date_str) + response

    request.reply(response)
