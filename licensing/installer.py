"""
Fichier : installer.py
Projet : SMARTOPS (Core Application)
Application : licensing
Auteur : Mohamed Ouedarbi
Version : 1.1
Description : Moteur universel d'installation de modules premium. 
              Gère le téléchargement sécurisé, l'installation pip et les migrations.
              Inspiré de la logique validée dans le POC.
"""

import importlib
import subprocess
import sys
import logging
from importlib.metadata import packages_distributions
import os
import requests
import tempfile
from django.conf import settings

logger = logging.getLogger(__name__)

class PluginInstaller:
    """
    Service responsable de l'installation physique des paquets de modules (Hot-Plug).
    """

    @staticmethod
    def distribution_names(package_name):
        """
        Nom(s) pip du paquet qui fournit le module Python `package_name`.
        Ex. : contrats_de_maintenance -> smartops-plugin-contrats-de-maintenance
        (nom défini dans le pyproject.toml de l'archive, différent du nom d'import).
        """
        importlib.invalidate_caches()
        return sorted(set(packages_distributions().get(package_name, []))) or [package_name]

    @staticmethod
    def install(package_name, download_url):
        """
        Télécharge le module depuis le Portail et l'installe via pip.
        """
        logger.info(f"Début de l'installation physique de {package_name}...")
        
        try:
            # 1. Téléchargement sécurisé dans un répertoire temporaire
            with tempfile.TemporaryDirectory() as temp_dir:
                package_file = os.path.join(temp_dir, f"{package_name}.tar.gz")
                
                logger.info(f"Téléchargement du package depuis : {download_url}")
                response = requests.get(download_url, stream=True, timeout=60)
                response.raise_for_status()
                
                with open(package_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info("Téléchargement réussi. Lancement de pip install...")
                
                # 2. Installation pip dans le venv actuel
                pip_command = [sys.executable, "-m", "pip", "install", package_file]
                result = subprocess.run(pip_command, capture_output=True, text=True, check=True)
                
                logger.info(f"Pip output : {result.stdout}")

            # 3. Lancement des migrations Django (dont celles du module)
            migrated, output = PluginInstaller.run_migrations()
            if not migrated:
                return False, f"Erreur lors des migrations : {output}"

            return True, f"Installation de {package_name} terminée avec succès."

        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur PIP : {e.stderr}")
            return False, f"Erreur lors de l'installation pip : {e.stderr}"
        except Exception as e:
            logger.exception("Erreur inattendue lors de l'installation.")
            return False, str(e)

    @staticmethod
    def migrate_command():
        """
        Commande `manage.py migrate` lancée dans un nouveau processus. Le processus en cours a calculé
        INSTALLED_APPS à son démarrage, avant l'activation du module : il ne connaît pas les migrations
        du module. Un nouveau processus relit les modules actifs en base (settings.get_dynamic_apps).
        """
        return [sys.executable, str(settings.BASE_DIR / 'manage.py'), 'migrate', '--noinput']

    @staticmethod
    def run_migrations():
        """
        Applique les migrations du Core et des modules actifs. Le module doit déjà être actif en base.
        Retourne (succès, sortie de la commande).
        """
        logger.info("Exécution des migrations Django...")
        result = subprocess.run(PluginInstaller.migrate_command(), capture_output=True, text=True,
                                cwd=settings.BASE_DIR)
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            logger.error(f"Erreur lors des migrations : {output}")
            return False, output
        logger.info("Migrations terminées.")
        return True, output
