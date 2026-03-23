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
    """Verify HMAC-SHA256 signature from ElevenLabs.
    Expected header format: t=<timestamp>,v0=<signature>
    Signature is HMAC of '<timestamp>.<body>' with the secret.
    """
    header = request.headers.get('Elevenlabs-Signature')
    if not header:
        print("No signature header found")
        return False

    print(f"Raw signature header: {header}")

    # Parsear el header
    parts = {}
    for item in header.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            parts[key] = value

    timestamp = parts.get('t')
    signature = parts.get('v0')  # ElevenLabs usa v0 actualmente

    if not timestamp or not signature:
        print("Missing timestamp or v0 in signature header")
        return False

    print(f"Timestamp: {timestamp}")
    print(f"Signature (v0): {signature}")

    secret_bytes = secret.encode('utf-8')
    body = request.body

    # Construir el mensaje: timestamp + "." + body (en bytes)
    # Nota: el timestamp debe ser string, el body es bytes
    message = timestamp.encode('utf-8') + b'.' + body
    print(f"Message length: {len(message)}")
    print(f"Message preview (first 200 bytes): {message[:200]}")

    expected = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()

    print("=== DEBUG SIGNATURE ===")
    print(f"Secret (first 10): {secret[:10]}...")
    print(f"Body length: {len(body)}")
    print(f"Body hex (first 100): {body[:100].hex()}")
    print(f"Expected signature: {expected}")
    print(f"Received signature: {signature}")
    print(f"Match: {expected == signature}")
    print("=========================")

    return hmac.compare_digest(expected, signature)

@csrf_exempt
@require_POST
def webhook_receiver(request, endpoint):
    """Generic webhook receiver."""
    print(f"Webhook received for endpoint '{endpoint}'")
    print(f"Headers: {dict(request.headers)}")

    try:
        payload = json.loads(request.body)
        raw_body = ''
        print(f"Payload parsed. Keys: {list(payload.keys()) if payload else 'empty'}")
    except json.JSONDecodeError as e:
        payload = {}
        raw_body = request.body.decode('utf-8', errors='replace')
        print(f"JSON decode error: {e}")
        print(f"Raw body (first 500): {raw_body[:500]}")

    entry = WebhookEntry.objects.create(
        endpoint=endpoint,
        method=request.method,
        payload=payload,
        raw_body=raw_body,
    )
    print(f"Created WebhookEntry ID: {entry.id}")

    # Asociar agente...
    agent_id = request.GET.get('agent_id')
    if not agent_id and payload:
        # Buscar en la raíz del payload
        agent_id = payload.get('agent_id') or payload.get('agentId') or payload.get('conversation_agent_id')
        # Si no se encuentra, buscar dentro de 'data' si existe
        if not agent_id and isinstance(payload.get('data'), dict):
            data = payload['data']
            agent_id = data.get('agent_id') or data.get('agentId') or data.get('conversation_agent_id')

    if agent_id:
        try:
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
            print(f"Agent associated: {agent.name}")
        except Agent.DoesNotExist:
            print(f"Agent with ID {agent_id} not found")
    else:
        print("No agent_id found")

    # Manejar call_ended
    if endpoint == 'call_ended':
        secret = settings.ELEVENLABS_SECRET_CALL_ENDED
        if not secret:
            print("ELEVENLABS_SECRET_CALL_ENDED not configured!")
            return HttpResponseBadRequest("Missing secret")

        print(f"Secret loaded (first 20): {secret[:20]}...")

        if not verify_elevenlabs_signature(request, secret):
            print(f"Invalid signature for call_ended. Entry ID: {entry.id}")
            return HttpResponseBadRequest("Invalid signature")

        print("Signature verified")
        try:
            result = handle_call_ended(entry)
            entry.processed = True
            entry.save(update_fields=['processed'])
            print(f"call_ended processed: {result}")
            return JsonResponse({"status": "success", "webhook_id": entry.id, "result": result})
        except Exception as e:
            print(f"Error processing: {e}")
            entry.processed = True
            entry.save(update_fields=['processed'])
            return JsonResponse({"status": "error", "error": str(e)}, status=500)

    # Otros endpoints...
    print(f"Generic endpoint '{endpoint}'")
    entry.processed = True
    entry.save(update_fields=['processed'])
    return JsonResponse({"status": "success", "webhook_id": entry.id})