"""
Fichier : throttles.py
Application : api
Description : Limitation du nombre de demandes de jeton JWT par adresse IP.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from accounts.security import get_client_ip


class TokenObtainRateThrottle(SimpleRateThrottle):
    """Taux lu à l'exécution (API_TOKEN_THROTTLE_RATE) ; None désactive la limite."""
    scope = 'auth_token'

    def get_rate(self):
        return getattr(settings, 'API_TOKEN_THROTTLE_RATE', None)

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': get_client_ip(request)}
