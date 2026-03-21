import logging
from django.utils import timezone
from calls.models import Call
from agents.models import Agent

logger = logging.getLogger(__name__)

def handle(entry):
    """
    Procesa el webhook de finalización de llamada enviado por ElevenLabs.
    """
    logger.info(f"Procesando call_ended webhook {entry.id}")
    payload = entry.payload

    # Extraer campos del payload (ajustar según la documentación de ElevenLabs)
    call_id = payload.get('call_id')
    duration_seconds = payload.get('duration_seconds', 0)
    status = payload.get('status', 'completed')
    started_at = payload.get('started_at')
    ended_at = payload.get('ended_at')

    # Obtener el agent_id del payload (nombre del campo puede variar)
    agent_id_from_payload = payload.get('agent_id') or payload.get('agentId') or payload.get('conversation_agent_id')
    
    # Si no viene en el payload, intentar usar el asociado por query param (por si acaso)
    agent = entry.agent
    if not agent and agent_id_from_payload:
        try:
            agent = Agent.objects.get(agent_id=agent_id_from_payload)
            # Actualizar la entrada con el agente encontrado
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
        except Agent.DoesNotExist:
            logger.warning(f"Agente con ID {agent_id_from_payload} no encontrado")
            return {"error": "Agent not found"}
    
    if not agent:
        logger.warning("No se pudo identificar el agente")
        return {"error": "No agent associated"}

    # Convertir timestamps a datetime si vienen como strings ISO
    if started_at and isinstance(started_at, str):
        started_at = timezone.datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if ended_at and isinstance(ended_at, str):
        ended_at = timezone.datetime.fromisoformat(ended_at.replace('Z', '+00:00'))

    # Mapeo de estados (ajustar según los valores que envía ElevenLabs)
    status_mapping = {
        'completed': 'completed',
        'failed': 'failed',
        'interrupted': 'interrupted',
        'in_progress': 'in_progress',
    }
    status = status_mapping.get(status, 'completed')

    # Crear o actualizar el registro de llamada
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

    logger.info(f"Llamada {call_id} {'creada' if created else 'actualizada'} para agente {agent.name}")
    return {"success": True, "call_id": call_id}