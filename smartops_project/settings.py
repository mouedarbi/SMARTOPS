"""
Fichier : settings.py
Projet : SMARTOPS (Core Application)
Application : smartops_project
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Réglages du projet SMARTOPS Core, lus depuis le fichier .env.
              Les modules premium actifs sont ajoutés à INSTALLED_APPS au démarrage.
"""

import os
import sqlite3
import sys
from pathlib import Path
import environ
import pymysql
from datetime import timedelta

# Chemins du projet : BASE_DIR / 'sous-dossier'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Prise en charge de MySQL via PyMySQL
pymysql.version_info = (2, 2, 8, "final", 0)
pymysql.install_as_MySQLdb()

# Initialisation de django-environ
env = environ.Env(
    DEBUG=(bool, False)
)
# Lecture du fichier .env
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

def get_dynamic_apps():
    """
    Récupère la liste des applications premium activées directement en SQL 
    pour éviter de charger l'ORM Django trop tôt (problème de l'œuf et la poule).
    Supporte SQLite et MySQL.
    """
    dynamic_apps = []
    # On récupère la config comme Django le ferait (par défaut sqlite)
    db_url = env('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
    db_config = env.db_url_config(db_url)
    
    try:
        if 'mysql' in db_config['ENGINE']:
            conn = pymysql.connect(
                host=db_config.get('HOST', 'localhost'),
                user=db_config.get('USER'),
                password=db_config.get('PASSWORD'),
                database=db_config.get('NAME'),
                port=int(db_config.get('PORT', 3306))
            )
            cursor = conn.cursor()
            cursor.execute("SELECT python_path FROM licensing_plugin WHERE is_active=1 ORDER BY priority ASC")
            dynamic_apps = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
        elif 'sqlite3' in db_config['ENGINE']:
            db_path = db_config['NAME']
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT python_path FROM licensing_plugin WHERE is_active=1 ORDER BY priority ASC")
                dynamic_apps = [row[0] for row in cursor.fetchall() if row[0]]
                conn.close()
    except Exception:
        # En cas d'erreur (ex: table non encore créée au premier migrate), on ignore
        pass
    return dynamic_apps

# SÉCURITÉ : la clé secrète de production ne doit jamais être divulguée.
# Fournie par le fichier .env (aucune valeur par défaut dans le code source).
SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Applications installées

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Bibliothèques tierces
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'axes',
    # Applications du Core SMARTOPS
    'accounts.apps.AccountsConfig',
    'system.apps.SystemConfig',
    'licensing.apps.LicensingConfig',
    'inventory.apps.InventoryConfig',
    'maintenance.apps.MaintenanceConfig',
    'schedule',
    'technician',
    'api',
]

# Injection automatique des plugins depuis la base de données
# Modules actifs en base : lus une seule fois, réutilisés par le montage des URLs (plugins_system/urls_loader.py).
DYNAMIC_PLUGIN_APPS = get_dynamic_apps()
INSTALLED_APPS += DYNAMIC_PLUGIN_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'smartops_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'system.context_processors.system_settings',
                'plugins_system.context_processors.plugin_menus',
            ],
        },
    },
]

WSGI_APPLICATION = 'smartops_project.wsgi.application'

# Base de données
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# Fichiers média
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- SÉCURITÉ COOKIES ---
SESSION_COOKIE_NAME = 'smartops_sessionid'
CSRF_COOKIE_NAME = 'smartops_csrftoken'

# En production (DEBUG=False), on renforce les protections HTTPS.
# Le Core étant auto-hébergé, ces paramètres ne s'activent qu'une fois
# le serveur déployé avec un certificat SSL (accès API mobile + synchro Portal).
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Actifs en dev et en prod
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Redirections d'authentification
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# --- LIMITATION DES TENTATIVES DE CONNEXION (django-axes) ---
# Tests : client.login() n'envoie pas de requête, axes n'est donc actif que dans ses tests dédiés.
TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
] if TESTING else [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_ENABLED = not TESTING
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_RESET_ON_SUCCESS = True
AXES_CLIENT_IP_CALLABLE = 'accounts.security.get_client_ip'

# Cache partagé entre les workers gunicorn (compteurs de limitation de débit)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'smartops_cache',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'SMARTOPS API',
    'DESCRIPTION': 'API REST de la plateforme de maintenance SMARTOPS (GMAO).',
    'VERSION': '0.2.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Demandes de jeton JWT par adresse IP (api/throttles.py)
API_TOKEN_THROTTLE_RATE = None if TESTING else env('API_TOKEN_THROTTLE_RATE', default='5/min')
# Vérification de licence par l'application mobile (essais de clés en série).
MOBILE_LICENSE_THROTTLE_RATE = None if TESTING else env('MOBILE_LICENSE_THROTTLE_RATE', default='10/min')

# --- JWT ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'TOKEN_OBTAIN_SERIALIZER': 'api.serializers.SmartOpsTokenObtainPairSerializer',
}

# --- LOGGING ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file_errors', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file_errors', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'
AUTH_USER_MODEL = 'accounts.CustomUser'
# Type de clé primaire par défaut
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CONFIGURATION INTERCONNEXION (PFE) ---
# MARKETPLACE_URL : URL du portail commercial SMARTOPS_PORTAL.
# En local (DEBUG=True), on pointe vers le port par défaut de Django (8000).
# En production, on utilise le domaine sécurisé.
MARKETPLACE_URL = env('MARKETPLACE_URL', default='https://www.opensmartops.org' if not DEBUG else 'http://127.0.0.1:8000')
