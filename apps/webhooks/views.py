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
from .handlers.call_ended import handle as handle_call_ended   # import directly

logger = logging.getLogger(__name__)

def verify_elevenlabs_signature(request, secret):
    """Verify HMAC-SHA256 signature from ElevenLabs."""
    signature = request.headers.get('X-ElevenLabs-Signature') or \
                request.headers.get('X-Elevenlabs-Signature')
    if not signature:
        logger.warning("No X-ElevenLabs-Signature header found")
        return False
    secret = secret.encode()
    body = request.body
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """Generic webhook receiver."""
    logger.info(f"Received webhook for endpoint '{endpoint}'")

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

    # Associate agent if possible (from query param or payload)
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

    # Handle special endpoint 'call_ended' with HMAC validation
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        if not secret:
            logger.error("ELEVENLABS_SECRET_CALL_ENDED not set")
            return HttpResponseBadRequest("Server misconfiguration")

        if not verify_elevenlabs_signature(request, secret):
            logger.warning(f"Invalid HMAC signature for call_ended. Entry ID: {entry.id}")
            return HttpResponseBadRequest("Invalid signature")

        # Process call_ended synchronously (or could be threaded if long)
        try:
            result = handle_call_ended(entry)
            entry.processed = True
            # No processing_result stored – we just log if needed
            entry.save(update_fields=['processed'])
            logger.info(f"call_ended processed: {result}")
        except Exception as e:
            logger.exception(f"Error processing call_ended: {e}")
            # Still mark as processed to avoid retries, but log error
            entry.processed = True
            entry.save(update_fields=['processed'])
        return JsonResponse({"status": "success", "webhook_id": entry.id})

    # For all other endpoints, just store the entry and return
    entry.processed = True
    entry.save(update_fields=['processed'])
    return JsonResponse({"status": "success", "webhook_id": entry.id})