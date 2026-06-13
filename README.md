# SMARTOPS — Plateforme de Maintenance Technique (GMAO)

![Version](https://img.shields.io/badge/version-0.1.0--alpha-orange)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Django](https://img.shields.io/badge/django-6.0%2B-green)
![Status](https://img.shields.io/badge/status-alpha-red)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)

SMARTOPS est une solution de gestion de maintenance (GMAO) de niveau entreprise, conçue pour être transversale, hautement configurable et auto-hébergeable. Elle permet aux entreprises de piloter l'ensemble de leur cycle de vie technique, de l'inventaire des équipements jusqu'à la traçabilité des interventions.

---

## Version Alpha — v0.1.0

> **Cette version est une release Alpha (MVP).** Les fonctionnalités de base sont opérationnelles. Certaines fonctionnalités avancées sont en cours de développement (voir Roadmap).

### Fonctionnalités disponibles dans cette version

| Module | Fonctionnalité | Statut |
|---|---|---|
| **Authentification** | Connexion / Déconnexion | ✅ Opérationnel |
| **Comptes** | Gestion des utilisateurs (création, édition, suppression logique) | ✅ Opérationnel |
| **Comptes** | Rôles : Admin, Manager, Technicien, Consultant | ✅ Opérationnel |
| **Inventaire** | Gestion des Clients B2B | ✅ Opérationnel |
| **Inventaire** | Gestion des Bâtiments par client | ✅ Opérationnel |
| **Inventaire** | Gestion des Équipements avec champs personnalisés (JSON) | ✅ Opérationnel |
| **Maintenance** | Création et suivi des tickets d'intervention | ✅ Opérationnel |
| **Maintenance** | Workflow complet : Ouvert → En cours → Résolu → Clôturé | ✅ Opérationnel |
| **Planning** | Calendrier des interventions (FullCalendar) | ✅ Opérationnel |
| **Planning** | Récurrences automatiques (hebdo, mensuel, trimestriel) | 🔜 v0.2.0 |
| **Technicien** | Interface mobile-first pour les techniciens terrain | ✅ Opérationnel |
| **Licensing** | Système de plugins avec Hardware Binding (UUID machine) | ✅ Opérationnel |
| **REST API** | Endpoints pour application mobile | 🔜 v0.2.0 |
| **API Docs** | Documentation Swagger / OpenAPI | 🔜 v0.2.0 |

### Limitations connues (Alpha)

- Pas d'inscription publique — les comptes sont créés par l'administrateur (système B2B)
- L'API REST n'est pas encore disponible (prévue v0.2.0)
- Le portail Marketplace est un service séparé (SMARTOPS Portal)

---

## Architecture Système

SMARTOPS repose sur une architecture **hybride** :

- **Application Core (Auto-hébergée)** : Le moteur métier fonctionne en local sur le serveur du client, garantissant une souveraineté totale sur les données (RGPD).
- **Portail Marketplace (Cloud)** : Un portail centralisé gère le cycle de vie des licences, l'activation des modules Premium et les mises à jour, via une authentification sécurisée par `Hardware Binding` (UUID unique par machine).

## Modules et Fonctionnalités

- **Gestion du Patrimoine** : Inventaire dynamique des Clients, Bâtiments et Équipements avec champs personnalisés (JSON).
- **Maintenance Avancée** : Workflow complet de tickets (Priorités, Types, État), historisation technique et traçabilité des interventions.
- **Planning** : Calendrier des interventions avec intégration FullCalendar. Récurrences prévues en v0.2.0.
- **Interface Technicien** : Dashboard mobile-first avec vue journalière/hebdomadaire et intégration maps.
- **Moteur de Plugins** : Système `Pluggy` permettant d'injecter de la logique métier sans modifier le cœur du système.
- **Licensing Intelligent** : Verrouillage par UUID machine pour la protection de la propriété intellectuelle.

---

## Prérequis Techniques

- **Runtime** : Python 3.13+, Django 6.0+
- **Base de données** : MySQL 8.0+
- **Environnement** : Virtualenv

## Installation

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

Créez un fichier `.env` à la racine (voir `.env.example`) :

```ini
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=mysql://user:password@localhost:3306/smartops_db
MARKETPLACE_URL=https://opensmartops.org
```

### 4. Initialisation

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

---

## Subtilités Architecturales

- **Hardware Binding** : Le système génère un UUID unique au premier lancement (`SystemConfiguration`). Il est immuable et obligatoire pour toute communication avec le portail Marketplace.
- **Sync Silencieuse** : Le dashboard interroge le portail via une API non-bloquante avec un throttle de 24h pour vérifier les mises à jour.
- **Auto-Installation** : Le système télécharge les archives des modules Premium, les installe dans le virtualenv et exécute les migrations automatiquement.
- **Routage Dynamique** : Les modules hot-plug sont détectés et routés automatiquement via `INSTALLED_APPS`.

---

## Roadmap

| Version | Objectif |
|---|---|
| `v0.1.0-alpha` | MVP — Authentification, Inventaire, Maintenance, Planning, Technicien |
| `v0.2.0` | REST API (DRF) + Documentation Swagger/OpenAPI pour app mobile |
| `v0.3.0` | Notifications temps réel, rapports PDF |
| `v1.0.0` | Release stable — production-ready |

---

## Changelog

### v0.1.0-alpha — 2026-06-10
- Authentification complète (login/logout, rôles)
- Gestion des utilisateurs avec suppression logique
- Inventaire : Clients, Bâtiments, Équipements avec champs dynamiques
- Tickets de maintenance avec workflow complet
- Calendrier des interventions (FullCalendar)
- Interface technicien mobile-first (dashboard journalier/hebdomadaire)
- Système de licensing avec Hardware Binding
- Moteur de plugins hot-plug
- CI/CD via GitHub Actions

---

## Licence

Propriétaire — SMARTOPS © 2026 — Mohamed Ouedarbi
