from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from maintenance.models import MaintenanceTicket

def is_technician(user):
    return user.is_authenticated and user.role == 'technician'

def technician_login(request):
    """
    Vue de connexion dédiée aux techniciens.
    """
    if request.user.is_authenticated:
        if request.user.is_technician:
            return redirect('technician_dashboard')
        return redirect('dashboard') # Redirige vers le dashboard manager si ce n'est pas un tech

    if request.method == 'POST':
        # Logique de connexion (on garde simple pour le moment, mais on valide l'auth)
        # En production, on utiliserait le système d'auth standard de Django
        # Mais ici on veut un écran spécifique.
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.role == 'technician':
                login(request, user)
                return redirect('technician_dashboard')
            else:
                messages.error(request, "Accès réservé au personnel technique.")
        else:
            messages.error(request, "Identifiants incorrects.")
    
    return render(request, 'technician/login.html', {
        'page_title': 'Connexion Technicien'
    })

@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    """
    Dashboard principal du technicien (Liste des interventions).
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    # Récupération des tickets pour le technicien connecté
    # Note: On accède via technician_profile car c'est un OneToOneField sur CustomUser
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('login')

    tickets_today = MaintenanceTicket.objects.filter(
        technician=tech_profile,
        planned_start__gte=today_start,
        planned_start__lt=today_end
    ).order_by('planned_start')

    tickets_week = MaintenanceTicket.objects.filter(
        technician=tech_profile,
        planned_start__gte=today_start,
        planned_start__lt=week_end
    ).order_by('planned_start')

    context = {
        'page_title': 'Mon Planning',
        'tickets_today': tickets_today,
        'tickets_week': tickets_week,
        'now': now,
    }
    return render(request, 'technician/dashboard.html', context)

def technician_logout(request):
    logout(request)
    return redirect('technician_login')
