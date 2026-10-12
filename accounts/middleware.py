"""
Fichier : middleware.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Langue de l'interface : celle choisie dans le profil de l'utilisateur connecté ;
              sans connexion (pages de connexion, blocage), celle du navigateur, français par défaut.
"""

from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


class UserLanguageMiddleware:
    """
    Active la langue du profil de l'utilisateur connecté (sinon celle du navigateur) pendant la requête,
    puis rétablit la langue par défaut.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        authenticated = user is not None and user.is_authenticated
        if authenticated and user.language in dict(settings.LANGUAGES):
            language = user.language
        else:
            # Pas de préférence enregistrée : langue du navigateur parmi LANGUAGES, français sinon.
            language = translation.get_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', language)
        if not authenticated:
            patch_vary_headers(response, ('Accept-Language',))
        # Pas de langue qui « fuit » vers la requête suivante traitée par le même processus.
        translation.activate(settings.LANGUAGE_CODE)
        return response
