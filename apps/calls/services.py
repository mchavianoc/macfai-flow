# apps/calls/services.py
from django.utils import timezone
from django.db.models import Sum, Count
from .models import Call  # <-- Importar modelo

def get_user_monthly_consumption(user):
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
    total_minutes = (total_seconds + 59) // 60  # Redondear hacia arriba
    
    # Evitar división por cero si el límite es 0
    limit = user.monthly_minutes_limit
    percentage_used = None
    if limit and limit > 0:
        percentage_used = (total_minutes / limit) * 100
    
    return {
        'total_seconds': total_seconds,
        'total_minutes': total_minutes,
        'total_calls': result['total_calls'] or 0,
        'percentage_used': percentage_used,
    }

def check_minutes_limit(user, additional_seconds=0):
    if not user.monthly_minutes_limit:
        return {'allowed': True, 'reason': 'no_limit'}
    
    consumption = get_user_monthly_consumption(user)
    # Calcular minutos adicionales redondeando hacia arriba
    additional_minutes = (additional_seconds + 59) // 60
    total_minutes = consumption['total_minutes'] + additional_minutes
    
    if total_minutes >= user.monthly_minutes_limit:
        return {
            'allowed': False,
            'reason': 'limit_exceeded',
            'current': consumption['total_minutes'],
            'limit': user.monthly_minutes_limit
        }
    
    return {'allowed': True, 'reason': 'within_limit'}