"""
Fichier : registry.py
Projet : SMARTOPS (Core Application)
Module : plugins_system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Gestionnaire central des plugins. Initialise Pluggy et 
              découvre les modules installés.
"""

import pluggy
import logging
from .hookspecs import SmartOpsHookSpecs

logger = logging.getLogger(__name__)

def get_plugin_manager():
    """
    Initialise et retourne l'instance unique du PluginManager.
    """
    pm = pluggy.PluginManager("smartops")
    pm.add_hookspecs(SmartOpsHookSpecs)
    
    # Découverte automatique des plugins via entry_points [smartops.plugins]
    # C'est ce qui permet l'installation "à chaud" via pip.
    try:
        pm.load_setuptools_entrypoints("smartops.plugins")
        # logger.info("Plugins SMARTOPS chargés avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors du chargement des plugins : {e}")
        
    return pm

# Instance globale pour un accès simplifié dans tout le projet Django
plugin_manager = get_plugin_manager()
