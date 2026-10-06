"""
Fichier : apps.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Configuration de l'application de maintenance (tickets et interventions).
"""

from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    """Configuration de l'application maintenance."""
    name = 'maintenance'
