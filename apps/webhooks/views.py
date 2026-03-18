import json
import threading
from django.db import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import WebhookEntry
from .handlers import run_handler
from agents.models import Agent
from users.models import User

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """
    Vista genérica para recibir webhooks.
    Guarda la petición y dispara el handler correspondiente.
    """
    # Guardar entrada
    try:
        payload = json.loads(request.body)
        raw_body = ''
    except json.JSONDecodeError:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')

    entry = WebhookEntry.objects.create(
        endpoint=endpoint,
        method=request.method,
        headers=dict(request.headers),
        payload=payload,
        raw_body=raw_body,
    )

    # Asociar agente si se proporciona ?agent_id=
    agent_id = request.GET.get('agent_id')
    if agent_id:
        try:
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
        except Agent.DoesNotExist:
            pass

    # Ejecutar handler en segundo plano
    threading.Thread(target=run_handler, args=(entry.id,)).start()

    return JsonResponse({
        "status": "success",
        "webhook_id": entry.id,
        "mensaje": "Webhook recibido y en proceso."
    })

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