# apps/webhooks/handlers/call_ended.py

def handle(entry):
    """
    Process call_ended webhook from ElevenLabs.
    Also supports post_call_transcription events where data is inside 'data'.
    """
    logger.info(f"Processing call_ended webhook {entry.id}")
    payload = entry.payload

    # Helper to get a field from payload, falling back to data
    def get_field(key, default=None):
        # Check root
        value = payload.get(key)
        if value is not None:
            return value
        # Check inside data
        data = payload.get('data', {})
        return data.get(key, default)

    # Extract fields with fallback
    call_id = get_field('call_id')
    duration_seconds = get_field('duration_seconds', 0)
    status = get_field('status', 'completed')
    started_at = get_field('started_at')
    ended_at = get_field('ended_at')
    agent_id_from_payload = get_field('agent_id') or get_field('agentId') or get_field('conversation_agent_id')

    if not call_id:
        logger.error(f"No call_id found in payload for entry {entry.id}")
        return {"error": "call_id missing"}

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
        'done': 'completed',          # 'done' appears in post_call_transcription
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