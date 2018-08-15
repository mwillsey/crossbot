from django.db import models
from django.contrib.auth.models import User

class SlackUser(models.Model):
    slackid = models.CharField(max_length=10, primary_key=True)
    slackname = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

class CommonTime(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True)

    # db = 'public'
    class Meta:
        abstract = True

class MiniCrosswordTime(CommonTime):
    pass

class CrosswordTime(CommonTime):
    pass

class EasySudokuTime(CommonTime):
    pass

class QueryShorthands(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    command = models.TextField()
    timestamp = models.DateTimeField(null=True)
