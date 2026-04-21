"""
Fichier : context_processors.py
Projet : SMARTOPS (Core Application)
Module : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Injecte la configuration système globale dans tous les templates.
              Permet d'afficher l'état du Portail et l'UUID sur n'importe quelle page.
"""

from .models import SystemConfiguration

def system_settings(request):
    """
    Retourne l'instance unique de configuration pour qu'elle soit 
    disponible globalement dans le dictionnaire de contexte.
    """
    return {
        'config': SystemConfiguration.get_instance()
    }
