from django_cron import CronJobBase, Schedule
from django.utils import timezone

from datetime import timedelta

from crossbot.models import MiniCrosswordTime
from crossbot.slack.api import post_message

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
                u=u, n=len(streak), emoji=':fire:' * len(streak))
            for u, streak in announce_data['streaks']
        ]

        # now add the other winners
        also = ' also' if announce_data['streaks'] else ''
        if announce_data['winners_today']:
            msgs.append(', '.join(announce_data['winners_today']) + also +
                        ' won.')
        if announce_data['winners_yesterday']:
            msgs.append(', '.join(announce_data['winners_yesterday']) + also +
                        ' won yesterday.')
        msgs.append("Play tomorrow's:")
        for game in announce_data['links']:
            msgs.append("{} : {}".format(game, announce_data['links'][game]))

        return '\n'.join(msgs)

    def do(self):
        now = timezone.now()
        if self.should_run_now(now):
            announce_data = MiniCrosswordTime.announcement_data(now)
            message = self.format_message(announce_data)
            # TODO dont hardcode
            channel = 'C58PXJTNU'
            response = post_message(channel, text=message)
            return "Ran release announcement at {}\n{}".format(now, message)
        return "Did not run release announcement at {} (hour={})".format(
            now, now.hour)


class MorningAnnouncement(CronJobBase):
    schedule = Schedule(run_at_times=['08:30'])
    code = 'crossbot.morning_announcement'

    def format_message(self, announce_data):
        msgs = ['Good morning crossworders!']

        msgs += [
            '{u} is currently on a {n}-day streak! {emoji}'.format(
                u=u, n=len(streak), emoji=':fire:' * len(streak))
            for u, streak in announce_data['streaks']
        ]

        # now add the other winners
        also = ' also' if announce_data['streaks'] else ''
        if announce_data['winners_today']:
            msgs.append(', '.join(announce_data['winners_today']) + also +
                        ' is winning.')
        if announce_data['winners_yesterday']:
            msgs.append(', '.join(announce_data['winners_yesterday']) + also +
                        ' won yesterday.')
        msgs.append("Think you can beat them? Play today's:")
        for game in announce_data['links']:
            msgs.append("{} : {}".format(game, announce_data['links'][game]))

        return '\n'.join(msgs)

    def do(self):
        now = timezone.now()
        announce_data = MiniCrosswordTime.announcement_data(now)
        message = self.format_message(announce_data)
        # TODO dont hardcode
        channel = 'C58PXJTNU'
        response = post_message(channel, text=message)
        return "Ran morning announcement at {}\n{}".format(now, message)
