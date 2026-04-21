"""
Fichier : admin.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Configuration de l'interface d'administration pour les paramètres système.
"""

from django.contrib import admin
from .models import SystemConfiguration

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour la configuration unique.
    L'UUID est affiché en lecture seule.
    """
    list_display = ('company_name', 'installation_uuid', 'installed_at')
    readonly_fields = ('installation_uuid', 'installed_at')

    def has_add_permission(self, request):
        """
        Empêche d'ajouter une deuxième configuration.
        """
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """
        Empêche de supprimer la configuration vitale.
        """
        return False
