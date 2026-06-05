from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def technician_login(request):
    """
    Vue de connexion dédiée aux techniciens.
    """
    if request.method == 'POST':
        # Logique de connexion simplifiée pour le moment
        return redirect('technician_dashboard')
    
    return render(request, 'technician/login.html', {
        'page_title': 'Connexion Technicien'
    })

def technician_dashboard(request):
    """
    Dashboard principal du technicien (Liste des interventions).
    """
    return render(request, 'technician/dashboard.html', {
        'page_title': 'Mon Planning'
    })
