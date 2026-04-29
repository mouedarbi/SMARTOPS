"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.1
Description : Vues pour l'activation des modules et la synchronisation avec le Portail.
"""

import json
import requests
import subprocess
import sys
import tempfile
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import StreamingHttpResponse
from django.core.management import call_command

from .services import LicenseService
from .models import Plugin
from system.models import SystemConfiguration

@login_required
def plugin_list_view(request):
    """
    Affiche la liste des modules premium et gère le formulaire d'activation.
    """
    if request.method == 'POST':
        license_key = request.POST.get('license_key')
        if license_key:
            result = LicenseService.activate_plugin(license_key)
            if result.get('success'):
                messages.success(request, result.get('message'))
            else:
                messages.error(request, result.get('error', "Une erreur est survenue lors de l'activation."))
        else:
            messages.warning(request, "Veuillez saisir une clé de licence.")
        return redirect('plugin_list')

    plugins = Plugin.objects.all().order_by('-installed_at')
    context = {
        'plugins': plugins,
        'page_title': "Gestion des Modules Premium"
    }
    return render(request, 'licensing/plugin_list.html', context)

@login_required
def plugin_install_stream_view(request):
    """
    Vue de streaming qui exécute l'installation et renvoie les logs en live.
    """
    license_key = request.GET.get('license_key')
    if not license_key:
        return StreamingHttpResponse("Erreur : Clé de licence manquante.")

    def stream_installation():
        yield ">>> INITIALISATION DE L'INSTALLATION SECURISEE...\n"
        
        # 1. Validation
        yield ">>> Validation de la licence auprès du Portail SMARTOPS...\n"
        validation_data = LicenseService.validate_key_with_portal(license_key)
        
        if not validation_data.get('success'):
            yield f"!!! ERREUR VALIDATION : {validation_data.get('error')}\n"
            return

        plugin_slug = validation_data['plugin_slug']
        yield f">>> Licence validée pour : {validation_data['plugin_name']} (v{validation_data['version']})\n"

        # 2. Préparation base de données locale
        yield ">>> Mise à jour du registre local des modules...\n"
        plugin, created = Plugin.objects.get_or_create(slug=plugin_slug)
        plugin.name = validation_data['plugin_name']
        plugin.version = validation_data['version']
        plugin.python_path = validation_data.get('package_name', plugin_slug.replace('-', '_'))
        plugin.license_key = license_key
        plugin.is_active = True
        plugin.save()

        # 3. Installation physique
        yield f">>> Téléchargement et installation de {plugin.python_path} via PIP...\n"
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                package_file = os.path.join(temp_dir, "package.tar.gz")
                resp = requests.get(validation_data['download_url'], stream=True)
                with open(package_file, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                process = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", "--upgrade", package_file],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                )
                for line in process.stdout:
                    yield f"    {line}"
                process.wait()
                
                if process.returncode != 0:
                    yield f"!!! ERREUR PIP (Code {process.returncode})\n"
                    plugin.is_active = False
                    plugin.save()
                    return

            # 4. Migrations
            yield ">>> Lancement des migrations de base de données...\n"
            call_command('migrate', interactive=False)
            yield "\n🎉 MODULE ACTIVÉ ET INSTALLÉ AVEC SUCCÈS !\n"
            yield ">>> IMPORTANT : Veuillez REDÉMARRER le serveur Django pour charger le nouveau module.\n"
            yield ">>> (Appuyez sur Ctrl+C dans votre terminal puis relancez runserver)\n"

        except Exception as e:
            yield f"!!! ERREUR FATALE : {str(e)}\n"
            plugin.is_active = False
            plugin.save()

    return StreamingHttpResponse(stream_installation(), content_type='text/plain')

@login_required
def plugin_uninstall_stream_view(request):
    """
    Vue de streaming pour la désinstallation physique d'un module.
    """
    slug = request.GET.get('slug')
    plugin = get_object_or_404(Plugin, slug=slug)
    
    def stream_uninstallation():
        yield f">>> DESINSTALLATION DU MODULE : {plugin.name}...\n"
        
        # 1. Libération de la licence sur le Portail
        yield ">>> Communication avec le Portail pour libérer la licence...\n"
        sys_config = SystemConfiguration.get_instance()
        marketplace_url = settings.MARKETPLACE_URL
        
        try:
            resp = requests.post(f"{marketplace_url}/api/licensing/release/", json={
                "installation_uuid": str(sys_config.installation_uuid),
                "license_key": plugin.license_key
            }, timeout=10)
            
            if resp.status_code == 200:
                yield ">>> Licence libérée sur le Portail avec succès.\n"
            else:
                yield f">>> [Avertissement] Le Portail a refusé la libération ({resp.status_code}).\n"
        except Exception as e:
            yield f">>> [Erreur] Échec de connexion : {str(e)}\n"

        # 2. Désactivation et Suppression PIP
        yield ">>> Désactivation dans le registre local...\n"
        package_name = plugin.python_path or plugin.slug.replace('-', '_')
        
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                yield f"    {line}"
            process.wait()
            
            yield ">>> Nettoyage de la base de données...\n"
            plugin.delete()
            yield "\n✅ MODULE DESINSTALLE AVEC SUCCÈS !\n"
            yield ">>> La licence a été libérée sur le Portail.\n"
            yield ">>> IMPORTANT : Veuillez REDÉMARRER le serveur pour finaliser le retrait du menu.\n"

        except Exception as e:
            yield f"!!! ERREUR LORS DE LA SUPPRESSION : {str(e)}\n"

    return StreamingHttpResponse(stream_uninstallation(), content_type='text/plain')

@login_required
def api_check_sync(request):
    """
    API interne appelée par le dashboard pour synchroniser en arrière-plan.
    Gère un throttle de 24h pour éviter de surcharger le portail.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    config = SystemConfiguration.get_instance()
    force = request.GET.get('force') == 'true'
    
    # Si la dernière synchro date de moins de 24h, on ignore (sauf si force=true)
    if not force and config.last_sync_portal:
        if timezone.now() < config.last_sync_portal + timedelta(hours=24):
            return JsonResponse({
                "success": True, 
                "message": "Synchro récente, sautée.",
                "already_synced": True
            })
    
    result = LicenseService.sync_with_portal()
    return JsonResponse(result)

@login_required
def sync_portal_view(request):
    """
    Déclenche la synchronisation manuelle avec le Portail SMARTOPS.
    """
    result = LicenseService.sync_with_portal()
    if result.get('success'):
        if result.get('updates_available'):
            messages.warning(request, f"Synchronisation réussie. {len(result['module_updates'])} mise(s) à jour disponible(s) !")
        else:
            messages.success(request, "Votre système est à jour.")
    else:
        messages.error(request, f"Échec de la synchronisation : {result.get('error')}")
    return redirect('dashboard')
