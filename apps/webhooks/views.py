import json
import threading
import hmac
import hashlib
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import WebhookEntry
from .handlers import run_handler
from agents.models import Agent

def verify_elevenlabs_signature(request):
    """
    Verifica la firma HMAC-SHA256 enviada por ElevenLabs.
    """
    signature = request.headers.get('X-ElevenLabs-Signature')
    if not signature:
        return False
    secret = settings.ELEVENLABS_WEBHOOK_SECRET.encode()
    body = request.body
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """
    Vista genérica para recibir webhooks.
    Guarda la petición y dispara el handler correspondiente.
    """
    # Verificar firma para endpoints que lo requieran
    if endpoint in ('call_ended', 'morgan_quote') and settings.ELEVENLABS_WEBHOOK_SECRET:
        if not verify_elevenlabs_signature(request):
            return HttpResponseBadRequest("Invalid signature")

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

    # Asociar agente si se proporciona ?agent_id= o viene en el payload
    agent_id = request.GET.get('agent_id')
    if not agent_id and payload:
        agent_id = payload.get('agent_id') or payload.get('agentId')
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