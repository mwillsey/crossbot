from django.urls import path
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('slack/', views.slash_command, name='slash_command'),
    path('api-event/', views.event, name='event'),
    path('rest-api/times/<time_model>/', views.times_rest_api),
    path('rest-api/times/', views.times_rest_api),
    path(
        'plot/',
        login_required(
            TemplateView.as_view(template_name='crossbot/plot.html')),
        name='plot'),
    path(
        '',
        TemplateView.as_view(template_name='crossbot/index.html'),
        name='home')
]
