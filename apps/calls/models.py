# calls/models.py
from django.db import models
from agents.models import Agent

class Call(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('failed', 'Failed'),
        ('interrupted', 'Interrupted')
    ]
    
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='calls')
    call_id = models.CharField(max_length=100, unique=True)
    duration_seconds = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    cost = models.PositiveIntegerField(default=0, help_text="Costo en créditos de ElevenLabs")
    termination_reason = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=10, blank=True)
    
    call_data = models.JSONField(default=dict)
    
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Call {self.call_id[:8]}..."
    
    @property
    def minutes_consumed(self):
        return (self.duration_seconds + 59) // 60