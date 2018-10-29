import math
import logging

from random import choice

from . import models, parse_date, parse_time, SlashCommandResponse

logger = logging.getLogger(__name__)


def init(parser):
    parser = parser.subparsers.add_parser('add', help='Add a time.')
    parser.set_defaults(command=add)

    parser.add_argument(
        'time',
        type=parse_time,
        help='Score to add. eg. ":32", "2:45", "fail"'
    )

    parser.add_argument(
        'date',
        nargs='?',
        default='now',
        type=parse_date,
        help='Date to add a score for.'
    )


# TODO: most of this logic should be moved into the model
def add(request):
    '''Add entry for today (`add 1:07`) or given date (`add :32 2017-05-05`).
       A zero second time will be interpreted as a failed attempt.'''
    response = SlashCommandResponse()

    args = request.args
    was_added, time = request.user.add_time(args.table, args.time, args.date)

    if not was_added:
        response.add_text(
            "I could not add this to the database, because you "
            "already have an entry ({}) for this date.".format(
                time.time_str()
            )
        )
        return response

    day_of_week = request.args.date.weekday()
    emj = emoji(args.time, args.table, day_of_week)

    # Send a basic ephemeral confirmation and a rich-text non-ephemeral message
    response.add_text(
        "Submitted {} for {}".format(time.time_str(), request.args.date)
    )
    response.add_text(
        "*{} Added:* {}  {}  :{}:".format(
            time.SHORT_NAME, time.date, time.time_str(), emj
        ),
        ephemeral=False
    )
    # Impersonate the user for the non-ephemeral message
    response.set_user(request.user, ephemeral=False)

    def get_streak_counts(streaks):
        for streak in streaks:
            for i, entry in enumerate(streak):
                if entry.date == args.date:
                    # i is the old streak count, len is the new one
                    return i, len(streak)
        raise ValueError("date wasn't in streaks!")

    streaks = args.table.participation_streaks(request.user)
    old_sc, new_sc = get_streak_counts(streaks)

    for streak_count in range(old_sc + 1, new_sc + 1):
        streak_messages = STREAKS.get(streak_count)
        if streak_messages:
            msg = choice(streak_messages).format(name=request.user)
            response.attach(
                ephemeral=False, color="#39C53D", text=msg + "  :achievement:"
            )

    logger.debug(
        "%s has a streak of %s in %s", request.user, new_sc, args.table
    )

    return response

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
    (15, 3 * 60 + 30),  # Monday
    (15, 3 * 60 + 30),  # Tuesday
    (15, 3 * 60 + 30),  # Wednesday
    (15, 3 * 60 + 30),  # Thursday
    (15, 3 * 60 + 30),  # Friday
    (30, 5 * 60 + 30),  # Saturday
    (15, 3 * 60 + 30),  # Sunday
]

REGULAR_TIMES = [
    (5 * 60, 15 * 60),  # Monday
    (10 * 60, 30 * 60),  # Tuesday
    (15 * 60, 45 * 60),  # Wednesday
    (30 * 60, 60 * 60),  # Thursday
    (30 * 60, 60 * 60),  # Friday
    (45 * 60, 120 * 60),  # Saturday
    (45 * 60, 120 * 60),  # Sunday
]

SUDOKU_TIMES = [
    (60, 10 * 60),  # Monday
    (60, 10 * 60),  # Tuesday
    (60, 10 * 60),  # Wednesday
    (60, 10 * 60),  # Thursday
    (60, 10 * 60),  # Friday
    (60, 10 * 60),  # Saturday
    (60, 10 * 60),  # Sunday
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
