"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Modèle de configuration centrale de l'application SMARTOPS. 
              Gère l'identité unique de l'installation (UUID) et les données 
              de l'entreprise pour les rapports et factures.
"""

from django.db import models
import uuid
import os

class SystemConfiguration(models.Model):
    """
    Modèle de configuration système (Singleton).
    Contient l'identité unique de l'instance SMARTOPS chez le client.
    """
    # Identité Technique
    installation_uuid = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False,
        verbose_name="ID Unique d'Installation"
    )
    installed_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'Installation")
    last_sync_portal = models.DateTimeField(null=True, blank=True, verbose_name="Dernière Synchro Portail")
    
    # Informations Entreprise (Pour les rapports)
    company_name = models.CharField(max_length=255, verbose_name="Nom de la Société")
    company_address = models.TextField(verbose_name="Adresse du Siège")
    company_phone = models.CharField(max_length=50, blank=True, verbose_name="Téléphone")
    company_email = models.EmailField(blank=True, verbose_name="Email de Contact")
    company_website = models.URLField(blank=True, verbose_name="Site Web")
    company_vat = models.CharField(max_length=50, blank=True, verbose_name="Numéro de TVA")
    company_logo = models.ImageField(upload_to='system/logos/', blank=True, null=True, verbose_name="Logo Entreprise")

    class Meta:
        verbose_name = "Configuration Système"
        verbose_name_plural = "Configuration Système"

    def __str__(self):
        return f"Configuration SMARTOPS - {self.company_name or 'Nouvelle Instance'}"

    def save(self, *args, **kwargs):
        """
        Garantit que l'on ne peut avoir qu'une seule instance de configuration.
        """
        if not self.pk and SystemConfiguration.objects.exists():
            # Dans un cas réel, on pourrait lever une exception ou simplement 
            # mettre à jour l'instance existante.
            return 
        super(SystemConfiguration, self).save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """
        Méthode utilitaire pour récupérer la configuration active.
        """
        obj, created = cls.objects.get_or_create(
            id=1,
            defaults={'company_name': 'Nouvelle Installation SMARTOPS'}
        )
        return obj
