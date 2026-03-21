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

def verify_elevenlabs_signature(request, secret):
    """
    Verifica la firma HMAC-SHA256 enviada por ElevenLabs usando el secret dado.
    """
    signature = request.headers.get('X-ElevenLabs-Signature')
    if not signature:
        return False
    secret = secret.encode()
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
    # --- Verificación según endpoint ---
    if endpoint == 'call_ended':
        # Verificación HMAC para call_ended
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        if secret:
            if not verify_elevenlabs_signature(request, secret):
                return HttpResponseBadRequest("Invalid signature")
    elif endpoint == 'morgan_quote':
        # Verificación simple por cabecera ELEVENLABS_SECRET
        expected_secret = settings.ELEVENLABS_SECRET
        if expected_secret:
            received_secret = request.headers.get('ELEVENLABS_SECRET')
            if not received_secret or received_secret != expected_secret:
                return HttpResponseBadRequest("Invalid secret")
    # Para otros endpoints, si se desea verificación, se puede añadir aquí
    # Si no hay verificación definida, se continúa sin comprobar

    # --- Guardar entrada ---
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