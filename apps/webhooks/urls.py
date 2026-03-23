from django.urls import path
from . import views

urlpatterns = [
    # Accept endpoint without trailing slash (webhooks typically don't have slashes)
    path('<slug:endpoint>/', views.webhook_receiver, name='webhook-receiver'),
    # Also accept with trailing slash for completeness
    path('<slug:endpoint>', views.webhook_receiver, name='webhook-receiver-no-slash'),
]