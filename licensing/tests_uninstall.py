"""
Fichier : tests_uninstall.py
Application : licensing
Description : Désinstallation complète d'un module (paquet pip retiré) et menus limités aux modules actifs.
"""

from unittest.mock import MagicMock, patch

import pluggy
from django.contrib.auth import get_user_model
from django.test import Client as HttpClient, RequestFactory, TestCase, override_settings
from django.urls import reverse

from licensing.installer import PluginInstaller
from licensing.models import Plugin
from plugins_system.hookspecs import SmartOpsHookSpecs
from system.models import SystemConfiguration

User = get_user_model()
hookimpl = pluggy.HookimplMarker("smartops")


class DistributionNameTests(TestCase):

    @patch('licensing.installer.packages_distributions',
           return_value={'contrats_de_maintenance': ['smartops-plugin-contrats-de-maintenance']})
    def test_import_name_is_resolved_to_the_pip_package(self, _):
        self.assertEqual(PluginInstaller.distribution_names('contrats_de_maintenance'),
                         ['smartops-plugin-contrats-de-maintenance'])

    @patch('licensing.installer.packages_distributions', return_value={})
    def test_unknown_module_falls_back_to_its_import_name(self, _):
        self.assertEqual(PluginInstaller.distribution_names('module_inconnu'), ['module_inconnu'])


@override_settings(SECURE_SSL_REDIRECT=False, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class UninstallStreamTests(TestCase):

    def setUp(self):
        User.objects.create_user(username='adm_uninst', password='pass', role='admin')
        self.http = HttpClient()
        self.http.login(username='adm_uninst', password='pass')
        SystemConfiguration.get_instance()
        self.plugin = Plugin.objects.create(slug='contrats-de-maintenance', name='Contrats de Maintenance',
                                            python_path='contrats_de_maintenance', license_key='cle', is_active=True)

    def uninstall(self, returncode):
        process = MagicMock()
        process.stdout = iter(["Successfully uninstalled\n"])
        process.returncode = returncode
        with patch('licensing.views.requests.post', return_value=MagicMock(status_code=200)), \
                patch('licensing.installer.packages_distributions',
                      return_value={'contrats_de_maintenance': ['smartops-plugin-contrats-de-maintenance']}), \
                patch('licensing.views.subprocess.Popen', return_value=process) as popen:
            response = self.http.get(reverse('plugin_uninstall_stream') + '?slug=contrats-de-maintenance')
            output = b''.join(response.streaming_content).decode()
        return popen.call_args.args[0], output

    def test_pip_uninstalls_the_real_package(self):
        command, output = self.uninstall(returncode=0)
        self.assertEqual(command[-1], 'smartops-plugin-contrats-de-maintenance')
        self.assertIn('MODULE DESINSTALLE AVEC SUCCÈS', output)
        self.assertFalse(Plugin.objects.filter(pk=self.plugin.pk).exists())

    def test_pip_failure_is_reported_and_registry_kept(self):
        _, output = self.uninstall(returncode=1)
        self.assertIn('ERREUR PIP (Code 1)', output)
        self.assertNotIn('SUCCÈS', output)
        self.assertTrue(Plugin.objects.filter(pk=self.plugin.pk).exists())


class MenuOfActiveModulesTests(TestCase):

    def setUp(self):
        pm = pluggy.PluginManager("smartops")
        pm.add_hookspecs(SmartOpsHookSpecs)

        class Menu:
            def __init__(self, label):
                self.label = label

            @hookimpl
            def register_menu_items(self):
                return [{'label': self.label, 'url': '/app/x/', 'icon': 'la-cube'}]

        pm.register(Menu('Module actif'), name='module_actif')
        pm.register(Menu('Module résiduel'), name='module_residuel')
        patcher = patch('plugins_system.context_processors.plugin_manager', pm)
        patcher.start()
        self.addCleanup(patcher.stop)
        Plugin.objects.create(slug='module-actif', name='Module actif', python_path='module_actif', is_active=True)

    def test_only_modules_active_in_registry_provide_menus(self):
        from plugins_system.context_processors import plugin_menus
        labels = [m['label'] for m in plugin_menus(RequestFactory().get('/'))['plugin_menus']]
        self.assertEqual(labels, ['Module actif'])
