import datetime
import random

from . import parse_date, date_fmt


def init(client):

    parser = client.parser.subparsers.add_parser(
        'random', help='Get a random mini crossword link.'
    )
    parser.set_defaults(command=random_date_url)

    parser.add_argument(
        '--start-date',
        default=first_dt,
        type=parse_date,
        help='Beginning of random range. Default {}'.format(first_date)
    )

    parser.add_argument(
        '--end-date',
        default='now',
        type=parse_date,
        help='End of random range. Default today.'
    )


mini_url = "https://www.nytimes.com/crosswords/game/mini/{:04}/{:02}/{:02}"

first_date = '2014-08-21'
first_dt = datetime.datetime.strptime('2014-08-21', date_fmt).date()


def random_date_url(request):

    start = request.args.start_date
    end = request.args.end_date

    if type(start) is str:
        start = datetime.datetime.strptime(start, date_fmt)
    if type(end) is str:
        end = datetime.datetime.strptime(end, date_fmt)

    if start > end:
        request.reply('Your dates are mixed up')
        return

    if start < first_dt:
        request.reply(
            'That start date is too early, must be {} or later'
            .format(first_date)
        )
        return

    rand = start + random.random() * (end - start)

    request.reply(mini_url.format(rand.year, rand.month, rand.day))
