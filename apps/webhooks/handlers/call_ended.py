import datetime
from calls.models import Call
from agents.models import Agent

def handle(entry):
    """
    Procesa webhook post_call_transcription de ElevenLabs.
    Extrae duración, costo, timestamps, idioma, motivo de terminación, etc.
    """
    print(f"Processing call_ended webhook {entry.id}")
    payload = entry.payload
    data = payload.get('data', {})
    metadata = data.get('metadata', {})
    charging = metadata.get('charging', {})
    
    # Identificador único: usar conversation_id si existe
    conversation_id = data.get('conversation_id')
    if conversation_id:
        call_id = conversation_id
        print(f"Using conversation_id as call_id: {call_id}")
    else:
        # Fallback: generar uno único
        call_id = f"webhook_{entry.id}_{datetime.datetime.utcnow().timestamp()}"
        print(f"Generated call_id: {call_id}")
    
    # Duración (segundos)
    duration_seconds = metadata.get('call_duration_secs', 0)
    print(f"Duration: {duration_seconds} seconds")
    
    # Costo (créditos ElevenLabs)
    cost = charging.get('call_charge', 0)
    print(f"Cost: {cost}")
    
    # Timestamp de inicio
    start_timestamp = metadata.get('start_time_unix_secs')
    if start_timestamp:
        started_at = datetime.datetime.fromtimestamp(start_timestamp, tz=datetime.timezone.utc)
    else:
        event_ts = payload.get('event_timestamp')
        if event_ts:
            started_at = datetime.datetime.fromtimestamp(event_ts, tz=datetime.timezone.utc)
        else:
            started_at = entry.created_at
    print(f"Started at: {started_at}")
    
    # Estado de la llamada
    status = data.get('status', 'completed')
    status_mapping = {
        'completed': 'completed',
        'failed': 'failed',
        'interrupted': 'interrupted',
        'in_progress': 'in_progress',
        'done': 'completed',
    }
    status = status_mapping.get(status, 'completed')
    
    # Motivo de terminación (si está disponible)
    termination_reason = metadata.get('termination_reason', '')
    # Idioma principal
    language = metadata.get('main_language', '')
    
    # Asociar agente
    agent_id_from_payload = data.get('agent_id')
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
    
    # Crear o actualizar la llamada
    call, created = Call.objects.update_or_create(
        call_id=call_id,
        defaults={
            'agent': agent,
            'duration_seconds': duration_seconds,
            'status': status,
            'cost': cost,
            'termination_reason': termination_reason,
            'language': language,
            'started_at': started_at,
            'ended_at': None,  # No se proporciona ended_at en este evento
            'call_data': payload,
        }
    )
    
    print(f"Call {call_id} {'created' if created else 'updated'} for agent {agent.name}")
    print(f"Duration: {duration_seconds}s, Cost: {cost}, Language: {language}, Termination: {termination_reason}")
    return {"success": True, "call_id": call_id}