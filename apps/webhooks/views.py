import json
import threading
import hmac
import hashlib
import logging
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import WebhookEntry
from .handlers import run_handler
from agents.models import Agent

logger = logging.getLogger(__name__)

def verify_elevenlabs_signature(request, secret):
    """
    Verifies the HMAC-SHA256 signature sent by ElevenLabs.
    """
    # Headers are case-insensitive in Django, but we'll try both common variants
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
    """
    Generic webhook receiver. Saves the request and triggers the appropriate handler.
    Now always saves the incoming request (even if validation fails) for debugging.
    """
    # Log all headers for debugging
    logger.info(f"Received webhook for endpoint '{endpoint}'")
    logger.debug(f"Headers: {dict(request.headers)}")

    # --- Parse and save entry first (so we always have a record) ---
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

    # --- Perform endpoint-specific validation ---
    validation_failed = False
    error_message = None

    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        if secret:
            if not verify_elevenlabs_signature(request, secret):
                logger.warning(f"Invalid HMAC signature for call_ended. Entry ID: {entry.id}")
                validation_failed = True
                error_message = "Invalid signature"
        else:
            logger.warning("ELEVENLABS_SECRET_CALL_ENDED not set, skipping signature check")

    elif endpoint == 'morgan_quote':
        expected_secret = settings.ELEVENLABS_SECRET
        if expected_secret:
            # Look for the secret header (case-insensitive)
            received_secret = request.headers.get('ElevenLabs-Secret') or \
                              request.headers.get('elevenlabs_secret')
            if not received_secret:
                logger.warning(f"No ElevenLabs-Secret header found. Headers: {dict(request.headers)}")
                validation_failed = True
                error_message = "Missing secret header"
            elif received_secret != expected_secret:
                logger.warning(f"Invalid secret for morgan_quote: expected '{expected_secret}', got '{received_secret}'")
                validation_failed = True
                error_message = "Invalid secret"
        else:
            logger.warning("ELEVENLABS_SECRET not set, skipping secret check")

    # If validation failed, update the entry and return 400
    if validation_failed:
        entry.processing_result = {"error": error_message}
        entry.save(update_fields=['processing_result'])
        return HttpResponseBadRequest(error_message)

    # --- Validation passed: associate agent (if possible) ---
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

    # --- Start background handler ---
    threading.Thread(target=run_handler, args=(entry.id,)).start()

    return JsonResponse({
        "status": "success",
        "webhook_id": entry.id,
        "mensaje": "Webhook recibido y en proceso."
    })