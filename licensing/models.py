"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Modèle pour la gestion des plugins premium installés. 
              Enregistre les métadonnées et les clés de licence activées.
"""

from django.db import models
import hashlib

class Plugin(models.Model):
    """
    Représente un module premium enregistré et/ou activé localement.
    """
    slug = models.SlugField(
        unique=True, 
        help_text="Identifiant technique unique (ex: smartops-billing)"
    )
    python_path = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Le chemin d'importation Python (ex: smartops_plugin_demo)"
    )
    priority = models.IntegerField(
        default=100, 
        help_text="Ordre de chargement dans INSTALLED_APPS (le plus petit en premier)"
    )
    name = models.CharField(max_length=255, verbose_name="Nom du Plugin")
    version = models.CharField(max_length=50, blank=True, verbose_name="Version Installée")
    license_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Clé de licence (UUID) utilisée pour ce module"
    )
    is_active = models.BooleanField(default=False, verbose_name="Statut d'Activation")
    installed_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'Installation")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière Mise à Jour")

    class Meta:
        verbose_name = "Module Premium"
        verbose_name_plural = "Modules Premium"

    def __str__(self):
        return f"{self.name} ({self.slug}) - {'Actif' if self.is_active else 'Inactif'}"

    @staticmethod
    def hash_key(key):
        """
        Méthode pour hacher la clé avant stockage local par sécurité.
        """
        return hashlib.sha256(key.encode()).hexdigest()
