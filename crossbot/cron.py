from django_cron import CronJobBase, Schedule
from django.utils import timezone

from crossbot.models import MiniCrosswordTime
from crossbot.slack.api import post_message

import logging

logger = logging.getLogger(__name__)


class Announce(CronJobBase):
    schedule = Schedule(run_at_times=['08:30'])
    code = 'crossbot.announce'

    def do(self):
        date = timezone.now().date()
        msg = MiniCrosswordTime.announcement_message(date)
        # TODO dont hardcode
        channel = 'C58PXJTNU'
        logger.info("Running announce")
        response = post_message(channel, text=msg)
        logger.info(response)
