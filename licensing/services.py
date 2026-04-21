"""
Fichier : services.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.1
Description : Service de gestion des licences avec Hardware Binding (UUID).
              Communique avec la Marketplace SMARTOPS_PORTAL.
"""

import logging
import requests
from django.db import models
from django.conf import settings
from .models import Plugin
from system.models import SystemConfiguration

logger = logging.getLogger(__name__)

class LicenseService:
    """
    Service pour la validation des clés et l'activation des plugins.
    Intègre l'Identifiant Unique d'Installation (UUID) pour la sécurité.
    """

    @staticmethod
    def validate_key_with_portal(key):
        """
        Appelle la Marketplace pour valider la clé de licence.
        Envoie également l'installation_uuid pour le Hardware Binding.
        """
        # Récupération de l'identité unique de cette machine
        sys_config = SystemConfiguration.get_instance()
        installation_uuid = str(sys_config.installation_uuid)
        
        marketplace_url = getattr(settings, 'MARKETPLACE_URL', 'http://127.0.0.1:8002')
        api_endpoint = f"{marketplace_url}/api/licensing/validate/"
        
        payload = {
            "license_key": key,
            "installation_uuid": installation_uuid
        }
        
        logger.info(f"Validation de la licence {key} (Installation: {installation_uuid})...")
        
        try:
            response = requests.post(
                api_endpoint, 
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                return {"success": False, "error": "Cette licence est déjà activée sur une autre machine ou est invalide."}
            else:
                return {"success": False, "error": f"Erreur Marketplace ({response.status_code})"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion Marketplace : {e}")
            return {"success": False, "error": "La Marketplace est injoignable."}

    @classmethod
    def sync_with_portal(cls):
        """
        Synchronise l'installation avec le Portail (Télémétrie + Updates).
        Permet de déclarer la machine et de vérifier les mises à jour des modules.
        """
        sys_config = SystemConfiguration.get_instance()
        installation_uuid = str(sys_config.installation_uuid)
        
        # Récupération des versions locales
        installed_modules = [
            {"slug": p.slug, "version": p.version} 
            for p in Plugin.objects.filter(is_active=True)
        ]
        
        marketplace_url = getattr(settings, 'MARKETPLACE_URL', 'http://127.0.0.1:8002')
        api_endpoint = f"{marketplace_url}/api/licensing/sync/"
        
        payload = {
            "installation_uuid": installation_uuid,
            "company_name": sys_config.company_name,
            "core_version": "1.0.0", # À dynamiser plus tard
            "installed_modules": installed_modules
        }
        
        try:
            response = requests.post(api_endpoint, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # Mise à jour de la date de synchro locale
                sys_config.last_sync_portal = models.functions.Now() # Django shortcut
                sys_config.save()
                return data
            else:
                return {"success": False, "error": f"Erreur Portail ({response.status_code})"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": "Le Portail est injoignable."}

    @classmethod
    def activate_plugin(cls, key):
        """
        Processus complet : Validation -> Téléchargement -> Installation physique.
        Utilise l'UUID d'installation pour le Hardware Binding.
        """
        # 1. Validation auprès du portail (Envoie Key + UUID)
        validation_data = cls.validate_key_with_portal(key)
        
        if not validation_data.get('success'):
            return validation_data

        plugin_slug = validation_data['plugin_slug']
        
        # 2. Contrôle local : Déjà installé ?
        if Plugin.objects.filter(slug=plugin_slug, is_active=True).exists():
            return {"success": False, "error": f"Le module '{plugin_slug}' est déjà installé et actif."}

        # 3. Enregistrement / Mise à jour en base locale (Prépare l'injection dans settings)
        plugin, created = Plugin.objects.get_or_create(slug=plugin_slug)
        plugin.name = validation_data['plugin_name']
        plugin.version = validation_data['version']
        plugin.python_path = validation_data.get('package_name', plugin_slug.replace('-', '_'))
        plugin.license_key = key # UUID en clair
        plugin.is_active = True
        plugin.save()

        # 4. Installation physique (Hot-Plug via pip + migrate)
        from .installer import PluginInstaller
        success, message = PluginInstaller.install(
            plugin.python_path, 
            validation_data['download_url']
        )
        
        if not success:
            # En cas d'échec physique, on désactive le module en base pour rester cohérent
            plugin.is_active = False
            plugin.save()
            return {"success": False, "error": message}
        
        return {
            "success": True,
            "message": f"Module '{plugin.name}' activé et installé ! Veuillez redémarrer le serveur.",
            "plugin": plugin
        }
