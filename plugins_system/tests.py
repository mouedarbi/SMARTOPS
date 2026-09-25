"""
Tests du montage des pages des modules (plugins_system/urls_loader.py).
Chaque test crée de vrais paquets Python temporaires : c'est le chemin d'import réel qui est exercé.
"""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

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
