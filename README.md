# SMARTOPS - Plateforme de Maintenance Technique (GMAO)

SMARTOPS est une solution de gestion de maintenance (GMAO) de niveau entreprise, conçue pour être transversale, hautement configurable et auto-hébergeable. Elle permet aux entreprises de piloter l'ensemble de leur cycle de vie technique, de l'inventaire des équipements jusqu'à la facturation des interventions.

## 🚀 Architecture Système
SMARTOPS repose sur une architecture **hybride** innovante :
*   **Application Core (Auto-hébergée)** : Le moteur métier fonctionne en local sur le serveur du client, garantissant une souveraineté totale sur les données (RGPD).
*   **Portail Marketplace (Cloud)** : Un portail centralisé gère le cycle de vie des licences, l'activation des modules Premium et les mises à jour, via une authentification sécurisée par `Hardware Binding` (UUID unique par machine).

## 🧩 Fonctionnalités Premium & Modularité
Le système est nativement modulaire :
- **Gestion du Patrimoine (Core)** : Inventaire dynamique des Clients, Bâtiments et Équipements avec champs personnalisés (JSON).
- **Maintenance Avancée** : Workflow complet de tickets (Priorités, Types, État), historisation technique et traçabilité des interventions.
- **Planning Pro** : Gestion automatique des récurrences et des contrats de maintenance.
- **Workflow & Hooks** : Moteur d'extension `Pluggy` permettant d'injecter de la logique métier personnalisée sans modifier le coeur du système.
- **Licensing Intelligent** : Système de verrouillage par UUID machine assurant la protection de la propriété intellectuelle tout en offrant une expérience utilisateur fluide.

## 🛠 Prérequis Techniques
- **Runtime** : Python 3.13+, Django 6.0+
- **Base de données** : MySQL 8.0+
- **Environnement** : Virtualenv

## ⚙️ Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/mouedarbi/SMARTOPS.git
cd SMARTOPS
```

### 2. Mise en place de l'environnement
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Créez un fichier `.env` à la racine :
```ini
DEBUG=False
DATABASE_URL=mysql://user:password@localhost:3306/smartops_db
MARKETPLACE_URL=https://opensmartops.org
```

### 4. Initialisation
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

## 🏗 Subtilités Architecturales
*   **Hardware Binding** : Le système génère un UUID unique au premier lancement (`SystemConfiguration`). Il est immuable et obligatoire pour toute communication avec le portail Marketplace.
*   **Sync Silencieuse** : Le dashboard interroge le portail via une API non-bloquante avec un throttle de 24h pour vérifier les mises à jour du Core et des modules, garantissant une faible empreinte réseau.
*   **Auto-Installation** : Le système télécharge les archives des modules Premium, les installe dans l'environnement virtuel et exécute les migrations automatiquement dès l'activation de la licence.

## 📄 Licence
Propriétaire - SMARTOPS © 2026.
