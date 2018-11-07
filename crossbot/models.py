"""Crossbot Django models."""

import datetime
import logging
import random

from operator import attrgetter
from os import path

import yaml

from crossbot.util import comma_and

from django.contrib.auth.models import User
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db import models, transaction
from django.utils import timezone

from .settings import CROSSBUCKS_PER_SOLVE, ITEM_DROP_RATE, DEFAULT_TITLE
from crossbot.slack.api import slack_users, slack_user

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
    slack_fullname = models.CharField(max_length=100, blank=True)
    image_url = models.CharField(max_length=150, blank=True)

    crossbucks = models.IntegerField(default=0)
    hat_key = models.CharField(max_length=40, null=True, blank=True)
    title_key = models.CharField(max_length=40, null=True, blank=True)

    auth_user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='cb_user'
    )

    @classmethod
    @transaction.atomic
    def from_slackid(cls, slackid, slackname=None):
        """Gets or creates the user with slackid, updating slackname.

        Returns:
            The CBUser if it exists or create=True, None otherwise.
        """
        try:
            user = cls.objects.get(slackid=slackid)
            if slackname:
                user.slackname = slackname
                user.save()
            return user
        except cls.DoesNotExist:
            try:
                slack_data = slack_user(slackid)
            except ValueError:
                if slackname:
                    # This should never happen, since we got the slackname from slack!
                    raise
                return None
            user = cls(
                slackid=slackid,
                slackname=slack_data['name'],
                slack_fullname=slack_data['profile']['real_name'],
                image_url=slack_data['profile']['image_48']
            )
            user.save()
            return user

    @classmethod
    def update_slacknames(cls):
        users = {u['id']: u for u in slack_users()}

        for user in cls.objects.all():
            u = users[user.slackid]
            user.slackname = u['name']
            user.slack_fullname = u['profile']['real_name']
            # image size options: 24 32 48 72 192 512 1024
            user.image_url = u['profile']['image_48']
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
            return time_model.objects.get(
                user=self, date=date, seconds__isnull=False, deleted=None
            )

        except time_model.DoesNotExist:
            return None

    @transaction.atomic
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

        time = time_model.objects.create(user=self, date=date, seconds=seconds)

        # Give the user crossbucks
        self.refresh_from_db()  # refresh this object inside the transaction
        self.crossbucks += CROSSBUCKS_PER_SOLVE
        self.save()

        return (True, time)

    @transaction.atomic
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
        if not time:
            return None

        time_str = str(time)

        assert time.deleted is None
        time.deleted = timezone.now()
        time.save()

        # Take away crossbucks from the user
        self.refresh_from_db()  # refresh this object inside the transaction
        self.crossbucks -= CROSSBUCKS_PER_SOLVE
        self.save()

        return time_str

    def times(self, time_model):
        """Returns a QuerySet with times this user has completed."""
        assert issubclass(time_model, CommonTime)

        return time_model.all_times().filter(user=self)

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

    def add_item(self, item, amount=1):
        """Add an item to this user's inventory.
        Args:
            item: An Item object.
            amount: An integer > 0.
        """
        assert isinstance(item, Item)
        assert amount > 0

        record, _ = ItemOwnershipRecord.objects.get_or_create(
            owner=self, item_key=item.key
        )
        if item.unique and record.quantity > 0:
            return False
        record.quantity += amount
        record.save()
        return True

    def remove_item(self, item, amount=1):
        """Remove an item from this user's inventory.
        Args:
            item: The Item to remove.
            amount: An integer > 0.
        Returns:
            Whether or not the item was removed.
        """
        assert isinstance(item, Item)
        assert amount > 0

        try:
            record = ItemOwnershipRecord.objects.get(
                owner=self, item_key=item.key
            )
        except ItemOwnershipRecord.DoesNotExist:
            return False

        # Check to see if there are enough to safely delete
        if amount + (1 if self.is_equipped(item) else 0) > record.quantity:
            return False

        record.quantity -= amount
        if record.quantity == 0:
            record.delete()
        else:
            record.save()
        return True

    def quantity_owned(self, item):
        """Return the amount of a given item this user owns."""
        assert isinstance(item, Item)
        try:
            return ItemOwnershipRecord.objects.get(
                owner=self, item_key=item.key
            ).quantity
        except ItemOwnershipRecord.DoesNotExist:
            return 0

    @property
    def hat(self):
        """Return the hat Item for a person, or None if they have no hat. :-("""
        return Item.from_key(self.hat_key)

    @property
    def title(self):
        """Return the title Item for a person, or None if they have no title."""
        return Item.from_key(self.title_key)

    @property
    def title_text(self):
        """Returns the title if the user has one, the default one otherwise."""
        title = self.title
        if title is None:
            return DEFAULT_TITLE
        return str(title)

    @transaction.atomic
    def equip(self, item):
        """Equip the item to the correct slot if the user owns at least one.
        Args:
            item: An Item.
        Returns:
            Whether or not the hat was sucessfully put on.
        """
        assert isinstance(item, Item)
        assert item.is_hat() or item.is_title()

        if self.quantity_owned(item) <= 0:
            return False

        if item.is_hat():
            self.hat_key = item.key
            self.save()
            return True

        if item.is_title():
            self.title_key = item.key
            self.save()
            return True

    def is_equipped(self, item):
        assert isinstance(item, Item)
        return item.key == self.hat_key or item.key == self.title_key

    def unequip(self, item):
        assert isinstance(item, Item)

        if item.key == self.hat_key:
            self.unequip_hat()

        elif item.key == self.title_key:
            self.unequip_title()

    def unequip_hat(self):
        self.hat_key = None
        self.save()

    def unequip_title(self):
        self.title_key = None
        self.save()

    @property
    def is_staff(self):
        if not self.auth_user:
            return False
        return self.auth_user.is_staff

    def __str__(self):
        if self.slack_fullname:
            return str(self.slack_fullname)
        if self.slackname:
            return str(self.slackname)
        return str(self.slackid)


class CommonTime(models.Model):
    class Meta:
        unique_together = ("user", "date", "deleted")
        abstract = True

    SLUG = 'common'
    SHORT = 'Common'
    PLURAL = 'commons'

    completed_milestones = [3, 10, 50, 100, 250, 500, 1000]
    completed_congrats = "Congrats on completing {n} {games}! You've earned a new title: \"{title}\""

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)
    deleted = models.DateTimeField(null=True, blank=True, default=None)

    @classmethod
    def all_times(cls):
        return cls.objects.filter(deleted=None)

    @classmethod
    def times_for_date(cls, date):
        """Return a query set with all times for a date."""
        return cls.all_times().filter(date=date)

    def is_fail(self):
        return self.seconds < 0

    def seconds_sort_key(self):
        if self.is_fail():
            return 9999999999999
        return self.seconds

    def time_str(self):
        if self.is_fail():
            return 'fail'

        minutes, seconds = divmod(self.seconds, 60)

        return '{}:{:02}'.format(minutes, seconds)

    def __str__(self):
        if self.deleted:
            maybe_deleted = 'DELETED '
        else:
            maybe_deleted = ''
        return '{}{} - {} - {}'.format(
            maybe_deleted, self.user, self.time_str(), self.date
        )

    @staticmethod
    def streaks(entries):
        """Takes an iterable of times and returns the streaks clumped together."""

        streaks = []
        current_streak = []

        one_day = datetime.timedelta(days=1)

        for entry in sorted(entries, key=attrgetter('date')):
            if not current_streak or entry.date == current_streak[
                    -1].date + one_day:
                # either there wasn't a streak so we should start one, or we maintained a streak
                current_streak.append(entry)
            else:
                # we broke it, create a new one
                streaks.append(current_streak)
                current_streak = [entry]

        if current_streak:
            streaks.append(current_streak)

        return streaks

    @classmethod
    def do_completed(cls, user):
        num_completed = len(cls.all_times().filter(user=user))
        most_recent_milestone = max(
            (n for n in cls.completed_milestones if n <= num_completed),
            default=0
        )
        if not most_recent_milestone:
            return
        title_key = '{}_completed{}_title'.format(
            cls.SLUG, most_recent_milestone
        )
        title = Item.from_key(title_key)

        if user.add_item(title):
            return cls.completed_congrats.format(
                n=most_recent_milestone, games=cls.PLURAL, title=title.name
            )
        return

    @classmethod
    def winning_times(cls, qs=None):
        if qs is None:
            qs = cls.all_times().filter(seconds__gt=0)
        values = qs.values_list('date').annotate(
            winning_time=models.Min('seconds')
        )

        return {date: winning_time for date, winning_time in values}

    @classmethod
    def winners(cls, date):
        entries = cls.times_for_date(date)
        try:
            best = min(e.seconds for e in entries if e.seconds > 0)
            winners = [e for e in entries if e.seconds == best]
            # if there was a best, there must be a winner
            assert winners
            return winners
        except ValueError as e:
            # entries was empty
            return []

    @classmethod
    def wins(cls, user, qs=None):
        if qs is None:
            qs = cls.all_times()
        qs = qs.filter(seconds__gt=0, user=user)
        wins = cls.winning_times()
        return [e for e in qs if e.seconds == wins[e.date]]

    @classmethod
    def win_streaks(cls, user, qs=None):
        wins = cls.wins(user, qs)
        return cls.streaks(wins)

    @classmethod
    # TODO: should this take a date or a timestamp?
    def current_win_streaks(cls, date):
        result = {}
        # get the win streaks up to this date
        qs = cls.all_times().filter(date__lte=date)
        for w in cls.winners(date):
            streaks = cls.win_streaks(w.user, qs)
            latest_streak = streaks[-1]
            # only include the streak if it comes up to this day
            if latest_streak[-1].date == date:
                result[w.user] = latest_streak
        return result

    @classmethod
    def announcement_data(cls, date):
        streaks = [(u, s)
                   for u, s in cls.current_win_streaks(date).items()
                   if len(s) > 1]
        # sort by streak length, descending
        streaks.sort(key=lambda x: len(x[1]), reverse=True)
        streakers = set(u for u, s in streaks)

        # get the winners who were not included in the long streaks
        winners1 = [
            str(w.user) for w in cls.winners(date) if w.user not in streakers
        ]
        yest = date - datetime.timedelta(days=1)
        winners2 = [
            str(w.user) for w in cls.winners(yest) if w.user not in streakers
        ]

        overperformers = [
            (str(m.user), m.residual)
            for m in Prediction.objects.filter(date=date, residual__lte=0
                                               ).order_by('residual')[:3]
        ]

        games = {
            "mini crossword": "https://www.nytimes.com/crosswords/game/mini",
            "easy sudoku":
            "https://www.nytimes.com/crosswords/game/sudoku/easy"
        }

        return {
            'streaks': streaks,
            'winners_today': winners1,
            'winners_yesterday': winners2,
            'overperformers': overperformers,
            'links': games,
        }

    @classmethod
    # TODO: should this be in model?
    def announcement_message(cls, date):

        # get the long streaks
        streaks = [(u, s)
                   for u, s in cls.current_win_streaks(date).items()
                   if len(s) > 1]
        # sort by streak length, descending
        streaks.sort(key=lambda x: len(x[1]), reverse=True)
        streakers = set(u for u, s in streaks)

        # get the winners who were not included in the long streaks
        winners1 = [
            w.user for w in cls.winners(date) if w.user not in streakers
        ]
        yest = date - datetime.timedelta(days=1)
        winners2 = [
            w.user for w in cls.winners(yest) if w.user not in streakers
        ]

        # start with the streak messages
        msgs = [
            '{u} is on a {n}-day streak! {emoji}'.format(
                u=u, n=len(streak), emoji=':fire:' * len(streak)
            ) for u, streak in streaks
        ]

        # now add the other winners
        also = ' also' if streakers else ''
        if winners1:
            msgs.append(comma_and(str(u) for u in winners1) + also + ' won.')
        if winners2:
            msgs.append(
                comma_and(str(u)
                          for u in winners2) + also + ' won the day before.'
            )

        games = {
            "mini crossword": "https://www.nytimes.com/crosswords/game/mini",
            "easy sudoku":
            "https://www.nytimes.com/crosswords/game/sudoku/easy"
        }

        msgs.append("Play today's:")
        for game in games:
            msgs.append("{} : {}".format(game, games[game]))

        return '\n'.join(msgs)

    @classmethod
    def participation_streaks(cls, user, filter_q=None):
        times = cls.all_times().filter(user_id=user)
        if filter_q:
            times = times.filter(filter_q)

        return cls.streaks(times)


class MiniCrosswordTime(CommonTime):
    SHORT_NAME = 'Mini'
    SLUG = 'mini'
    PLURAL = 'mini crosswords'
    pass


class CrosswordTime(CommonTime):
    SHORT_NAME = 'Crossword'
    SLUG = 'crossword'
    PLURAL = 'regular crosswords'
    pass


class EasySudokuTime(CommonTime):
    SHORT_NAME = 'Sudoku'
    SLUG = 'sudoku'
    PLURAL = 'sudokus'
    pass


class Prediction(models.Model):
    class Meta:
        unique_together = (('user', 'date'), )

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    date = models.DateField()
    prediction = models.FloatField()
    residual = models.FloatField()


class PredictionUser(models.Model):
    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    skill = models.FloatField()
    skill_25 = models.FloatField()
    skill_75 = models.FloatField()


class PredictionDate(models.Model):
    date = models.DateField()
    difficulty = models.FloatField()
    difficulty_25 = models.FloatField()
    difficulty_75 = models.FloatField()


class PredictionParameter(models.Model):
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
    when_run = models.DateTimeField()


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
            arg_str = ' (takes {} arg{})'.format(
                nargs, '' if nargs == 1 else 's'
            )
        else:
            arg_str = ''

        # return '{} - {}'.format(self.name, self.user)

        return '*{}* by {}{}:\n {}'.format(
            self.name, self.user, arg_str, self.command
        )


# Items are stored in YAML (not the DB) but loaded here for convenience


# TODO: ensure this class is immutable? Or reload from YAML details every time?
class Item:
    ITEMS = {}

    def __init__(self, key, options):
        """Only used on initialization, do not call elsewhere."""
        self.key = key
        self.name = options['name']
        # use setattr and defaults in getter methods?
        self.droppable = options.get('droppable', True)
        self.tradeable = options.get('tradeable', True)
        self.unique = options.get('unique', False)
        self.rarity = options.get('rarity', 1.0)
        self.image_name = options.get('image_name', None)
        self.type = options.get('type', None)
        self.game_specific = options.get('game_specific', False)

    @classmethod
    def load_items(cls):
        with open(path.join(path.dirname(__file__), 'items.yaml')) as f:
            for key, options in yaml.load(f).items():
                if key.startswith('__'):
                    continue
                if options.get('game_specific', False):
                    for game_cls in CommonTime.__subclasses__():
                        game_key = '{}_{}'.format(game_cls.SLUG, key)
                        formatter_options = {
                            'slug': game_cls.SLUG,
                            'short': game_cls.SHORT_NAME
                        }
                        game_options = {
                            k: (
                                v.format(**formatter_options)
                                if isinstance(v, str) else v
                            )
                            for (k, v) in options.items()
                        }
                        cls.ITEMS[game_key] = Item(game_key, game_options)
                else:
                    cls.ITEMS[key] = Item(key, options)

    @classmethod
    def from_key(cls, key):
        return cls.ITEMS.get(key, None)

    @classmethod
    def choose_droppable(cls):
        """Drop a randomly chosen Item from this class, or None. First, selects
        whether or not to drop a randomly chosen Item based on the global drop
        rate, then selects from all droppable items weighted by their rarity.
        Does not create an ownership record.

        Returns:
            An Item or None.
        """

        if random.random() > ITEM_DROP_RATE:
            return None

        droppables = [item for item in cls.ITEMS.values() if item.droppable]

        if not droppables:
            return None

        return random.choices(
            droppables, [item.rarity for item in droppables]
        )[0]

    def image_url(self):
        if not self.image_name:
            return None
        return static('crossbot/img/items/%s' % self.image_name)

    def is_hat(self):
        return self.type == 'hat'

    def is_title(self):
        return self.type == 'title'

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Item) and self.key == other.key

    def __hash__(self):
        return hash(self.key)


# Load all the items into memory
Item.load_items()


class ItemOwnershipRecord(models.Model):
    class Meta:
        unique_together = (('owner', 'item_key'), )

    owner = models.ForeignKey(CBUser, models.CASCADE)
    item_key = models.CharField(max_length=40)
    quantity = models.IntegerField(default=0)

    @property
    def item(self):
        return Item.from_key(self.item_key)

    def __str__(self):
        return '%s: %s %s(s)' % (self.owner, self.quantity, self.item)
