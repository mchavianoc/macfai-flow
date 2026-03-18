from django.db import models

from users.models import User
from agents.models import Agent

class WebhookEntry(models.Model):
    endpoint = models.SlugField()
    method = models.CharField(max_length=10)
    headers = models.JSONField(default=dict)
    payload = models.JSONField(default=dict)
    raw_body = models.TextField(blank=True)
    agent = models.ForeignKey(Agent, null=True, blank=True, on_delete=models.SET_NULL, related_name='webhooks')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='webhooks')
    processed = models.BooleanField(default=False)
    processing_result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.endpoint} - {self.created_at}"