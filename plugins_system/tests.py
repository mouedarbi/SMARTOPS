"""
Tests du montage des pages des modules (plugins_system/urls_loader.py).
Chaque test crée de vrais paquets Python temporaires : c'est le chemin d'import réel qui est exercé.
"""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from plugins_system.urls_loader import build_plugin_urlpatterns, is_mountable

VALID_URLS = (
    "from django.http import HttpResponse\n"
    "from django.urls import path\n"
    "urlpatterns = [path('', lambda request: HttpResponse('ok'), name='index')]\n"
)


class TemporaryModulesMixin:
    """Fournit un dossier ajouté à sys.path où créer des paquets, nettoyé après chaque test."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='smartops_modules_test_'))
        sys.path.insert(0, str(self.root))
        self._known_modules = set(sys.modules)
        importlib.invalidate_caches()

    def tearDown(self):
        sys.path.remove(str(self.root))
        for name in set(sys.modules) - self._known_modules:
            sys.modules.pop(name, None)
        importlib.invalidate_caches()
        shutil.rmtree(self.root, ignore_errors=True)

    def make_package(self, name, urls_source=None):
        package = self.root / name
        package.mkdir()
        (package / '__init__.py').write_text('')
        if urls_source is not None:
            (package / 'urls.py').write_text(urls_source)
        importlib.invalidate_caches()


class PluginUrlLoaderTests(TemporaryModulesMixin, SimpleTestCase):

    def routes(self, patterns):
        return [str(p.pattern) for p in patterns]

    def test_valid_module_is_mounted_under_app_prefix(self):
        self.make_package('smartops_ok', VALID_URLS)
        patterns = build_plugin_urlpatterns(['smartops_ok'])
        self.assertEqual(self.routes(patterns), ['app/smartops_ok/'])

    def test_module_with_syntax_error_is_ignored_and_logged(self):
        self.make_package('smartops_broken', "urlpatterns = [path('', view'")  # erreur de syntaxe volontaire
        self.make_package('smartops_ok', VALID_URLS)
        with self.assertLogs('plugins_system.urls_loader', level='ERROR') as logs:
            patterns = build_plugin_urlpatterns(['smartops_broken', 'smartops_ok'])
        # Le module fautif est ignoré, le module valide reste monté.
        self.assertEqual(self.routes(patterns), ['app/smartops_ok/'])
        self.assertIn('smartops_broken', logs.output[0])

    def test_module_with_failing_import_is_ignored(self):
        self.make_package('smartops_import', "import module_qui_n_existe_pas\nurlpatterns = []\n")
        with self.assertLogs('plugins_system.urls_loader', level='ERROR'):
            patterns = build_plugin_urlpatterns(['smartops_import'])
        self.assertEqual(patterns, [])

    def test_failing_module_does_not_change_order_of_valid_ones(self):
        for name in ('smartops_a', 'smartops_c'):
            self.make_package(name, VALID_URLS)
        self.make_package('smartops_b', 'raise RuntimeError("boom")\n')
        with self.assertLogs('plugins_system.urls_loader', level='ERROR'):
            patterns = build_plugin_urlpatterns(['smartops_a', 'smartops_b', 'smartops_c'])
        self.assertEqual(self.routes(patterns), ['app/smartops_a/', 'app/smartops_c/'])

    def test_module_without_urls_file_is_skipped_silently(self):
        self.make_package('smartops_nourls')
        with self.assertNoLogs('plugins_system.urls_loader', level='ERROR'):
            self.assertEqual(build_plugin_urlpatterns(['smartops_nourls']), [])

    def test_core_apps_are_never_treated_as_modules(self):
        for name in ('system', 'licensing', 'smartops_project', 'maintenance', 'django.contrib.admin'):
            self.assertFalse(is_mountable(name), name)
        self.assertTrue(is_mountable('smartops_analytics'))

    def test_missing_module_is_ignored_without_crashing(self):
        # Application déclarée mais non importable : traitée comme un module défectueux, pas d'exception.
        with self.assertLogs('plugins_system.urls_loader', level='ERROR'):
            patterns = build_plugin_urlpatterns(['smartops_introuvable_zzz'])
        self.assertEqual(patterns, [])


class ActivePluginMountingTests(TemporaryModulesMixin, SimpleTestCase):
    """Un module actif est monté quel que soit le nom de son paquet (le Portal nomme les paquets d'après le slug)."""

    def routes(self, patterns):
        return [str(p.pattern) for p in patterns]

    def test_active_module_without_smartops_prefix_is_mounted(self):
        self.make_package('stock_pieces_detachees', VALID_URLS)
        patterns = build_plugin_urlpatterns(['stock_pieces_detachees'], active_plugin_apps=['stock_pieces_detachees'])
        self.assertEqual(self.routes(patterns), ['app/stock_pieces_detachees/'])

    def test_module_not_in_active_list_is_not_mounted(self):
        self.make_package('stock_pieces_detachees', VALID_URLS)
        self.assertEqual(build_plugin_urlpatterns(['stock_pieces_detachees'], active_plugin_apps=[]), [])
        self.assertEqual(build_plugin_urlpatterns(['stock_pieces_detachees']), [])  # comportement historique

    def test_smartops_prefix_is_still_mounted_without_being_listed(self):
        self.make_package('smartops_legacy', VALID_URLS)
        patterns = build_plugin_urlpatterns(['smartops_legacy'], active_plugin_apps=[])
        self.assertEqual(self.routes(patterns), ['app/smartops_legacy/'])

    def test_core_apps_are_never_mounted_even_if_listed_as_active(self):
        self.assertFalse(is_mountable('licensing', active_plugin_apps=['licensing']))
        self.assertFalse(is_mountable('system', active_plugin_apps=['system']))

    def test_active_module_with_error_is_ignored_and_others_survive(self):
        self.make_package('hrm_module', "syntax error here\n")
        self.make_package('flotte_module', VALID_URLS)
        with self.assertLogs('plugins_system.urls_loader', level='ERROR'):
            patterns = build_plugin_urlpatterns(
                ['hrm_module', 'flotte_module'], active_plugin_apps=['hrm_module', 'flotte_module'])
        self.assertEqual(self.routes(patterns), ['app/flotte_module/'])


class DynamicPluginAppsSettingTests(SimpleTestCase):
    def test_dynamic_plugin_apps_are_exposed_and_installed(self):
        from django.conf import settings
        self.assertIsInstance(settings.DYNAMIC_PLUGIN_APPS, list)
        for app in settings.DYNAMIC_PLUGIN_APPS:
            self.assertIn(app, settings.INSTALLED_APPS)


VIEW_URLS = (
    "from django.contrib.auth.decorators import login_required\n"
    "from django.http import HttpResponse\n"
    "from django.urls import path\n"
    "@login_required\n"
    "def index(request):\n"
    "    return HttpResponse('page du module')\n"
    "urlpatterns = [path('', index)]\n"
)


@override_settings(ROOT_URLCONF='urlconf_demo', SECURE_SSL_REDIRECT=False)
class MountedModulePageTests(TemporaryModulesMixin, TestCase):
    """Bout en bout : la page d'un module actif, monté par le chargeur, répond pour un utilisateur connecté."""

    def setUp(self):
        super().setUp()
        self.make_package('demo_actif', VIEW_URLS)
        (self.root / 'urlconf_demo.py').write_text(
            "from smartops_project.urls import urlpatterns as core_urlpatterns\n"
            "from plugins_system.urls_loader import build_plugin_urlpatterns\n"
            "urlpatterns = core_urlpatterns + build_plugin_urlpatterns("
            "['demo_actif'], active_plugin_apps=['demo_actif'])\n"
        )
        importlib.invalidate_caches()
        self.user = get_user_model().objects.create_user(username='u1', password='x', role='manager')

    def test_logged_in_user_gets_the_module_page(self):
        self.client.force_login(self.user)
        response = self.client.get('/app/demo_actif/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'page du module')

    def test_anonymous_user_is_redirected_to_login(self):
        self.assertEqual(self.client.get('/app/demo_actif/').status_code, 302)

    def test_unlisted_url_stays_404(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/app/autre_module/').status_code, 404)
