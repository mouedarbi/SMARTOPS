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

import subprocess
import sys
import logging
import os
import requests
import tempfile
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)

class PluginInstaller:
    """
    Service responsable de l'installation physique des paquets de modules (Hot-Plug).
    """

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

            # 3. Lancement des migrations Django
            PluginInstaller.run_migrations()
            
            return True, f"Installation de {package_name} terminée avec succès."

        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur PIP : {e.stderr}")
            return False, f"Erreur lors de l'installation pip : {e.stderr}"
        except Exception as e:
            logger.exception("Erreur inattendue lors de l'installation.")
            return False, str(e)

    @staticmethod
    def run_migrations():
        """
        Exécute les migrations pour intégrer les nouveaux modèles du plugin.
        """
        try:
            logger.info("Exécution des migrations Django...")
            call_command('migrate', interactive=False)
            logger.info("Migrations terminées.")
        except Exception as e:
            logger.error(f"Erreur lors des migrations : {e}")
