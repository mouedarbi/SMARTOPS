"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routage pour le licensing et les mises à jour.
"""

from django.urls import path
from .views import sync_portal_view, plugin_list_view, plugin_install_stream_view, plugin_uninstall_stream_view

urlpatterns = [
    path('modules/', plugin_list_view, name='plugin_list'),
    path('install-stream/', plugin_install_stream_view, name='plugin_install_stream'),
    path('uninstall-stream/', plugin_uninstall_stream_view, name='plugin_uninstall_stream'),
    path('sync/', sync_portal_view, name='sync_portal'),
]
