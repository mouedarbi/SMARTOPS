"""
Fichier : security.py
Application : accounts
Description : Adresse IP du client derrière le proxy nginx (limitation des tentatives de connexion).
"""


def get_client_ip(request):
    """IP transmise par nginx (X-Real-IP), à défaut REMOTE_ADDR."""
    meta = request.META
    return meta.get('HTTP_X_REAL_IP') or meta.get('REMOTE_ADDR') or ''
