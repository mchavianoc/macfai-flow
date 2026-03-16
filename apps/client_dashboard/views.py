# client_dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from agents.models import Agent
from calls.models import Call
from .services import get_user_monthly_consumption

@login_required
def dashboard(request):
    user = request.user
    consumption = get_user_monthly_consumption(user)
    agents = Agent.objects.filter(user=user, is_active=True)
    recent_calls = Call.objects.filter(
        agent__user=user
    ).select_related('agent').order_by('-started_at')[:10]

    context = {
        'user': user,
        'agents': agents,
        'recent_calls': recent_calls,
        'consumption': consumption,
        'limit_warning': consumption.get('percentage_used', 0) >= 80 
            if consumption.get('percentage_used') else False,
    }

    return render(request, 'dashboard.html', context)