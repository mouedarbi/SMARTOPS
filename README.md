# SMARTOPS

SMARTOPS est une plateforme de gestion de maintenance technique (GMAO) conçue pour optimiser le suivi des interventions, la gestion des équipements et la planification technique.

## 🚀 Fonctionnalités principales
- **Gestion des Tickets** : Création et planification d'interventions avec filtrage dynamique AJAX (Client > Bâtiment > Équipement).
- **Suivi Technique** : Dashboard complet avec indicateurs de performance (taux de réussite, durée moyenne).
- **Intégration Calendrier** : Synchronisation automatique des interventions via `django-scheduler`.
- **Gestion de Modules (Plugins)** : Système d'installation modulaire avec licence bindée sur UUID machine.
- **Connectivité Portail** : Synchronisation transparente avec le portail Marketplace (OpenSMARTOPS).

## 🛠 Prérequis
- Python 3.13+
- MySQL Server 8.0+
- Virtualenv

## ⚙️ Installation

### 1. Cloner le projet
```bash
git clone https://github.com/mouedarbi/SMARTOPS.git
cd SMARTOPS
```

### 2. Configuration de l'environnement
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration des variables d'environnement
Créez un fichier `.env` à la racine :
```bash
DEBUG=True
DATABASE_URL=mysql://user:password@localhost:3306/db_name
MARKETPLACE_URL=https://opensmartops.org
```

### 4. Initialisation de la base de données
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Démarrage
```bash
python manage.py runserver 0.0.0.0:8000
```

## 🏗 Subtilités techniques
- **Validation AJAX** : Le formulaire de création de tickets nécessite que les données soient POSTées avec les IDs de Bâtiment et d'Équipement valides pour le Client sélectionné.
- **Hardware Binding** : Lors du premier démarrage, un `installation_uuid` unique est généré et stocké dans `SystemConfiguration`. Il est utilisé pour authentifier l'instance auprès du portail.
- **Sync Silencieuse** : Le dashboard interroge automatiquement l'API de synchronisation (throttle de 24h) pour vérifier les mises à jour des modules.

## 📄 Licence
Propriétaire - SMARTOPS © 2026.
