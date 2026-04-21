"""
Fichier : context_processors.py
Projet : SMARTOPS (Core Application)
Module : plugins_system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Injecte dynamiquement les menus des plugins dans toutes les pages.
"""

from .registry import plugin_manager

def plugin_menus(request):
    """
    Récupère les items de menu via le hook register_menu_items de Pluggy.
    """
    dynamic_menus = []
    
    # Appel du hook Pluggy
    # Chaque plugin renvoie une liste d'items
    results = plugin_manager.hook.register_menu_items()
    
    # On aplatit la liste de listes en une seule liste
    for plugin_result in results:
        if plugin_result:
            dynamic_menus.extend(plugin_result)
            
    return {
        'plugin_menus': dynamic_menus
    }
