"""
Fichier : tests.py
Application : licensing
Auteur : Mohamed Ouedarbi
Description : Tests unitaires du module de licensing, validation de plugins et communication mockée.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from licensing.models import Plugin
from licensing.services import LicenseService
from system.models import SystemConfiguration

User = get_user_model()


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class LicensingUnitTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin_lic',
            password='password123',
            role='admin'
        )
        self.client_http = HttpClient()
        self.client_http.login(username='admin_lic', password='password123')
        self.sys_config = SystemConfiguration.get_instance()

    def test_plugin_model_creation_and_hash(self):
        """Vérifie la création d'un modèle Plugin et la fonction statique de hachage de clé."""
        plugin = Plugin.objects.create(
            slug='smartops-analytics',
            python_path='smartops_analytics',
            name='Module Analytics',
            version='1.0.0',
            license_key='1234-5678-90ab-cdef',
            is_active=True
        )
        self.assertEqual(plugin.slug, 'smartops-analytics')
        self.assertTrue(plugin.is_active)
        self.assertIn('Module Analytics', str(plugin))

        # Test de hachage SHA-256
        hashed = Plugin.hash_key('1234-5678-90ab-cdef')
        self.assertIsInstance(hashed, str)
        self.assertEqual(len(hashed), 64)

    @patch('requests.post')
    def test_license_service_validate_key_success(self, mock_post):
        """Vérifie la validation réussie d'une clé auprès du portail mocké."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "plugin_slug": "smartops-iot",
            "plugin_name": "Connecteur IoT",
            "version": "1.2.0",
            "download_url": "https://www.opensmartops.org/download/test/"
        }
        mock_post.return_value = mock_response

        result = LicenseService.validate_key_with_portal("valid-license-key-uuid")
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("plugin_slug"), "smartops-iot")
        self.assertEqual(result.get("version"), "1.2.0")

    @patch('requests.post')
    def test_license_service_validate_key_forbidden_quota(self, mock_post):
        """Vérifie le rejet d'une clé lorsque le quota est dépassé ou la clé invalide."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        result = LicenseService.validate_key_with_portal("exceeded-quota-uuid")
        self.assertFalse(result.get("success"))
        self.assertIn("déjà activée", result.get("error"))

    def test_plugin_list_view_get(self):
        """Vérifie l'affichage de la page de gestion des plugins."""
        url = reverse('plugin_list')
        response = self.client_http.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modules Premium")

    def test_plugin_menus_hidden_when_no_active_plugin(self):
        """Sans module actif en base, aucune entrée de menu de plugin n'est injectée."""
        from plugins_system.context_processors import plugin_menus
        from django.test import RequestFactory

        Plugin.objects.all().delete()
        ctx = plugin_menus(RequestFactory().get('/'))
        self.assertEqual(ctx['plugin_menus'], [])

        # La section « Extensions » ne doit pas apparaître dans la sidebar
        response = self.client_http.get(reverse('plugin_list'))
        self.assertNotContains(response, '>Extensions<')

    def test_hot_reload_sends_sighup_under_gunicorn(self):
        """_hot_reload envoie SIGHUP au process maître lorsqu'on tourne sous gunicorn."""
        from licensing.views import _hot_reload
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.META['SERVER_SOFTWARE'] = 'gunicorn/26.0.0'
        with patch('licensing.views.os.kill') as mock_kill, \
             patch('licensing.views.os.getppid', return_value=4242):
            lines = _hot_reload(request)
            mock_kill.assert_called_once()
            args = mock_kill.call_args[0]
            self.assertEqual(args[0], 4242)
        self.assertTrue(any('à chaud' in line for line in lines))

    def test_hot_reload_noop_without_gunicorn(self):
        """Hors gunicorn (runserver), _hot_reload n'envoie aucun signal."""
        from licensing.views import _hot_reload
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.META['SERVER_SOFTWARE'] = 'WSGIServer/0.2 CPython/3.13'
        with patch('licensing.views.os.kill') as mock_kill:
            _hot_reload(request)
            mock_kill.assert_not_called()
