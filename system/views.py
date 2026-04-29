"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour la gestion de la configuration système.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import SystemConfiguration
from .forms import SystemConfigurationForm
from inventory.models import Equipment, Building, Client
from maintenance.models import MaintenanceTicket

@login_required
def dashboard_view(request):
    """
    Vue principale du tableau de bord.
    """
    config = SystemConfiguration.get_instance()
    
    # Si l'installation n'est pas personnalisée, on force la configuration
    if config.company_name == 'Nouvelle Installation SMARTOPS' or not config.company_name:
        messages.info(request, "Bienvenue ! Veuillez personnaliser le nom de votre société pour déverrouiller le système.")
        return redirect('system_config')

    # Statistiques
    stats = {
        'tickets_count': MaintenanceTicket.objects.count(),
        'equipment_count': Equipment.objects.count(),
        'buildings_count': Building.objects.count(),
        'clients_count': Client.objects.count(),
    }

    # Activité récente (10 derniers tickets)
    recent_tickets = MaintenanceTicket.objects.all().order_by('-created_at')[:10]

    context = {
        'config': config,
        'page_title': "Tableau de Bord",
        'stats': stats,
        'recent_tickets': recent_tickets,
    }
    return render(request, 'system/dashboard.html', context)

@login_required
def system_config_view(request):
    """
    Vue unique pour visualiser et modifier la configuration du système.
    Elle assure la récupération de l'unique instance de configuration.
    """
    config = SystemConfiguration.get_instance()
    
    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Les paramètres système ont été mis à jour avec succès.")
            return redirect('system_config')
        else:
            messages.error(request, "Une erreur est survenue lors de la mise à jour.")
    else:
        form = SystemConfigurationForm(instance=config)
        
    context = {
        'config': config, # Nécessaire pour l'UUID dans la sidebar
        'form': form,
        'page_title': "Paramètres du Système"
    }
    return render(request, 'system/config_detail.html', context)
