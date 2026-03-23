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
    # La cabecera exacta que envía ElevenLabs es 'Elevenlabs-Signature'
    signature = request.headers.get('Elevenlabs-Signature')
    
    if not signature:
        # Fallback para otras variaciones
        signature = (request.headers.get('X-ElevenLabs-Signature') or
                    request.headers.get('X-Elevenlabs-Signature'))
    
    if not signature:
        logger.warning("No signature header found. Headers: %s", list(request.headers.keys()))
        return False
    
    logger.info(f"Signature header found")
    
    # Quitar prefijo 'sha256=' si existe
    if signature.startswith('sha256='):
        signature = signature[7:]
        logger.info("Removed 'sha256=' prefix")
    
    secret_bytes = secret.encode('utf-8')
    body = request.body
    
    # Calcular HMAC
    expected = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
    
    # Logs para depuración (opcional, puedes comentarlos después)
    logger.debug(f"Expected: {expected[:20]}...")
    logger.debug(f"Received: {signature[:20]}...")
    
    result = hmac.compare_digest(expected, signature)
    logger.info(f"Signature verification: {'SUCCESS' if result else 'FAILED'}")
    
    return result

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """Generic webhook receiver."""
    logger.info(f"Webhook received for endpoint '{endpoint}'")
    
    # Parse payload
    try:
        payload = json.loads(request.body)
        raw_body = ''
    except json.JSONDecodeError:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')

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
            logger.info(f"Agent associated: {agent.name}")
        except Agent.DoesNotExist:
            logger.warning(f"Agent with ID {agent_id} not found")

    # Manejar call_ended
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        
        if not secret:
            logger.error("ELEVENLABS_SECRET_CALL_ENDED not configured")
            return HttpResponseBadRequest("Server configuration error")
        
        if not verify_elevenlabs_signature(request, secret):
            logger.error(f"Invalid signature for call_ended. Entry ID: {entry.id}")
            return HttpResponseBadRequest("Invalid signature")
        
        logger.info(f"Signature verified successfully")

        try:
            result = handle_call_ended(entry)
            entry.processed = True
            entry.save(update_fields=['processed'])
            logger.info(f"call_ended processed: {result}")
        except Exception as e:
            logger.exception(f"Error processing call_ended: {e}")
            entry.processed = True
            entry.save(update_fields=['processed'])
            return JsonResponse({"status": "error", "error": str(e)}, status=500)
            
        return JsonResponse({"status": "success", "webhook_id": entry.id})

    # Otros endpoints
    entry.processed = True
    entry.save(update_fields=['processed'])
    return JsonResponse({"status": "success", "webhook_id": entry.id})