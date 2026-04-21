"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routage pour le licensing et les mises à jour.
"""

from django.urls import path
from .views import sync_portal_view

urlpatterns = [
    path('sync/', sync_portal_view, name='sync_portal'),
]
