import datetime

from django.urls import path
from django.http import HttpResponse
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required

from . import views


@login_required
def private(request):
    html = '<html><body>You are logged in!<br><a href="/logout/">Logout.</a></body></html>'
    return HttpResponse(html)


urlpatterns = [
    path('slack/', views.slash_command, name='slash_command'),
    path('api-event/', views.event, name='event'),
    path('private/', private),
    path('', TemplateView.as_view(template_name='crossbot/index.html'), name='home')
]
