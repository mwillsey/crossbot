from django.urls import path
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test

from . import views

urlpatterns = [
    path('slack/', views.slash_command, name='slash_command'),
    path('rest-api/times/<time_model>/', views.times_rest_api),
    path('rest-api/times/', views.times_rest_api),
    path(
        'plot/',
        login_required(
            TemplateView.as_view(template_name='crossbot/plot.html')
        ),
        name='plot'
    ),
    path('inventory/equip-item/', views.equip_item, name='equip_item'),
    path(
        'inventory/unequip-<item_type>/',
        views.unequip_item,
        name='unequip_item'
    ),
    path(
        'inventory/',
        user_passes_test(lambda u: u.is_staff)(
            TemplateView.as_view(template_name='crossbot/inventory.html')
        ),
        name='inventory'
    ),
    path('', views.home, name='home')
]
