import logging
from ..models import WebhookEntry

logger = logging.getLogger(__name__)

def handle(entry: WebhookEntry):
    """
    Procesa un webhook de cotización.
    Se asume que el payload contiene la información necesaria.
    """
    logger.info(f"Procesando cotización {entry.id}")
    payload = entry.payload
    texto = payload.get('texto', '')

    # Aquí puedes extraer más datos del payload o del agente asociado
    agent = entry.agent
    if agent and agent.user:
        # Ejemplo: enviar SMS al teléfono del usuario
        telefono = agent.user.phone_number  # Asegúrate de que User tenga este campo
        if telefono:
            enviar_sms(telefono, f"Nueva cotización: {texto[:50]}...")
            return {"sms_enviado": True, "destinatario": telefono}
        else:
            return {"sms_enviado": False, "razon": "Usuario sin teléfono"}
    return {"sms_enviado": False, "razon": "Agente no asociado"}

def enviar_sms(destino, mensaje):
    """Función simulada de envío de SMS. Reemplazar con integración real."""
    # from twilio.rest import Client
    # client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
    # client.messages.create(body=mensaje, from_=settings.TWILIO_NUMBER, to=destino)
    logger.info(f"Enviando SMS a {destino}: {mensaje}")
    # En desarrollo, solo imprimimos
    print(f"SMS enviado a {destino}: {mensaje}")