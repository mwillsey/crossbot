import datetime

from django.urls import path
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from . import views


def index(request):
    now = datetime.datetime.now()
    html = "<html><body>It is now %s. crossbot is up and running!</body></html>" % now
    return HttpResponse(html)

@login_required
def private(request):
    html = '<html><body>You are logged in!<br><a href="/logout/">Logout.</a></body></html>'
    return HttpResponse(html)


urlpatterns = [
    path('slack/', views.slash_command, name='slash_command'),
    path('api-event/', views.event, name='event'),
    path('private/', private, name='event'),
    path('', index)
]
