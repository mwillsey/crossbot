"""Crossbot Django models."""

import datetime
import logging

from copy import copy

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


# TODO: switch from return codes to exceptions to help with transactions???
#       or, we can use set_rollback
#       https://stackoverflow.com/questions/39332010/django-how-to-rollback-transaction-atomic-without-raising-exception
class CBUser(models.Model):
    """Main user model used by the rest of the app."""
    class Meta:
        verbose_name = "CBUser"
        verbose_name_plural = "CBUsers"

    slackid = models.CharField(max_length=10, primary_key=True)
    slackname = models.CharField(max_length=100, blank=True)

    auth_user = models.OneToOneField(User, null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='cb_user')

    @classmethod
    def from_slackid(cls, slackid, slackname=None, create=True):
        """Gets or creates the user with slackid, updating slackname.

        Returns:
            The CBUser if it exists or create=True, None otherwise.
        """
        if create and slackname:
            return cls.objects.update_or_create(
                slackid=slackid, defaults={'slackname': slackname})[0]
        if create:
            return cls.objects.get_or_create(slackid=slackid)[0]
        try:
            user = cls.objects.get(slackid=slackid)
            if slackname:
                user.slackname = slackname
                user.save()
            return user
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_slacknames(cls):
        from crossbot.slack.api import slack_users

        users = {
            u['id']: u for u in slack_users()
        }

        for user in cls.objects.all():
            user.slackname = users[user.slackid]['name']
            user.save()

    def get_time(self, time_model, date):
        """Get the time for this user for the given date.

        Args:
            time_model: Reference to the subclass of CommonTime to get.
            date: The date of the puzzle.

        Returns:
            An instance of time_model if it exists, None otherwise.
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(date, datetime.date)

        try:
            return time_model.objects.get(user=self, date=date,
                                          seconds__isnull=False)
        except time_model.DoesNotExist:
            return None

    # TODO: wrap this and other operations in transactions???
    def add_time(self, time_model, seconds, date):
        """Add a time for this user for the given date.

        Args:
            time_model: Reference to the subclass of CommonTime to add.
            seconds: An integer representing the seconds taken, -1 if user
                failed to solve.
            date: The date of the puzzle.

        Returns:
            A 2-tuple, (was_added, time), where was_added denotes whether or not
            the time was successfully added, time is the instace of time_model
            for this user and date (the already existent one if was_added is
            False).
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(seconds, int)
        assert isinstance(date, datetime.date)

        time = self.get_time(time_model, date)
        if time:
            return (False, time)

        time = time_model.objects.create(user=self,
                                         date=date,
                                         seconds=seconds)
        return (True, time)

    def remove_time(self, time_model, date):
        """Remove a time record for this user.

        Args:
            time_model: Reference to the subclass of CommonTime to remove.
            date: The date of the puzzle.

        Returns:
            A str representing the deleted time or None.
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(date, datetime.date)

        time = self.get_time(time_model, date)
        if time:
            time_str = str(time)
            time.delete()
            return time_str

        return None

    def times(self, time_model):
        """Returns a QuerySet with times this user has completed."""
        assert issubclass(time_model, CommonTime)

        return time_model.objects.filter(user=self)

    def streaks(self, time_model, date):
        """Returns the full, forwards, and backwards streaks the user is on.

        Calculates the number of days in a row the user has completed a given
        puzzle, centered on a given date.

        Returns:
            (streak_length, old_streak_length, forwards_streak_length,
             backward_streak_length)
        """

        dates_completed = set(
            self.times(time_model).values_list('date', flat=True))

        # calculate the backwards streak
        check_date = copy(date) # why is this copied? Does -= change value?
        backward_streak_count = 0
        while check_date in dates_completed:
            backward_streak_count += 1
            check_date -= datetime.timedelta(days=1)

        # calculate the forwards streak
        check_date = copy(date)
        forward_streak_count = 0
        while check_date in dates_completed:
            forward_streak_count += 1
            check_date += datetime.timedelta(days=1)

        streak_count = forward_streak_count + backward_streak_count
        # Don't double-count date
        if streak_count > 0:
            streak_count -= 1

        old_streak_count = max(backward_streak_count, forward_streak_count)
        # Don't count date in the old_streak_count
        if old_streak_count > 0:
            old_streak_count -= 1

        return (streak_count, old_streak_count,
                forward_streak_count, backward_streak_count)

    def get_mini_crossword_time(self, *args, **kwargs):
        return self.get_time(MiniCrosswordTime, *args, **kwargs)

    def get_crossword_time(self, *args, **kwargs):
        return self.get_time(CrosswordTime, *args, **kwargs)

    def get_easy_sudoku_time(self, *args, **kwargs):
        return self.get_time(EasySudokuTime, *args, **kwargs)

    def add_mini_crossword_time(self, *args, **kwargs):
        return self.add_time(MiniCrosswordTime, *args, **kwargs)

    def add_crossword_time(self, *args, **kwargs):
        return self.add_time(CrosswordTime, *args, **kwargs)

    def add_easy_sudoku_time(self, *args, **kwargs):
        return self.add_time(EasySudokuTime, *args, **kwargs)

    def remove_mini_crossword_time(self, *args, **kwargs):
        return self.remove_time(MiniCrosswordTime, *args, **kwargs)

    def remove_crossword_time(self, *args, **kwargs):
        return self.remove_time(CrosswordTime, *args, **kwargs)

    def remove_easy_sudoku_time(self, *args, **kwargs):
        return self.remove_time(EasySudokuTime, *args, **kwargs)

    def __str__(self):
        return str(self.slackname if self.slackname else self.slackid)


class CommonTime(models.Model):
    class Meta:
        unique_together = ("user", "date")
        abstract = True

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    @classmethod
    def all_times(cls):
        return cls.objects.all()

    @classmethod
    def times_for_date(cls, date):
        """Return a query set with all times for a date."""
        return cls.objects.filter(date=date)

    def is_fail(self):
        return self.seconds < 0

    def time_str(self):
        if self.is_fail():
            return 'fail'

        minutes, seconds = divmod(self.seconds, 60)

        return '{}:{:02}'.format(minutes, seconds)

    def __str__(self):
        return '{} - {} - {}'.format(self.user, self.time_str(), self.date)


class MiniCrosswordTime(CommonTime):
    pass

class CrosswordTime(CommonTime):
    pass

class EasySudokuTime(CommonTime):
    pass


class MiniCrosswordModel(models.Model):
    class Meta:
        managed = False
        db_table = 'mini_crossword_model'
        unique_together = (('userid', 'date'),)

    userid = models.TextField()
    date = models.IntegerField()
    prediction = models.IntegerField()
    residual = models.FloatField()

class ModelUser(models.Model):
    class Meta:
        managed = False
        db_table = 'model_users'

    uid = models.TextField(unique=True)
    nth = models.IntegerField()
    skill = models.FloatField()
    skill_25 = models.FloatField()
    skill_75 = models.FloatField()

class ModelDate(models.Model):
    class Meta:
        managed = False
        db_table = 'model_dates'

    date = models.IntegerField()
    difficulty = models.FloatField()
    difficulty_25 = models.FloatField()
    difficulty_75 = models.FloatField()

class ModelParams(models.Model):
    class Meta:
        managed = False
        db_table = 'model_params'
        verbose_name_plural = "ModelParams"

    time = models.FloatField()
    time_25 = models.FloatField()
    time_75 = models.FloatField()
    satmult = models.FloatField()
    satmult_25 = models.FloatField()
    satmult_75 = models.FloatField()
    bgain = models.FloatField()
    bgain_25 = models.FloatField()
    bgain_75 = models.FloatField()
    bdecay = models.FloatField()
    bdecay_25 = models.FloatField()
    bdecay_75 = models.FloatField()
    skill_dev = models.FloatField()
    date_dev = models.FloatField()
    sigma = models.FloatField()
    lp = models.FloatField()
    when_run = models.FloatField()


class QueryShorthand(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(CBUser, null=True, on_delete=models.SET_NULL)
    command = models.TextField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    @classmethod
    def from_name(cls, name):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            return None

    def num_args(self):
        return self.command.count('?')

    def __str__(self):
        nargs = self.num_args()
        if nargs:
            arg_str = ' (takes {} arg{})'.format(nargs, '' if nargs == 1 else 's')
        else:
            arg_str = ''

        # return '{} - {}'.format(self.name, self.user)

        return '*{}* by {}{}:\n {}'.format(
            self.name, self.user, arg_str, self.command)
