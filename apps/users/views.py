from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

@login_required
def dashboard(request):
    # Aquí obtendremos datos relacionados con el usuario (llamadas, agentes, etc.)
    # Por ahora solo pasamos el usuario
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard.html', context)