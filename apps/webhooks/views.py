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
    # Buscar la cabecera en diferentes formatos
    signature_header = (request.headers.get('X-ElevenLabs-Signature') or
                       request.headers.get('X-Elevenlabs-Signature') or
                       request.headers.get('HTTP_X_ELEVENLABS_SIGNATURE'))
    
    if not signature_header:
        logger.warning("No signature header found. Headers: %s", list(request.headers.keys()))
        return False
    
    logger.info(f"Raw signature header: {signature_header}")
    
    # ElevenLabs puede enviar "sha256=hash" o solo el hash
    signature = signature_header
    if signature_header.startswith('sha256='):
        signature = signature_header[7:]  # Quitar "sha256="
        logger.info("Detected 'sha256=' prefix, extracted hash")
    elif signature_header.startswith('v1='):
        # Algunos servicios usan formato v1=...
        signature = signature_header[3:]
        logger.info("Detected 'v1=' prefix, extracted hash")
    
    secret_bytes = secret.encode('utf-8')
    body = request.body
    
    # Logs para depuración
    logger.debug(f"Body length: {len(body)}")
    logger.debug(f"Body preview: {body[:200]}")
    
    # Calcular HMAC
    expected = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
    
    logger.info(f"Expected signature: {expected}")
    logger.info(f"Received signature: {signature}")
    
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
        logger.info(f"Payload keys: {list(payload.keys()) if payload else 'empty'}")
    except json.JSONDecodeError:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')
        logger.info(f"Raw body (non-JSON): {raw_body[:200]}")

    entry = WebhookEntry.objects.create(
        endpoint=endpoint,
        method=request.method,
        payload=payload,
        raw_body=raw_body,
    )
    logger.info(f"Created webhook entry {entry.id}")

    # Associate agent
    agent_id = request.GET.get('agent_id')
    if not agent_id and payload:
        agent_id = payload.get('agent_id') or payload.get('agentId')
    if agent_id:
        try:
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
            logger.info(f"Associated agent: {agent.name} (ID: {agent.agent_id})")
        except Agent.DoesNotExist:
            logger.warning(f"Agent with ID {agent_id} not found")

    # Handle call_ended
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        
        if not secret:
            logger.error("ELEVENLABS_SECRET_CALL_ENDED not configured!")
            return HttpResponseBadRequest("Server configuration error")
        
        if not verify_elevenlabs_signature(request, secret):
            logger.error(f"Invalid signature for call_ended. Entry ID: {entry.id}")
            return HttpResponseBadRequest("Invalid signature")
        
        logger.info(f"Signature verified successfully for call_ended")

        try:
            result = handle_call_ended(entry)
            entry.processed = True
            entry.save(update_fields=['processed'])
            logger.info(f"call_ended processed successfully: {result}")
        except Exception as e:
            logger.exception(f"Error processing call_ended: {e}")
            entry.processed = True
            entry.save(update_fields=['processed'])
            return JsonResponse({"status": "error", "error": str(e)}, status=500)
            
        return JsonResponse({"status": "success", "webhook_id": entry.id})

    # Other endpoints
    entry.processed = True
    entry.save(update_fields=['processed'])
    return JsonResponse({"status": "success", "webhook_id": entry.id})