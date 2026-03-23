from django.urls import re_path
from . import views

urlpatterns = [
    # Accept endpoint with or without trailing slash
    re_path(r'^(?P<endpoint>[-\w]+)/?$', views.webhook_receiver, name='webhook-receiver'),
]