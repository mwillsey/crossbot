from django.utils import timezone

import crossbot
from crossbot.commands.add import emoji


def init(client):

    parser = client.parser.subparsers.add_parser('times', help='show times')
    parser.set_defaults(command= times)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = crossbot.date,
        help    = 'Date to get times for.')


def times(request):
    '''Get all the times for today or given date (`times 2017-05-05`).'''

    response = ''
    failures = ''

    args = request.args

    day_of_week = timezone.now().weekday()

    times = args.table.objects.filter(date=args.date).order_by('seconds')

    for item in times:
        name = str(item.user)
        if item.seconds < 0:
            failures += ':facepalm: - {}\n'.format(name)
        else:
            emj = emoji(item.seconds, args.table, day_of_week)
            minutes, seconds = divmod(item.seconds, 60)
            response += ':{}: - {}:{:02d} - {}\n'.format(
                emj, minutes, seconds, name)

    # append now so failures at the end
    response += failures

    date_str = args.date.strftime('%a, %b %d, %Y')

    if len(response) == 0:
        if args.date == crossbot.parser.date('now'):
            response = 'No times yet today. Be the first!'
        else:
            response = 'No times for ' + date_str
    else:
        response = '*Times for {}*\n'.format(date_str) + response

    request.reply(response)
