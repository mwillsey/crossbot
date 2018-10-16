"""crossbot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import datetime

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def index(request):
    now = datetime.datetime.now()
    html = "<html><body>It is now %s. crossbot is up and running!</body></html>" % now
    return HttpResponse(html)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('slack/', include('crossbot.urls')),
    path('', index),
]
