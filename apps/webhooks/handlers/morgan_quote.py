import logging
from ..models import WebhookEntry

logger = logging.getLogger(__name__)

def handle(entry: WebhookEntry):
    """
    Procesa un webhook de cotización.
    Actualmente solo almacena el payload en la base de datos (ya está en WebhookEntry).
    Deja una función placeholder para futuras acciones.
    """
    logger.info(f"Procesando cotización {entry.id}")

    # Aquí puedes agregar lógica personalizada en el futuro.
    # Por ahora, solo se registra la recepción.
    # El payload ya está guardado en entry.payload (JSONField).

    # Llama a la función placeholder donde pondrás la lógica futura
    resultado_placeholder = procesar_cotizacion(entry)

    return {
        "status": "success",
        "message": "Webhook recibido y almacenado",
        "placeholder_result": resultado_placeholder
    }

def procesar_cotizacion(entry: WebhookEntry):
    """
    Función placeholder para acciones futuras.
    Aquí puedes implementar la lógica de negocio cuando esté lista.
    """
    # Por ahora, solo devuelve un mensaje indicando que no se ha implementado.
    # En el futuro, puedes extraer datos del payload y realizar acciones.
    return {"implementado": False, "mensaje": "Lógica pendiente de implementar"}