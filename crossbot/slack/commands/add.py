import math
import logging

from random import choice

from django.utils import timezone

from . import models, parse_date, parse_time

logger = logging.getLogger(__name__)


def init(client):
    parser = client.parser.subparsers.add_parser('add', help='Add a time.')
    parser.set_defaults(command=add)

    parser.add_argument(
        'time',
        type=parse_time,
        help='Score to add. eg. ":32", "2:45", "fail"')

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to add a score for.')

    # TODO add a command-line only --user parameter


def add(request):
    '''Add entry for today (`add 1:07`) or given date (`add :32 2017-05-05`).
       A zero second time will be interpreted as a failed attempt.'''

    args = request.args

    was_added, time = request.user.add_time(args.table, args.time, args.date)

    if not was_added:
        request.reply(
            'I could not add this to the database, '
            'because you already have an entry '
            '({}) for this date.'.format(time.time_str()),
            direct=True)
        return

    # XXX: Isn't this wrong for historical adds?
    day_of_week = timezone.now().weekday()
    emj = emoji(args.time, args.table, day_of_week)

    request.message_and_react(request.text, emj, as_user=request.user)
    request.reply('Submitted {} for {}'.format(time.time_str(),
                                               request.args.date))

    new_sc, old_sc, _, _ = request.user.streaks(args.table, args.date)

    for streak_count in range(old_sc + 1, new_sc + 1):
        streak_messages = STREAKS.get(streak_count)
        if streak_messages:
            msg = choice(streak_messages).format(name=request.user)
            try:
                # try here because we might fail if the reaction already exists.
                emj = "achievement"
                request.message_and_react(msg, emj)
            except:
                logger.warning("Achievement reaction failed!")
            request.reply(msg)

    logger.debug("{} has a streak of {} in {}".format(request.user, new_sc,
                                                      args.table))

    # if args.table == 'mini_crossword_time':
    #     requests.post('http://plseaudio.cs.washington.edu:8087/scroll_text',
    #                   data='{}\n{} sec\n:{}:'.format(name, args.time, emj))


# STREAKS[streak_num] = list of messages with {name} format option
STREAKS = {
    #    1:   ["First one in a while, {name}.",
    #          "Try it every day, {name}." ],
    3: ["3 entries in a row! Keep it up {name}!", "Nice work, 3 in a row!"],
    10: ["{name}'s on a streak of 10 entries, way to go!"],
    25: [":open_mouth:, 25 days in a row!"],
    50: ["50 in a row, here's a medal :sports_medal:!"],
    100:
    [":100::100::100: {name}'s done 100 crosswords in a row! :100::100::100:"],
    150: ["{name}'s on a streak of 150 days... impressive!"],
    200: [":two::zero::zero: days in a row!?! Wow! Great work {name}!"],
    300: ["Congrats {name} for doing 300 crosswords in a row!"],
    365: [
        "Whoa, {name} just finished a full *year of crosswords*! Congratulations! :calendar::partypopper:"
    ],
    500: ["{name} just completed their 500th in a row! :partypopper:"],
}

# (fast_time, slow_time) for each day
MINI_TIMES = [
    (15, 3 * 60 + 30),  # Sunday
    (15, 3 * 60 + 30),  # Monday
    (15, 3 * 60 + 30),  # Tuesday
    (15, 3 * 60 + 30),  # Wednesday
    (15, 3 * 60 + 30),  # Thursday
    (15, 3 * 60 + 30),  # Friday
    (30, 5 * 60 + 30),  # Saturday
]

REGULAR_TIMES = [
    (45 * 60, 120 * 60),  # Sunday
    (5 * 60, 15 * 60),  # Monday
    (10 * 60, 30 * 60),  # Tuesday
    (15 * 60, 45 * 60),  # Wednesday
    (30 * 60, 60 * 60),  # Thursday
    (30 * 60, 60 * 60),  # Friday
    (45 * 60, 120 * 60),  # Saturday
]

SUDOKU_TIMES = [
    (60, 10 * 60),  # Sunday
    (60, 10 * 60),  # Monday
    (60, 10 * 60),  # Tuesday
    (60, 10 * 60),  # Wednesday
    (60, 10 * 60),  # Thursday
    (60, 10 * 60),  # Friday
    (60, 10 * 60),  # Saturday
]

# possible reactions sorted by speed
# if these aren't in Slack, crossbot will crash
SPEED_EMOJI = [
    'fire',
    'hot_pepper',
    'rockon',
    'rocket',
    'nicer',
    'fastparrot',
    'fistv',
    'thumbsup',
    'ok',
    'slowparrot',
    'slow',
    'slowpoke',
    'waiting',
    'turtle',
    'snail',
    'zzz',
    'rip',
    'poop',
]


def emoji(time, table, day_of_week):

    if table == models.MiniCrosswordTime:
        times_list = MINI_TIMES
    elif table == models.CrosswordTime:
        times_list = REGULAR_TIMES
    elif table == models.EasySudokuTime:
        times_list = SUDOKU_TIMES
    else:
        raise RuntimeError('Unknown table {}'.format(table))

    fast_time, slow_time = times_list[day_of_week]
    assert fast_time < slow_time

    if time < 0:
        return 'facepalm'
    if time < fast_time:
        return SPEED_EMOJI[0]
    if time > slow_time:
        return SPEED_EMOJI[-1]

    last_emoji = len(SPEED_EMOJI) - 2

    speed = time - fast_time
    time_range = slow_time - fast_time
    ratio = (speed / time_range)**0.8
    index = int(math.ceil(ratio * last_emoji))

    index = min(index, last_emoji)

    assert index in range(len(SPEED_EMOJI))

    return SPEED_EMOJI[index]
