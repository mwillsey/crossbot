from django.contrib import admin
import requests

import crossbot.models as models

admin.site.register(models.MyUser)
admin.site.register(models.SlackUser)

admin.site.register(models.MiniCrosswordTime)
admin.site.register(models.CrosswordTime)
admin.site.register(models.EasySudokuTime)

admin.site.register(models.QueryShorthands)
