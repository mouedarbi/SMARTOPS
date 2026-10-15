"""
Fichier : tests_migrations.py
Application : licensing
Description : Les migrations d'un module qui vient d'être activé sont appliquées à l'installation (#58).
"""

import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from licensing.installer import PluginInstaller

MODULE_MODELS = """
from django.db import models


class Widget(models.Model):
    name = models.CharField(max_length=50)
"""

MODULE_MIGRATION = """
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Widget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
            ],
        ),
    ]
"""


class ModuleMigrationsTests(SimpleTestCase):
    """
    Base SQLite dans un fichier : la commande de migration tourne dans un autre processus, comme à
    l'installation réelle, et doit trouver le module activé en base après le démarrage du Core.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        package = root / 'smo_test_module'
        (package / 'migrations').mkdir(parents=True)
        (package / '__init__.py').write_text('')
        (package / 'models.py').write_text(MODULE_MODELS)
        (package / 'migrations' / '__init__.py').write_text('')
        (package / 'migrations' / '0001_initial.py').write_text(MODULE_MIGRATION)
        self.db_path = root / 'db.sqlite3'
        self.env = {**os.environ, 'DATABASE_URL': f'sqlite:///{self.db_path}', 'PYTHONPATH': str(root)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_migrations(self):
        with patch.dict(os.environ, self.env, clear=True):
            return PluginInstaller.run_migrations()

    def tables(self):
        with sqlite3.connect(self.db_path) as conn:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def test_migrations_du_module_active_appliquees(self):
        # Core seul, puis activation du module en base (comme l'installation, avant les migrations).
        migrated, output = self.run_migrations()
        self.assertTrue(migrated, output)
        self.assertNotIn('smo_test_module_widget', self.tables())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO licensing_plugin (slug, python_path, priority, name, version, license_key, is_active,"
                " installed_at, updated_at) VALUES ('smo-test-module', 'smo_test_module', 100, 'Test', '1.0', '',"
                " 1, '2026-10-15 00:00:00', '2026-10-15 00:00:00')"
            )

        migrated, output = self.run_migrations()
        self.assertTrue(migrated, output)
        self.assertIn('smo_test_module_widget', self.tables())

    def test_echec_des_migrations_signale(self):
        with patch.object(PluginInstaller, 'migrate_command',
                          return_value=[*PluginInstaller.migrate_command(), 'application_inconnue']):
            migrated, output = self.run_migrations()
        self.assertFalse(migrated)
        self.assertIn('application_inconnue', output)

    def test_commande_dans_un_nouveau_processus(self):
        command = PluginInstaller.migrate_command()
        self.assertEqual(command[1:], [str(settings.BASE_DIR / 'manage.py'), 'migrate', '--noinput'])
