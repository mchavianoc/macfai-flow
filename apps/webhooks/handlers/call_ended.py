# apps/webhooks/handlers/call_ended.py

from django.utils import timezone
from calls.models import Call
from agents.models import Agent

def handle(entry):
    """
    Process call_ended webhook from ElevenLabs.
    Also supports post_call_transcription events where data is inside 'data'.
    """
    print(f"Processing call_ended webhook {entry.id}")
    payload = entry.payload

    # Helper para obtener un campo desde payload, buscando dentro de 'data' si no está en raíz
    def get_field(key, default=None):
        # Buscar en raíz
        value = payload.get(key)
        if value is not None:
            return value
        # Buscar dentro de 'data'
        data = payload.get('data', {})
        return data.get(key, default)

    # Extraer campos
    call_id = get_field('call_id')
    duration_seconds = get_field('duration_seconds', 0)
    status = get_field('status', 'completed')
    started_at = get_field('started_at')
    ended_at = get_field('ended_at')
    agent_id_from_payload = get_field('agent_id') or get_field('agentId') or get_field('conversation_agent_id')

    if not call_id:
        print(f"No call_id found in payload for entry {entry.id}")
        return {"error": "call_id missing"}

    # Usar agente ya asociado o buscarlo por ID
    agent = entry.agent
    if not agent and agent_id_from_payload:
        try:
            agent = Agent.objects.get(agent_id=agent_id_from_payload)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
        except Agent.DoesNotExist:
            print(f"Agent with ID {agent_id_from_payload} not found")
            return {"error": "Agent not found"}

    if not agent:
        print("No agent associated")
        return {"error": "No agent associated"}

    # Convertir timestamps si son strings
    if started_at and isinstance(started_at, str):
        started_at = timezone.datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if ended_at and isinstance(ended_at, str):
        ended_at = timezone.datetime.fromisoformat(ended_at.replace('Z', '+00:00'))

    # Mapeo de estados (incluyendo 'done' de post_call_transcription)
    status_mapping = {
        'completed': 'completed',
        'failed': 'failed',
        'interrupted': 'interrupted',
        'in_progress': 'in_progress',
        'done': 'completed',
    }
    status = status_mapping.get(status, 'completed')

    # Crear o actualizar la llamada
    call, created = Call.objects.update_or_create(
        call_id=call_id,
        defaults={
            'agent': agent,
            'duration_seconds': duration_seconds,
            'status': status,
            'started_at': started_at or timezone.now(),
            'ended_at': ended_at,
            'call_data': payload,
        }
    )

    print(f"Call {call_id} {'created' if created else 'updated'} for agent {agent.name}")
    return {"success": True, "call_id": call_id}