"""
Fichier : urls_loader.py
Projet : SMARTOPS (Core Application)
Module : plugins_system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Montage des pages des modules installés (« Hot-Plug »). Le chargement de chaque module
              est isolé : une erreur dans un module est journalisée et ce module est ignoré, sans
              empêcher le Core ni les autres modules de fonctionner.
"""

import importlib
import importlib.util
import logging

from django.urls import include, path

logger = logging.getLogger(__name__)

# Applications du Core, jamais traitées comme des modules.
EXCLUDED_APPS = ('system', 'licensing', 'smartops_project')
PLUGIN_PREFIX = 'smartops_'


def is_mountable(app_name):
    """Indique si l'application est un module dont on doit monter les pages."""
    return app_name not in EXCLUDED_APPS and app_name.startswith(PLUGIN_PREFIX)


def build_plugin_urlpatterns(app_names):
    """
    Retourne les routes `app/<module>/` des modules qui exposent un `urls.py`.

    Un module dont le chargement échoue (erreur de syntaxe, import manquant...) est ignoré :
    l'erreur est écrite dans les journaux et les autres modules restent montés.
    """
    patterns = []
    for app_name in app_names:
        if not is_mountable(app_name):
            continue

        urls_module = f"{app_name}.urls"
        try:
            # Un module sans urls.py n'expose simplement aucune page.
            if importlib.util.find_spec(urls_module) is None:
                continue
            # Import explicite : c'est ici qu'une erreur du module est interceptée.
            importlib.import_module(urls_module)
            patterns.append(path(f'app/{app_name}/', include(urls_module)))
        except Exception:
            logger.exception("Module « %s » ignoré : ses pages n'ont pas pu être chargées.", app_name)
    return patterns
