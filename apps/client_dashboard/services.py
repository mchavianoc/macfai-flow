# apps/client_dashboard/services.py
import requests
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings

def get_agent_monthly_consumption(agent_id):
    """
    Consulta a la API de ElevenLabs el consumo de minutos del mes actual
    para un agente específico.
    Retorna un dict con total_seconds, total_minutes y total_calls.
    """
    api_key = settings.ELEVENLABS_API_KEY
    if not api_key:
        return {
            'error': 'API key de ElevenLabs no configurada.',
            'total_seconds': 0,
            'total_minutes': 0,
            'total_calls': 0
        }

    # Calcular fechas de inicio y fin del mes actual
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Convertir a formato ISO 8601 que espera ElevenLabs
    start_date = start_of_month.isoformat().replace('+00:00', 'Z')
    end_date = now.isoformat().replace('+00:00', 'Z')

    # Endpoint de conversaciones de ElevenLabs
    url = "https://api.elevenlabs.io/v1/convai/conversations"

    headers = {
        "xi-api-key": api_key
    }

    params = {
        "agent_id": agent_id,
        "start_date": start_date,
        "end_date": end_date,
        "page_size": 100  # Ajusta según necesites, pueden venir muchas
    }

    total_seconds = 0
    total_calls = 0
    next_cursor = None

    try:
        while True:
            if next_cursor:
                params['cursor'] = next_cursor
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            conversations = data.get('conversations', [])
            for conv in conversations:
                # Solo considerar conversaciones completadas
                if conv.get('status') == 'completed':
                    start_time = conv.get('start_time')
                    end_time = conv.get('end_time')
                    if start_time and end_time:
                        # Convertir a datetime (asumiendo formato ISO)
                        try:
                            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            duration = (end - start).total_seconds()
                            total_seconds += duration
                            total_calls += 1
                        except (ValueError, TypeError):
                            # Si hay error en formato, ignoramos esta conversación
                            pass

            next_cursor = data.get('next_cursor')
            if not next_cursor:
                break

    except requests.exceptions.RequestException as e:
        return {
            'error': f'Error al consultar ElevenLabs: {str(e)}',
            'total_seconds': 0,
            'total_minutes': 0,
            'total_calls': 0
        }

    total_minutes = int(total_seconds // 60)  # minutos enteros

    return {
        'total_seconds': total_seconds,
        'total_minutes': total_minutes,
        'total_calls': total_calls,
        'error': None
    }

def get_user_monthly_consumption(user):
    """
    Calcula el consumo total de todos los agentes activos de un usuario.
    """
    agents = user.agents.filter(is_active=True)
    total_seconds = 0
    total_calls = 0
    errors = []

    for agent in agents:
        consumption = get_agent_monthly_consumption(agent.agent_id)
        if consumption.get('error'):
            errors.append(f"Agente {agent.name}: {consumption['error']}")
        else:
            total_seconds += consumption['total_seconds']
            total_calls += consumption['total_calls']

    total_minutes = int(total_seconds // 60)

    # Calcular porcentaje respecto al límite del usuario (si existe)
    percentage_used = None
    if user.monthly_minutes_limit and user.monthly_minutes_limit > 0:
        percentage_used = (total_minutes / user.monthly_minutes_limit) * 100

    return {
        'total_seconds': total_seconds,
        'total_minutes': total_minutes,
        'total_calls': total_calls,
        'percentage_used': percentage_used,
        'errors': errors if errors else None
    }