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
    For 'call_ended', HMAC signature is mandatory. All other endpoints accept any request.
    """
    logger.info(f"Received webhook for endpoint '{endpoint}'")
    logger.debug(f"Headers: {dict(request.headers)}")

    # Parse and save entry first (so we always have a record)
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

    # --- HMAC validation for call_ended (mandatory) ---
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        if not secret:
            logger.error("ELEVENLABS_SECRET_CALL_ENDED not set, cannot validate HMAC")
            entry.processing_result = {"error": "Server misconfiguration: HMAC secret missing"}
            entry.save(update_fields=['processing_result'])
            return HttpResponseBadRequest("Server misconfiguration")

        if not verify_elevenlabs_signature(request, secret):
            logger.warning(f"Invalid HMAC signature for call_ended. Entry ID: {entry.id}")
            entry.processing_result = {"error": "Invalid signature"}
            entry.save(update_fields=['processing_result'])
            return HttpResponseBadRequest("Invalid signature")

    # For all other endpoints, no authentication is performed.

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

    # Start background handler
    threading.Thread(target=run_handler, args=(entry.id,)).start()

    return JsonResponse({
        "status": "success",
        "webhook_id": entry.id,
        "mensaje": "Webhook recibido y en proceso."
    })