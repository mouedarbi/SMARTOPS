import pluggy

hookimpl = pluggy.HookimplMarker("smartops")

class DemoPlugin:
    """
    Implémentation simple du plugin de démonstration SmartOps.
    """
    
    @hookimpl
    def register_dashboard_widgets(self):
        """
        Ajoute un widget démo au dashboard.
        """
        return [{
            "id": "demo-widget",
            "title": "Module Démo",
            "content": "Bonjour ! Ce widget provient du plugin Premium activé par clé de licence.",
            "type": "info"
        }]

    @hookimpl
    def register_menu_items(self):
        """
        Ajoute un item au menu latéral.
        """
        return [{
            "label": "Demo Premium",
            "url": "/demo-premium/",
            "icon": "star"
        }]

    @hookimpl
    def process_data(self, data):
        """
        Ajoute une clé 'demo_processed' aux données reçues.
        """
        data["demo_processed"] = True
        return data

# Instanciation pour l'enregistrement
plugin_implementation = DemoPlugin()
