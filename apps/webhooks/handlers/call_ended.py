import logging
from django.utils import timezone
from calls.models import Call
from agents.models import Agent

logger = logging.getLogger(__name__)

def handle(entry):
    """
    Process call_ended webhook from ElevenLabs.
    """
    logger.info(f"Processing call_ended webhook {entry.id}")
    payload = entry.payload

    call_id = payload.get('call_id')
    duration_seconds = payload.get('duration_seconds', 0)
    status = payload.get('status', 'completed')
    started_at = payload.get('started_at')
    ended_at = payload.get('ended_at')
    agent_id_from_payload = payload.get('agent_id') or payload.get('agentId') or payload.get('conversation_agent_id')
    # Buscar también dentro de 'data'
    if not agent_id_from_payload and isinstance(payload.get('data'), dict):
        data = payload['data']
        agent_id_from_payload = data.get('agent_id') or data.get('agentId') or data.get('conversation_agent_id')

    # Use agent already associated or try to find by ID
    agent = entry.agent
    if not agent and agent_id_from_payload:
        try:
            agent = Agent.objects.get(agent_id=agent_id_from_payload)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
        except Agent.DoesNotExist:
            logger.warning(f"Agent with ID {agent_id_from_payload} not found")
            return {"error": "Agent not found"}

    if not agent:
        logger.warning("No agent associated")
        return {"error": "No agent associated"}

    # Convert timestamps if they are strings
    if started_at and isinstance(started_at, str):
        started_at = timezone.datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if ended_at and isinstance(ended_at, str):
        ended_at = timezone.datetime.fromisoformat(ended_at.replace('Z', '+00:00'))

    # Map status if needed
    status_mapping = {
        'completed': 'completed',
        'failed': 'failed',
        'interrupted': 'interrupted',
        'in_progress': 'in_progress',
    }
    status = status_mapping.get(status, 'completed')

    # Create or update call record
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

    logger.info(f"Call {call_id} {'created' if created else 'updated'} for agent {agent.name}")
    return {"success": True, "call_id": call_id}