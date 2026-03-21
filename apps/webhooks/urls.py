from django.urls import path
from . import views

urlpatterns = [
    path('<slug:endpoint>', views.webhook_receiver, name='webhook-receiver'),
]