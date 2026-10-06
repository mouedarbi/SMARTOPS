"""
Fichier : apps.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Configuration de l'application d'inventaire (clients, lieux, équipements).
"""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """Configuration de l'application inventory."""
    name = 'inventory'
