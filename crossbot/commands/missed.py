import crossbot

from crossbot.parser import date_fmt

import datetime

def init(client):

    parser = client.parser.subparsers.add_parser(
            'missed',
            help='Get a mini crossword link for a day you missed.')
    parser.set_defaults(command=get_missed)

    parser.add_argument(
        '--start-date',
        default = first_dt,
        type    = crossbot.date,
        help    = 'Beginning of missed range. Default {}'.format(first_date))

    parser.add_argument(
        '--end-date',
        default = 'now',
        type    = crossbot.date,
        help    = 'End of missed range. Default today.')

mini_url = "https://www.nytimes.com/crosswords/game/mini/{:04}/{:02}/{:02}"

first_date = '2014-08-21'
first_dt = datetime.datetime.strptime('2014-08-21', date_fmt)

def get_missed(client, request):

    args = request.args
    start = args.start_date
    end = args.end_date

    if type(start) is str:
        start = datetime.datetime.strptime(start, date_fmt)
    if type(end) is str:
        end = datetime.datetime.strptime(end, date_fmt)

    if start > end:
        request.reply('Your dates are mixed up.')
        return

    if start < first_dt:
        request.reply('That start date is too early, must be {} or later.'
                      .format(first_date))
        return

    # get all the entries for this person
    with sqlite3.connect(crossbot.db_path) as con:
        query = '''
        SELECT date
        FROM {}
        WHERE userid = ?
        '''.format(args.table)

        result = con.execute(query, (request.userid,))

    # sort dates completed from earliest to most recent
    dates_completed = sorted(tup[0] for tup in result)

    # find a gap in the dates
    gap_date = None
    for i in range(1, len(dates_completed)):
        prev = datetime.strptime(dates_completed[i - 1], date_fmt)
        next_done = datetime.strptime(dates_completed[i], date_fmt)
        next_cal = prev + timedelta(days=1)
        if next_done != next_cal:
            gap_date = next_cal
            break

    if gap_date == None:
        request.reply("You are all caught up for this date range.").
    else:
        url = mini_url.format(gap_date.year, gap_date.month, gap_date.day)
        request.reply(url)

