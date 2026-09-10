"""
Fichier : context_processors.py
Projet : SMARTOPS (Core Application)
Module : plugins_system
Auteur : Mohamed Ouedarbi
Version : 1.1
Description : Injecte dynamiquement les menus des plugins dans toutes les pages.
              La base de données (table licensing_plugin) est la source de vérité :
              un module désinstallé disparaît du menu au rafraîchissement suivant,
              sans attendre le redémarrage des workers.
"""

import logging

from .registry import plugin_manager

logger = logging.getLogger(__name__)


def plugin_menus(request):
    """
    Récupère les items de menu via le hook register_menu_items de Pluggy,
    mais uniquement si au moins un module est réellement actif en base.

    Cela évite d'afficher des entrées de menu « fantômes » lorsqu'un module
    a été désinstallé alors que les workers gunicorn tournent encore avec
    l'ancienne instance de plugin_manager en mémoire.
    """
    try:
        from licensing.models import Plugin
        has_active_plugin = Plugin.objects.filter(is_active=True).exists()
    except Exception as exc:  # base non migrée, table absente, etc.
        logger.debug("plugin_menus: vérification des modules actifs impossible (%s)", exc)
        return {'plugin_menus': []}

    if not has_active_plugin:
        return {'plugin_menus': []}

    dynamic_menus = []
    try:
        results = plugin_manager.hook.register_menu_items()
        for plugin_result in results:
            if plugin_result:
                dynamic_menus.extend(plugin_result)
    except Exception as exc:
        logger.error("plugin_menus: échec de la collecte des menus de plugins (%s)", exc)
        return {'plugin_menus': []}

    return {'plugin_menus': dynamic_menus}
