"""
Fichier : tests_login_protection.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Limitation des tentatives de connexion (django-axes) et des demandes de jeton JWT.
"""

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import CustomUser

AXES_ON = dict(
    AXES_ENABLED=True,
    AUTHENTICATION_BACKENDS=[
        'axes.backends.AxesStandaloneBackend',
        'django.contrib.auth.backends.ModelBackend',
    ],
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)


@override_settings(**AXES_ON)
class LoginLockoutTestCase(TestCase):
    """Après 5 échecs, le couple identifiant + IP est bloqué, même avec le bon mot de passe."""

    def setUp(self):
        CustomUser.objects.create_user(username='mgr_lock', password='Bon-Mot-De-Passe1', role='manager')
        CustomUser.objects.create_user(username='tech_lock', password='Bon-Mot-De-Passe1', role='technician')

    def fail(self, url, username, times=5, ip='203.0.113.7'):
        for _ in range(times):
            self.client.post(url, {'username': username, 'password': 'mauvais'}, HTTP_X_REAL_IP=ip)

    def test_web_login_locked_after_five_failures(self):
        url = reverse('login')
        self.fail(url, 'mgr_lock')
        response = self.client.post(url, {'username': 'mgr_lock', 'password': 'Bon-Mot-De-Passe1'},
                                    HTTP_X_REAL_IP='203.0.113.7')
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_other_ip_is_not_locked(self):
        url = reverse('login')
        self.fail(url, 'mgr_lock')
        response = self.client.post(url, {'username': 'mgr_lock', 'password': 'Bon-Mot-De-Passe1'},
                                    HTTP_X_REAL_IP='198.51.100.9')
        self.assertEqual(response.status_code, 302)

    def test_four_failures_then_success_is_allowed(self):
        url = reverse('login')
        self.fail(url, 'mgr_lock', times=4)
        response = self.client.post(url, {'username': 'mgr_lock', 'password': 'Bon-Mot-De-Passe1'},
                                    HTTP_X_REAL_IP='203.0.113.7')
        self.assertEqual(response.status_code, 302)

    def test_technician_login_locked_after_five_failures(self):
        url = reverse('technician_login')
        self.fail(url, 'tech_lock')
        response = self.client.post(url, {'username': 'tech_lock', 'password': 'Bon-Mot-De-Passe1'},
                                    HTTP_X_REAL_IP='203.0.113.7')
        self.assertEqual(response.status_code, 429)

    def test_api_token_refused_after_five_failures(self):
        api = APIClient()
        for _ in range(5):
            api.post('/api/v1/auth/token/', {'username': 'mgr_lock', 'password': 'mauvais'}, HTTP_X_REAL_IP='203.0.113.7')
        response = api.post('/api/v1/auth/token/', {'username': 'mgr_lock', 'password': 'Bon-Mot-De-Passe1'},
                            HTTP_X_REAL_IP='203.0.113.7')
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn('access', getattr(response, 'data', {}) or {})


@override_settings(API_TOKEN_THROTTLE_RATE='3/min', SECURE_SSL_REDIRECT=False,
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TokenThrottleTestCase(TestCase):
    """Au-delà du taux autorisé, l'obtention de jeton répond 429 pour cette IP."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        CustomUser.objects.create_user(username='mgr_rate', password='pass', role='manager')

    def test_token_requests_are_rate_limited_per_ip(self):
        api = APIClient()
        for _ in range(3):
            r = api.post('/api/v1/auth/token/', {'username': 'mgr_rate', 'password': 'pass'}, HTTP_X_REAL_IP='203.0.113.8')
            self.assertEqual(r.status_code, 200)
        r = api.post('/api/v1/auth/token/', {'username': 'mgr_rate', 'password': 'pass'}, HTTP_X_REAL_IP='203.0.113.8')
        self.assertEqual(r.status_code, 429)
        r = api.post('/api/v1/auth/token/', {'username': 'mgr_rate', 'password': 'pass'}, HTTP_X_REAL_IP='198.51.100.10')
        self.assertEqual(r.status_code, 200)
