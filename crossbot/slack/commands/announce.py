from django.utils import timezone

from . import parse_date


def init(client):
    parser = client.parser.subparsers.add_parser(
        'announce', help='Announce any streaks.')
    parser.set_defaults(command=announce)

    parser.add_argument(
        'date',
        nargs   = '?',
        default = 'now',
        type    = parse_date,
        help    = 'Date to announce for.')


def best(table, date, offset=0):
    offset = timezone.timedelta(days=offset)

    # TODO: move all of this function into models
    # Filter out fails
    times_for_date = [t for t in table.times_for_date(date=date - offset)
                      if not t.is_fail()]

    if not times_for_date:
        return []

    best_time = min(t.seconds for t in times_for_date)

    return set(t.user for t in times_for_date if t.seconds == best_time)


def announce(request):
    '''Report who won the previous day and if they're on a streak.
    Optionally takes a date.'''

    message = ""

    date = request.args.date
    table = request.args.table

    best1 = best(table, date, 1)
    best2 = best(table, date, 2)
    streaks = best1 & best2

    def fmt(best_set):
        return ' and '.join(str(user) for user in best_set)

    if not best1:
        message += 'No one played the minicrossword yesterday. Why not?\n'
    else:
        message += 'Yesterday, {} solved the minicrossword fastest.\n'\
                .format(fmt(best1))
        if best2:
            message += '{} won the day before.\n'\
                    .format(fmt(best2))

    for user in streaks:
        n = 2
        while user in best(table, date, n+1):
            n += 1
        message += (
            '{} is on a {}-day streak! {}\nCan they keep it up?\n'.format(
                user, n, ':fire:' * n))

    games = {
        "mini crossword" : "https://www.nytimes.com/crosswords/game/mini",
        "easy sudoku"    : "https://www.nytimes.com/crosswords/game/sudoku/easy"
    }

    message += "Play today's:"
    for game in games:
        message += "\n{} : {}".format(game, games[game])

    request.reply(message)
