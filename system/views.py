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
