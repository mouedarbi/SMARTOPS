"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour l'activation des modules et la synchronisation avec le Portail.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .services import LicenseService
from .models import Plugin

@login_required
def plugin_list_view(request):
    """
    Affiche la liste des modules premium et gère le formulaire d'activation.
    """
    if request.method == 'POST':
        license_key = request.POST.get('license_key')
        if license_key:
            # Appel au service d'activation (Validation + Binding)
            result = LicenseService.activate_plugin(license_key)
            
            if result.get('success'):
                messages.success(request, result.get('message'))
            else:
                messages.error(request, result.get('error', "Une erreur est survenue lors de l'activation."))
        else:
            messages.warning(request, "Veuillez saisir une clé de licence.")
        
        return redirect('plugin_list')

    # Récupération des modules déjà installés
    plugins = Plugin.objects.all().order_by('-installed_at')
    
    context = {
        'plugins': plugins,
        'page_title': "Gestion des Modules Premium"
    }
    return render(request, 'licensing/plugin_list.html', context)

@login_required
def sync_portal_view(request):
    """
    Déclenche la synchronisation manuelle avec le Portail SMARTOPS.
    """
    result = LicenseService.sync_with_portal()
    
    if result.get('success'):
        if result.get('updates_available'):
            messages.warning(request, f"Synchronisation réussie. {len(result['module_updates'])} mise(s) à jour de modules disponible(s) !")
        else:
            messages.success(request, "Votre système est à jour. Synchronisation réussie.")
    else:
        messages.error(request, f"Échec de la synchronisation : {result.get('error')}")
        
    return redirect('dashboard')
