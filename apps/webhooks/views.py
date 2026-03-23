import json
import hmac
import hashlib
import logging
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import WebhookEntry
from agents.models import Agent
from .handlers.call_ended import handle as handle_call_ended

logger = logging.getLogger(__name__)

def verify_elevenlabs_signature(request, secret):
    """Verify HMAC-SHA256 signature from ElevenLabs."""
    # Probar diferentes variaciones del nombre
    signature = (request.headers.get('X-ElevenLabs-Signature') or
                request.headers.get('X-Elevenlabs-Signature') or
                request.headers.get('HTTP_X_ELEVENLABS_SIGNATURE') or
                request.headers.get('ElevenLabs-Signature'))
    
    if not signature:
        logger.warning("No se encontró cabecera de firma. Cabeceras: %s", 
                      list(request.headers.keys()))
        return False
    
    secret = secret.encode()
    body = request.body
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    return hmac.compare_digest(expected, signature)

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """Generic webhook receiver."""
    logger.info(f"Webhook recibido para endpoint '{endpoint}'")
    logger.info(f"Cabeceras: {dict(request.headers)}")
    
    # Parse payload
    try:
        payload = json.loads(request.body)
        raw_body = ''
        logger.info(f"Payload: {json.dumps(payload, indent=2)[:500]}")  # Log parcial
    except json.JSONDecodeError:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')
        logger.info(f"Raw body: {raw_body[:500]}")

    entry = WebhookEntry.objects.create(
        endpoint=endpoint,
        method=request.method,
        payload=payload,
        raw_body=raw_body,
    )

    # Asociar agente
    agent_id = request.GET.get('agent_id')
    if not agent_id and payload:
        agent_id = payload.get('agent_id') or payload.get('agentId')
    if agent_id:
        try:
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
            logger.info(f"Agente asociado: {agent.name}")
        except Agent.DoesNotExist:
            logger.warning(f"Agente con ID {agent_id} no encontrado")

    # Manejar call_ended
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        
        if secret:
            if not verify_elevenlabs_signature(request, secret):
                logger.error(f"Firma inválida para call_ended. Entry ID: {entry.id}")
                return HttpResponseBadRequest("Firma inválida")
            logger.info(f"Firma verificada correctamente para call_ended")
        else:
            logger.warning("ELEVENLABS_SECRET_CALL_ENDED no configurado")

        try:
            result = handle_call_ended(entry)
            entry.processed = True
            entry.save(update_fields=['processed'])
            logger.info(f"call_ended procesado: {result}")
        except Exception as e:
            logger.exception(f"Error procesando call_ended: {e}")
            entry.processed = True
            entry.save(update_fields=['processed'])
            return JsonResponse({"status": "error", "error": str(e)}, status=500)
            
        return JsonResponse({"status": "success", "webhook_id": entry.id})

    # Otros endpoints
    entry.processed = True
    entry.save(update_fields=['processed'])
    return JsonResponse({"status": "success", "webhook_id": entry.id})