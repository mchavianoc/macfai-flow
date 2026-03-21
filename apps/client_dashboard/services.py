# client_dashboard/services.py (nueva versión)

from django.utils import timezone
from django.db.models import Sum, Count
from calls.models import Call

def get_user_monthly_consumption(user):
    """
    Calcula el consumo total de minutos del usuario a partir de las llamadas
    registradas en la base de datos local.
    Retorna un dict con total_seconds, total_minutes, total_calls y percentage_used.
    """
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = Call.objects.filter(
        agent__user=user,
        started_at__gte=month_start,
        status='completed'
    ).aggregate(
        total_seconds=Sum('duration_seconds'),
        total_calls=Count('id')
    )

    total_seconds = result['total_seconds'] or 0
    total_minutes = (total_seconds + 59) // 60  # redondeo hacia arriba

    # Calcular porcentaje consumido respecto al límite mensual del usuario
    percentage_used = None
    if user.monthly_minutes_limit and user.monthly_minutes_limit > 0:
        percentage_used = (total_minutes / user.monthly_minutes_limit) * 100

    return {
        'total_seconds': total_seconds,
        'total_minutes': total_minutes,
        'total_calls': result['total_calls'] or 0,
        'percentage_used': percentage_used,
        'errors': None   # se mantiene por compatibilidad, pero ya no se usa
    }