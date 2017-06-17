import datetime
import argparse
import re

import crossbot

time_rx = re.compile(r'(\d*):(\d\d)')

def get_time(time_str):

    if time_str == 'fail':
        return 0

    match = time_rx.match(time_str)
    if not match:
        raise argparse.ArgumentTypeError(
            'Cannot parse time "{}", should look like ":32" or "fail"'
            .format(time_str))

    minutes, seconds = ( int(x) if x else 0
                         for x in match.groups() )

    return minutes * 60 + seconds


def get_date(date_str):
    '''If date is a date, this does nothing. If it's 'now' or None, then this
    gets either today's date or tomorrow's if the crossword has already come
    out (10pm on weekdays, 6pm on weekends)'''

    date_fmt = '%Y-%m-%d'

    if date_str is None or date_str == 'now':

        date = datetime.datetime.now(crossbot.nyt_timezone)

        release_hour = 22 if date.weekday() < 5 else 18
        release_dt = date.replace(hour=release_hour, minute=0, second=30, microsecond=0)

        # if it's already been released (with a small buffer), use tomorrow
        if date > release_dt:
            date += datetime.timedelta(days=1)

    else:

        try:
            date = datetime.datetime.strptime(date_str, date_fmt)
        except ValueError:
            raise argparse.ArgumentTypeError(
                'Cannot parse date "{}", should look like "YYYY-MM-DD" or "now".'
                .format(date_str))

    return date.strftime(date_fmt)
