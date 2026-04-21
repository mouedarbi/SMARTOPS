"""
Fichier : hookspecs.py
Projet : SMARTOPS (Core Application)
Module : plugins_system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Spécifications des points d'entrée (hooks) pour les plugins SMARTOPS.
"""

import pluggy

hookspec = pluggy.HookspecMarker("smartops")

class SmartOpsHookSpecs:
    """
    Définition des hooks disponibles pour étendre SMARTOPS.
    """
    
    @hookspec
    def register_dashboard_widgets(self):
        """
        Permet aux plugins d'ajouter des widgets visuels au dashboard.
        Doit retourner une liste de dictionnaires.
        """
        pass

    @hookspec
    def register_menu_items(self):
        """
        Permet aux plugins d'ajouter des liens dans la barre latérale.
        Doit retourner une liste de dictionnaires (label, url, icon).
        """
        pass

    @hookspec
    def process_intervention_data(self, intervention):
        """
        Hook pour modifier ou enrichir les données d'une intervention.
        """
        pass
