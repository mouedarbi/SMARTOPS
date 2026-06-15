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
    Toutes les applications du Core doivent appeler ces hooks aux moments clés.
    """
    
    # --- UI & NAVIGATION ---
    
    @hookspec
    def register_menu_items(self):
        """Ajouter des liens dans la barre latérale (Sidebar)."""
        pass

    @hookspec
    def register_dashboard_widgets(self):
        """Ajouter des widgets (stats, graphiques) au dashboard principal."""
        pass

    @hookspec
    def enrich_template_context(self, context, request):
        """Ajouter des variables globales à tous les templates."""
        pass

    # --- INVENTORY (CLIENTS, SITES, EQUIPEMENTS) ---

    @hookspec
    def enrich_client_detail_context(self, client, context):
        """Ajouter des données/onglets à la fiche détaillée d'un client."""
        pass

    @hookspec
    def enrich_equipment_detail_context(self, equipment, context):
        """Ajouter des données/onglets à la fiche d'un équipement."""
        pass

    @hookspec
    def pre_save_equipment(self, equipment, is_new):
        """Logique avant la sauvegarde d'un équipement (validation, calcul)."""
        pass

    # --- MAINTENANCE (TICKETS, INTERVENTIONS) ---

    @hookspec
    def on_ticket_created(self, ticket):
        """Déclenché juste après la création d'un ticket (ex: notification)."""
        pass

    @hookspec
    def on_ticket_status_change(self, ticket, old_status, new_status):
        """Déclenché lors du changement de statut d'une intervention."""
        pass

    @hookspec
    def process_intervention_data(self, intervention):
        """Modifier ou enrichir les données d'une intervention avant traitement."""
        pass

    # --- SYSTEM & BACKGROUND ---

    @hookspec
    def register_periodic_tasks(self):
        """Enregistrer des fonctions à exécuter par le worker (Cron/Celery)."""
        pass

    @hookspec
    def register_settings_tabs(self):
        """Ajouter des onglets de configuration dans les paramètres système."""
        pass

    # --- API ---

    @hookspec
    def modify_api_response(self, view_name, data):
        """Intercepter et modifier les réponses JSON de l'API."""
        pass
