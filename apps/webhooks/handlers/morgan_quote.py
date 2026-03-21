import logging
from django.utils import timezone
from ..models import WebhookEntry

logger = logging.getLogger(__name__)

def handle(entry: WebhookEntry):
    """
    Procesa un webhook de cotización.
    Extrae los datos del payload y los almacena en un modelo específico (si existe).
    """
    logger.info(f"Procesando cotización {entry.id}")
    payload = entry.payload

    # Extraer campos típicos de una cotización (ajusta según el JSON real de ElevenLabs)
    quote_id = payload.get('quote_id')
    amount = payload.get('amount')
    currency = payload.get('currency', 'USD')
    status = payload.get('status', 'pending')
    agent_id = payload.get('agent_id') or payload.get('agentId')

    # Asociar agente si no se hizo en la vista
    agent = entry.agent
    if not agent and agent_id:
        try:
            from agents.models import Agent
            agent = Agent.objects.get(agent_id=agent_id)
            entry.agent = agent
            entry.user = agent.user
            entry.save(update_fields=['agent', 'user'])
        except Agent.DoesNotExist:
            logger.warning(f"Agente con ID {agent_id} no encontrado")

    return {
        "status": "success",
        "quote_id": quote_id,
        "amount": amount,
        "currency": currency,
        "message": "Cotización procesada correctamente"
    }