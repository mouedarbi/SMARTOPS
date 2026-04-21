"""
URL configuration for smartops_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.apps import apps
import importlib.util

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('system/', include('system.urls')),
    path('licensing/', include('licensing.urls')),
    path('', lambda request: redirect('dashboard')),
]

# --- MOTEUR DE ROUTAGE DYNAMIQUE (Hot-Plug) ---
# Ce bloc est le cerveau qui branche les modules installés
for app_config in apps.get_app_configs():
    # On cible uniquement nos modules premium
    if app_config.name.startswith('smartops_'):
        # On ignore les dossiers de base
        if app_config.name in ['system', 'licensing', 'smartops_project']:
            continue
            
        urls_module = f"{app_config.name}.urls"
        # Si le module possède un fichier urls.py, on l'injecte dans le système
        if importlib.util.find_spec(urls_module):
            urlpatterns.append(
                path(f'app/{app_config.name}/', include(urls_module))
            )
# ----------------------------------------------

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
