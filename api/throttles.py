"""
Fichier : throttles.py
Projet : SMARTOPS (Core Application)
Application : api
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Limitation du nombre de demandes de jeton JWT par adresse IP.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from accounts.security import get_client_ip


class TokenObtainRateThrottle(SimpleRateThrottle):
    """Taux lu à l'exécution (API_TOKEN_THROTTLE_RATE) ; None désactive la limite."""
    scope = 'auth_token'

    def get_rate(self):
        """Taux lu à chaque requête dans API_TOKEN_THROTTLE_RATE."""
        return getattr(settings, 'API_TOKEN_THROTTLE_RATE', None)

    def get_cache_key(self, request, view):
        """Compteur par adresse IP du client."""
        return self.cache_format % {'scope': self.scope, 'ident': get_client_ip(request)}


class MobileLicenseRateThrottle(TokenObtainRateThrottle):
    """Vérification de licence de l'app mobile, par adresse IP (MOBILE_LICENSE_THROTTLE_RATE)."""
    scope = 'mobile_license'

    def get_rate(self):
        """Taux lu à chaque requête dans MOBILE_LICENSE_THROTTLE_RATE."""
        return getattr(settings, 'MOBILE_LICENSE_THROTTLE_RATE', None)
