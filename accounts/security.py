"""
Fichier : security.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Adresse IP du client derrière le proxy nginx (limitation des tentatives de connexion).
"""


def get_client_ip(request):
    """IP transmise par nginx (X-Real-IP), à défaut REMOTE_ADDR."""
    meta = request.META
    return meta.get('HTTP_X_REAL_IP') or meta.get('REMOTE_ADDR') or ''
