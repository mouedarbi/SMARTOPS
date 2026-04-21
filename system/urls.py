"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routage pour l'application système.
"""

from django.urls import path
from .views import system_config_view, dashboard_view

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('config/', system_config_view, name='system_config'),
]
