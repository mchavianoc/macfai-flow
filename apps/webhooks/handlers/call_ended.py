import uuid
from django.utils import timezone
from calls.models import Call
from agents.models import Agent

def handle(entry):
    """
    Process call_ended webhook from ElevenLabs.
    Generates a call_id if not present.
    """
    print(f"Processing call_ended webhook {entry.id}")
    payload = entry.payload

    # Helper para obtener campos desde payload o data
    def get_field(key, default=None):
        value = payload.get(key)
        if value is not None:
            return value
        data = payload.get('data', {})
        return data.get(key, default)

    # Mostrar el contenido de data para depuración
    data = payload.get('data', {})
    print("Data keys:", list(data.keys()))
    print("Full data:", data)

    # Extraer campos
    call_id = get_field('call_id')
    duration_seconds = get_field('duration_seconds', 0)
    status = get_field('status', 'completed')
    started_at = get_field('started_at')
    ended_at = get_field('ended_at')
    agent_id_from_payload = get_field('agent_id') or get_field('agentId') or get_field('conversation_agent_id')

    # Si no hay call_id, generamos uno
    if not call_id:
        # Usamos un UUID + algo de contexto (entry.id) para asegurar unicidad
        call_id = f"webhook_{entry.id}_{uuid.uuid4().hex[:8]}"
        print(f"Generated call_id: {call_id}")

    # Asociar agente
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

    # Mapeo de estados
    status_mapping = {
        'completed': 'completed',
        'failed': 'failed',
        'interrupted': 'interrupted',
        'in_progress': 'in_progress',
        'done': 'completed',
    }
    status = status_mapping.get(status, 'completed')

    # Si no hay started_at, usamos el event_timestamp del payload o el created_at de entrada
    if not started_at:
        event_ts = payload.get('event_timestamp')
        if event_ts:
            started_at = timezone.datetime.fromtimestamp(event_ts, tz=timezone.utc)
        else:
            started_at = entry.created_at

    # Crear o actualizar llamada (usamos update_or_create con call_id generado)
    call, created = Call.objects.update_or_create(
        call_id=call_id,
        defaults={
            'agent': agent,
            'duration_seconds': duration_seconds,
            'status': status,
            'started_at': started_at,
            'ended_at': ended_at,
            'call_data': payload,
        }
    )

    print(f"Call {call_id} {'created' if created else 'updated'} for agent {agent.name}")
    return {"success": True, "call_id": call_id}