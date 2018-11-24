from django_cron import CronJobBase, Schedule
from django.utils import timezone

from datetime import timedelta

from crossbot.util import comma_and
from crossbot.models import MiniCrosswordTime
from crossbot.slack.api import post_message
import crossbot.predictor as predictor

import logging

logger = logging.getLogger(__name__)


class ReleaseAnnouncement(CronJobBase):
    schedule = Schedule(run_at_times=['15:00', '19:00'])
    code = 'crossbot.release_announcement'

    def should_run_now(self, time):
        if time.isoweekday() in (6, 7):  # It's Saturday or Sunday
            return 14 <= time.hour <= 15
        else:
            return 18 <= time.hour <= 19

    def format_message(self, announce_data):
        msgs = ['Good evening crossworders!']
        msgs += [
            '{u} is on a {n}-day streak! {emoji}'.format(
                u=u, n=len(streak), emoji=':fire:' * len(streak)
            ) for u, streak in announce_data['streaks']
        ]

        # now add the other winners
        also = ' also' if announce_data['streaks'] else ''
        if announce_data['winners_today']:
            msgs.append(
                comma_and(announce_data['winners_today']) + also + ' won.'
            )
        if announce_data['winners_yesterday']:
            msgs.append(
                comma_and(announce_data['winners_yesterday']) + also +
                ' won yesterday.'
            )
        if announce_data['overperformers']:
            users = [
                u + (
                    " " + ":chart_with_upwards_trend:" * int(-i)
                    if i <= -1 else ""
                ) for u, i in announce_data['overperformers']
            ]
            msgs.append(comma_and(users) + ' did really well today!')
        if announce_data['difficulty'] > 1:
            diff = int(announce_data['difficulty'])
            msgs.append("Oof, that was a tough mini! " + diff * ":open_mouth:")
        msgs.append("Play tomorrow's:")
        for game in announce_data['links']:
            msgs.append("{} : {}".format(game, announce_data['links'][game]))

        return '\n'.join(msgs)

    def do(self):
        now = timezone.localtime()
        if self.should_run_now(now):
            announce_data = MiniCrosswordTime.announcement_data(now)
            message = self.format_message(announce_data)
            # TODO dont hardcode
            channel = 'C58PXJTNU'
            response = post_message(channel, {'text': message})
            return "Ran release announcement at {}\n{}".format(now, message)
        return "Did not run release announcement at {} (hour={})".format(
            now, now.hour
        )


class MorningAnnouncement(CronJobBase):
    schedule = Schedule(run_at_times=['08:30'])
    code = 'crossbot.morning_announcement'

    def format_message(self, announce_data):
        msgs = ['Good morning crossworders!']

        msgs += [
            '{u} is currently on a {n}-day streak! {emoji}'.format(
                u=u, n=len(streak), emoji=':fire:' * len(streak)
            ) for u, streak in announce_data['streaks']
        ]

        # now add the other winners
        also = ' also' if announce_data['streaks'] else ''
        if announce_data['winners_today']:
            is_are = 'are' if len(announce_data['winners_today']) > 1 else 'is'
            msgs.append(
                '{} {}{} winning'.format(
                    comma_and(announce_data['winners_today']), is_are, also
                )
            )
        if announce_data['winners_yesterday']:
            msgs.append(
                comma_and(announce_data['winners_yesterday']) + also +
                ' won yesterday.'
            )
        msgs.append("Think you can beat them? Play today's:")
        for game in announce_data['links']:
            msgs.append("{} : {}".format(game, announce_data['links'][game]))

        return '\n'.join(msgs)

    def do(self):
        now = timezone.localtime()
        announce_data = MiniCrosswordTime.announcement_data(now)
        message = self.format_message(announce_data)
        # TODO dont hardcode
        channel = 'C58PXJTNU'
        response = post_message(channel, {'text': message})
        return "Ran morning announcement at {}\n{}".format(now, message)


class Predictor(CronJobBase):
    schedule = Schedule(run_every_mins=60)
    code = 'crossbot.predictor.infer'

    def do(self):
        data = predictor.data()
        fit = predictor.fit(data, quiet=True)
        model = predictor.extract_model(data, fit)
        predictor.save(model)
        historic, dates, users, params = model
        return "Ran the predictor at {}".format(params.when_run)
