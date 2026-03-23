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
    # Obtener la cabecera exacta que ElevenLabs envía
    signature = request.headers.get('Elevenlabs-Signature')
    
    if not signature:
        logger.warning("No signature header found. Headers: %s", list(request.headers.keys()))
        return False
    
    logger.info(f"Raw signature header: {signature}")
    
    # Quitar prefijo 'sha256=' si existe
    if signature.startswith('sha256='):
        signature = signature[7:]
        logger.info("Removed 'sha256=' prefix")
    
    secret_bytes = secret.encode('utf-8')
    body = request.body
    
    # Calcular HMAC
    expected = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
    
    # LOGS DETALLADOS PARA DEPURACIÓN
    logger.info("=" * 50)
    logger.info("SIGNATURE DEBUG INFO:")
    logger.info(f"Secret (first 10 chars): {secret[:10]}...")
    logger.info(f"Body length: {len(body)} bytes")
    logger.info(f"Body hex (first 100): {body[:100].hex()}")
    logger.info(f"Body preview (first 300 chars): {body[:300]}")
    logger.info(f"Expected signature: {expected}")
    logger.info(f"Received signature: {signature}")
    logger.info(f"Signatures match: {expected == signature}")
    logger.info("=" * 50)
    
    return hmac.compare_digest(expected, signature)

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """Generic webhook receiver."""
    logger.info(f"Webhook received for endpoint '{endpoint}'")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    # Parse payload
    try:
        payload = json.loads(request.body)
        raw_body = ''
        logger.info(f"Payload parsed successfully. Keys: {list(payload.keys()) if payload else 'empty'}")
    except json.JSONDecodeError as e:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')
        logger.warning(f"JSON decode error: {e}")
        logger.info(f"Raw body (first 500 chars): {raw_body[:500]}")

    # Crear entrada en la base de datos
    entry = WebhookEntry.objects.create(
        endpoint=endpoint,
        method=request.method,
        payload=payload,
        raw_body=raw_body,
    )
    logger.info(f"Created WebhookEntry with ID: {entry.id}")

    # Asociar agente si es posible
    agent_id = request.GET.get('agent_id')
    if not agent_id and payload:
        agent_id = payload.get('agent_id') or payload.get('agentId') or payload.get('conversation_agent_id')
    
    if agent_id:
        try:
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
            logger.info(f"Agent associated: {agent.name} (ID: {agent.agent_id})")
        except Agent.DoesNotExist:
            logger.warning(f"Agent with ID {agent_id} not found")
    else:
        logger.info("No agent_id found in request or payload")

    # Manejar endpoint específico 'call_ended'
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        
        # Verificar que el secreto está configurado
        if not secret:
            logger.error("ELEVENLABS_SECRET_CALL_ENDED is not configured in settings!")
            logger.error("Please set this environment variable and restart the server")
            return HttpResponseBadRequest("Server configuration error: missing secret")
        
        logger.info(f"Secret loaded (first 20 chars): {secret[:20]}...")
        
        # Verificar la firma
        if not verify_elevenlabs_signature(request, secret):
            logger.error(f"Invalid signature for call_ended. Entry ID: {entry.id}")
            return HttpResponseBadRequest("Invalid signature")
        
        logger.info(f"Signature verified successfully for call_ended webhook")
        
        # Procesar el webhook
        try:
            result = handle_call_ended(entry)
            entry.processed = True
            entry.save(update_fields=['processed'])
            logger.info(f"call_ended processed successfully. Result: {result}")
            return JsonResponse({"status": "success", "webhook_id": entry.id, "result": result})
        except Exception as e:
            logger.exception(f"Error processing call_ended webhook: {e}")
            entry.processed = True
            entry.save(update_fields=['processed'])
            return JsonResponse({"status": "error", "error": str(e)}, status=500)
    
    # Para cualquier otro endpoint, solo almacenar y responder
    logger.info(f"Processing generic endpoint '{endpoint}'")
    entry.processed = True
    entry.save(update_fields=['processed'])
    
    return JsonResponse({
        "status": "success", 
        "webhook_id": entry.id,
        "message": f"Webhook for '{endpoint}' received and stored"
    })