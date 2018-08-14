from django.db import models

# Create your models here.


class MiniCrosswordTime(models.Model):
    userid = models.TextField()
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True)
