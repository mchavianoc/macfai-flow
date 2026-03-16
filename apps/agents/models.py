from django.db import models
from django.conf import settings

class Agent(models.Model):
    """
    Representa un agente de ElevenLabs perteneciente a un cliente.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='agents'
    )
    name = models.CharField(max_length=100)
    agent_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"