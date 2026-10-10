"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : smartops_project
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routes principales du Core, puis pages des modules installés (« Hot-Plug »).
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.apps import apps
from plugins_system.urls_loader import build_plugin_urlpatterns
from maintenance.media import protected_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('system/', include('system.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('licensing/', include('licensing.urls')),
    path('inventory/', include('inventory.urls')),
    path('technician/', include('technician.urls')),
    # REST API v0.2.0
    path('api/v1/', include('api.urls')),
    # SEO — application privée, indexation interdite
    # Fichiers téléversés : accès contrôlé (photos d'intervention), envoi délégué à nginx
    path('media/<path:path>', protected_media, name='protected_media'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('', lambda request: redirect('dashboard')),
]

# --- MOTEUR DE ROUTAGE DYNAMIQUE (Hot-Plug) ---
# Branche les pages des modules installés ; un module défectueux est ignoré (voir plugins_system/urls_loader.py).
urlpatterns += build_plugin_urlpatterns(
    [app_config.name for app_config in apps.get_app_configs()],
    active_plugin_apps=getattr(settings, 'DYNAMIC_PLUGIN_APPS', ()),
)
# ----------------------------------------------
