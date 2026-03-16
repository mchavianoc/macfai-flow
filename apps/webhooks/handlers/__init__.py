import importlib
import pkgutil
import logging
from ..models import WebhookEntry

logger = logging.getLogger(__name__)

_handlers = {}

# Descubrir todos los módulos en el paquete handlers
package = __name__
for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name.startswith('_'):
        continue
    try:
        module = importlib.import_module(f'.{module_name}', package=package)
        if hasattr(module, 'handle'):
            _handlers[module_name] = module.handle
            logger.info(f"Handler cargado para endpoint '{module_name}'")
    except Exception as e:
        logger.error(f"Error cargando handler {module_name}: {e}")

def get_handler(endpoint):
    """Retorna la función handle para el endpoint dado."""
    return _handlers.get(endpoint)

def run_handler(entry_id):
    """
    Ejecuta el handler correspondiente a una entrada de webhook.
    Esta función se llama de forma asíncrona.
    """
    try:
        entry = WebhookEntry.objects.get(id=entry_id)
    except WebhookEntry.DoesNotExist:
        logger.error(f"WebhookEntry {entry_id} no encontrado")
        return

    handler = get_handler(entry.endpoint)
    if handler:
        try:
            result = handler(entry)
            entry.processed = True
            entry.processing_result = result
        except Exception as e:
            logger.exception(f"Error en handler para {entry.endpoint}: {e}")
            entry.processing_result = {"error": str(e)}
        finally:
            entry.save(update_fields=['processed', 'processing_result'])
    else:
        # No hay handler específico, marcamos como procesado sin resultado
        entry.processed = True
        entry.save(update_fields=['processed'])