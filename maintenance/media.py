"""
Fichier : media.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Accès contrôlé aux fichiers téléversés (/media/). Django vérifie les droits puis
              délègue l'envoi du fichier à nginx (en-tête X-Accel-Redirect).
"""

import mimetypes
import posixpath
from urllib.parse import quote

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.static import serve

from accounts.views import is_management_staff
from .models import InterventionPhoto
from .services import related_ticket_ids

# Emplacement interne nginx (directive « internal ») qui pointe sur MEDIA_ROOT.
PROTECTED_MEDIA_PREFIX = '/protected-media/'


def _authenticated_user(request):
    """Utilisateur de la session web, ou du jeton JWT (application mobile) à défaut."""
    if request.user.is_authenticated:
        return request.user
    from rest_framework_simplejwt.authentication import JWTAuthentication
    try:
        result = JWTAuthentication().authenticate(request)
    except Exception:
        return None
    return result[0] if result else None


def _can_view(user, path):
    """
    Gestion : tous les fichiers. Technicien : photos des tickets qu'il peut ouvrir (les siens et
    les tickets liés, origine ou suite). Personne d'autre.
    """
    if is_management_staff(user):
        return True
    if user.role != 'technician':
        return False
    technician = getattr(user, 'technician_profile', None)
    photo = InterventionPhoto.objects.filter(image=path).select_related('ticket').first()
    if technician is None or photo is None:
        return False
    return photo.ticket.technician_id == technician.pk or photo.ticket_id in related_ticket_ids(technician)


def protected_media(request, path):
    """Sert un fichier de MEDIA_ROOT si l'utilisateur y a droit, sinon 404 (on ne révèle rien)."""
    path = posixpath.normpath(path).lstrip('/')
    if path.startswith('..') or path in ('', '.'):
        raise Http404
    user = _authenticated_user(request)
    if user is None or not _can_view(user, path):
        raise Http404

    if settings.DEBUG:
        # Développement sans nginx : Django sert le fichier lui-même.
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    response = HttpResponse(content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
    response['X-Accel-Redirect'] = PROTECTED_MEDIA_PREFIX + quote(path)
    response['Cache-Control'] = 'private, max-age=3600'
    return response
