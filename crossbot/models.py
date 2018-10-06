from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

import crossbot.slack


class MyUser(User):

    class Meta:
        proxy = True

    def __str__(self):
        try:
            slack_user = SlackUser.objects.get(user=self)
            return str(slack_user)
        except SlackUser.DoesNotExist:
            return self.username


class SlackUser(models.Model):
    slackid = models.CharField(max_length=10, primary_key=True)
    slackname = models.CharField(max_length=100)
    user = models.ForeignKey(MyUser, null=True, on_delete=models.SET_NULL)

    @classmethod
    def update_all_from_slack(cls):
        users = crossbot.slack.slack_users()
        for user_json in users:
            u, created = cls.objects.get_or_create(slackid=user_json['id'])
            print(user_json['name'])
            u.slackname = user_json['name']
            u.save()

    def __str__(self):
        if self.slackname:
            return self.slackname
        else:
            return self.slackid


class CommonTime(models.Model):
    user = models.ForeignKey(MyUser, null=True, on_delete=models.SET_NULL)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        abstract = True

    def time_str(self):
        if self.seconds < 0:
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


class QueryShorthands(models.Model):
    user = models.ForeignKey(MyUser, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    command = models.TextField()
    timestamp = models.DateTimeField(null=True)

    def __str__(self):
        return '{} - {}'.format(self.name, self.user)
