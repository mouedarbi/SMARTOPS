"""
Fichier : middleware.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Langue de l'interface : celle choisie dans le profil de l'utilisateur connecté,
              le français (LANGUAGE_CODE) pour les pages sans connexion.
"""

from django.conf import settings
from django.utils import translation


class UserLanguageMiddleware:
    """Active la langue du profil de l'utilisateur connecté pendant la requête, puis rétablit la langue par défaut."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        language = settings.LANGUAGE_CODE
        if user is not None and user.is_authenticated and user.language in dict(settings.LANGUAGES):
            language = user.language
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', language)
        # Pas de langue qui « fuit » vers la requête suivante traitée par le même processus.
        translation.activate(settings.LANGUAGE_CODE)
        return response
