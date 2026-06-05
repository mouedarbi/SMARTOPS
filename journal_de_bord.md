# Journal de Bord - Projet SMARTOPS (Core Application)

---

## [21/04/2026] - Phase 1 : Initialisation et Identité Système

### Avancement : Création du Socle Technique
- **Description** : Lancement de l'application principale SMARTOPS après validation du POC.
- **Implementation** :
    - Initialisation du projet Django `smartops_project`.
    - Création de l'application `system` pour la gestion du noyau.
    - **Identité Unique** : Implémentation du modèle `SystemConfiguration` générant un `installation_uuid` définitif dès le premier lancement.
    - **Configuration Entreprise** : Ajout des champs pour les informations de la société (Nom, Adresse, Logo, TVA).
- **Outcome** : Chaque installation SMARTOPS possède désormais une identité numérique infalsifiable.

---

## [21/04/2026] - Phase 2 : Design Dashboard Premium (Style AdminLTE)

### Avancement : Refonte de l'Interface Utilisateur
- **Description** : Création d'une interface de gestion moderne et ergonomique inspirée par AdminLTE et le style LIFTOP_OLD.
- **Implementation** :
    - Création d'un template `base.html` avec Sidebar latérale sombre (Slate-900) et header flottant.
    - Utilisation de Tailwind CSS pour un rendu "Premium".
    - **Widgets** : Affichage dynamique de l'UUID d'installation et du logo entreprise dans la navigation.
    - **Formulaires** : Stylisation complète de l'écran de configuration avec retours utilisateurs (Django Messages).
- **Outcome** : L'application dispose d'un look professionnel prêt pour la démonstration.

---

## [21/04/2026] - Phase 3 : Socle de Licensing & Hardware Binding

### Avancement : Préparation du système de Plugins
- **Description** : Mise en place de l'application `licensing` pour l'activation des modules premium.
- **Implementation** :
    - Création de l'application `licensing` et du modèle `Plugin`.
    - **Hardware Binding** : Développement du `LicenseService` capable d'envoyer l'`installation_uuid` au Portail lors de la validation.
    - **Sécurité Locale** : Ajout de contrôles pour empêcher la réinstallation ou le double usage de clés sur un même module déjà actif.
- **Outcome** : Le système est prêt pour une communication sécurisée et bidirectionnelle avec la Marketplace.

---

## [21/04/2026] - Moteur Universel "Hot-Plug" et UX Avancée

### Avancement : Architecture Modulaire Dynamique
- **Description** : Création d'un moteur capable d'injecter des applications Django entières à chaud depuis la base de données.
- **Implementation** :
    - **Pluggy** : Intégration de `plugins_system` pour la communication inter-modules via des hooks.
    - **Moteur SQL de boot** : Modification de `settings.py` pour charger `INSTALLED_APPS` via une requête SQL brute au démarrage.

### Problèmes rencontrés et Résolutions :

1. **Le problème de "l'œuf et la poule" (Chargement ORM)** :
    - **Description** : Impossible d'utiliser l'ORM Django dans `settings.py` pour lister les plugins, car Django a besoin des settings pour démarrer l'ORM.
    - **Solution** : Utilisation du module standard `sqlite3` pour lire directement le fichier `db.sqlite3` en SQL brut avant l'initialisation de Django.

2. **Échec CSRF (Conflit de ports sur localhost)** :
    - **Description** : Les formulaires SMARTOPS étaient rejetés (403 Forbidden) car les cookies de session entraient en collision avec ceux du Portail sur le même domaine (`127.0.0.1`).
    - **Solution** : Isolation des cookies via `SESSION_COOKIE_NAME` et `CSRF_COOKIE_NAME` uniques dans les réglages du projet.

3. **Boucle de redirection d'Onboarding** :
    - **Description** : La vérification trop stricte du nom de société par défaut empêchait l'accès au Dashboard même après configuration.
    - **Solution** : Refonte de la logique de redirection dans les vues et centralisation des notifications dans le layout de base pour une meilleure ergonomie.

4. **Erreurs d'imports dans les services** :
    - **Description** : `NameError: models is not defined` lors de l'appel de fonctions SQL de temps réel.
    - **Solution** : Correction des imports manquants dans `licensing/services.py`.

- **Outcome** : SMARTOPS est devenu un système totalement extensible. N'importe quel module activé en base de données s'intègre désormais de manière transparente au noyau.

---

## [21/04/2026] - Phase 4 : Cycle de Vie complet et Gestion des Erreurs

### Avancement : Moteur de gestion des modules (Install/Uninstall)
- **Description** : Implémentation du système "Hot-Unplug" pour libérer les ressources et les licences proprement.
- **Implementation** :
    - **Streaming Console** : Création d'un terminal HTTP en temps réel pour afficher les logs de `pip install` et `pip uninstall`.
    - **Libération Stricte** : Développement du protocole de libération de licence envoyant l'UUID Licence + UUID Machine au Portail.
    - **Routage de secours** : Sécurisation du fichier `urls.py` pour ignorer les modules corrompus ou supprimés sans faire planter l'application.

### Problèmes rencontrés et Résolutions :

1. **Crash "TypeError: 'module' object is not iterable"** :
    - **Description** : Django plantait au démarrage après une désinstallation.
    - **Solution** : Suppression de lignes de code orphelines (résidus de manipulations) à la fin de `licensing/views.py` et nettoyage des dossiers `__pycache__`.

2. **Échec de l'import des menus (404 sur les URLs des modules)** :
    - **Description** : Le lien apparaissait mais l'URL ne répondait pas.
    - **Cause** : Archive ZIP mal structurée (dossiers imbriqués) empêchant Django de localiser `urls.py`.
    - **Solution** : Reconstruction d'un package ZIP "FINAL" avec une structure à plat et une `TRACE_ID` pour vérification.

- **Outcome** : Le cycle de vie (Achat -> Installation -> Utilisation -> Désinstallation -> Libération) est validé à 100%. La plateforme est techniquement mature et robuste.

---

## 29 Avril 2026 - Développement Core Métier (Phase 1 & 2)

### Réalisations :
- **Architecture Core :** Intégration complète du modèle `CustomUser` (Auth, RBAC, Soft-delete) et résolution de la cohérence des migrations.
- **Application Inventaire :** 
  - Développement des modèles `Client`, `Building`, `Equipment` et `EquipmentType` (avec champs dynamiques JSONField).
  - Implémentation des vues CRUD pour les Clients, Bâtiments, Types et Équipements.
  - Tests unitaires complets pour valider la robustesse des données.
- **UI Custom Dashboard :** 
  - Intégration des liens de gestion dans la sidebar existante (Tailwind).
  - Correction des problèmes de routage (NoReverseMatch, NameError) pour assurer l'accessibilité.

### État du projet :
- Le système est stable et testé. Les fonctionnalités de base du cœur de métier sont opérationnelles.
- Git commit final effectué pour l'ensemble des fonctionnalités implémentées aujourd'hui.

---

## [29/04/2026] - Optimisation UX et Nettoyage Système

### Avancement : Amélioration du module Maintenance et Connectivité
- **Description** : Refonte de la fiche technicien et optimisation du flux de création de tickets. Nettoyage des résidus du système de plugins.
- **Implementation** :
    - **Stats Techniciens** : Ajout de calculs de performance en temps réel (taux de succès, durée moyenne).
    - **Sélection Intelligente** : Mise en place de filtres AJAX (Client > Bâtiment > Équipement) et recherche par référence/S/N dans le formulaire de ticket.
    - **Visibilité UI** : Correction des contrastes (blanc sur blanc) dans les formulaires Tailwind.
    - **Maintenance Système** : Suppression des répertoires orphelins (`tmp_plugin`, `rebuild_plugin`) et mise à jour de l'`URL Marketplace` vers la production (`https://opensmartops.org`).
- **Outcome** : Une interface plus fluide, une meilleure traçabilité des performances et un socle de plugins assaini.

## Séance du 05/06/2026

### Travaux réalisés
1.  **Évolutions Métier (Module Maintenance) :**
    *   Implémentation du nouvel état de ticket : **"À replanifier"** (`to_reschedule`).
    *   Mise à jour du workflow : Distinction entre échecs techniques temporaires et annulations définitives.
    *   Interface : Attribution de la couleur **Orange** pour l'identification visuelle immédiate des tickets à traiter en priorité.

2.  **Infrastructure & DevOps :**
    *   Mise en place de la **CI/CD via GitHub Actions** (`django_ci.yml`).
    *   Configuration des environnements de test automatisés pour Python 3.13.
    *   Stabilisation de l'environnement de développement sur **Django 6.0.4**.

3.  **Maintenance du dépôt :**
    *   Nettoyage de la racine du projet et organisation des documents techniques dans un répertoire externe.
    *   Gestion du versionnement via une branche dédiée `feat-technician-app`.

### Prochaines étapes
*   Initialisation de l'application dédiée `technician`.
*   Mise en place de l'interface mobile-first pour le personnel de terrain.

---

## Séance du 05/06/2026 (suite) - Résolution de la CI cassée (django-scheduler + tests inventaire)

### Problèmes rencontrés

#### Problème 1 — Échec de migration `0015` en CI (django-scheduler)

**Symptôme :**
```
ValueError: Found wrong number (0) of indexes for schedule_calendarrelation(content_type_id, object_id).
```
La CI GitHub Actions échouait lors de la création de la base de test (`python manage.py test`), avant même d'exécuter un seul test.

**Cause racine :**
Les migrations vendorisées de `django-scheduler` utilisaient une chaîne d'opérations incompatible avec Django 6.0 :
1. Migration `0003` et `0008` : `AlterIndexTogether` → censé créer des index non nommés en base de données.
2. Migration `0015` (générée par `makemigrations` sur Django 6.0) : `RenameIndex(old_fields=...)` → cherche ces index non nommés pour les renommer.

Or, **en Django 6.0, `AlterIndexTogether` est devenu un no-op au niveau base de données** (il ne maintient plus que l'état de migration, sans créer d'index réel). Du coup, `RenameIndex` ne trouvait aucun index à renommer (0 trouvé).

**Solution apportée :**
Remplacement du contenu de la migration `schedule/migrations/0015_rename_*.py` :
- **Avant** : 4 opérations `RenameIndex(old_fields=(...), new_name='...')` qui échouaient.
- **Après** :
  1. `SeparateDatabaseAndState` avec des `AlterIndexTogether(index_together=set())` en `state_operations` uniquement (sans toucher la DB) pour nettoyer l'état de migration.
  2. 4 opérations `AddIndex` avec des index nommés explicitement pour créer les index directement en base.

Cette approche fonctionne aussi bien sur une base fraîche (CI) que sur une base existante.

---

#### Problème 2 — 3 tests `inventory` en erreur (bug préexistant, masqué par le problème 1)

**Symptôme :**
```
ValueError: Cannot assign "'elevator'": "Equipment.equipment_type" must be a "EquipmentType" instance.
```
Après correction du problème 1, les migrations passaient mais 3 tests sur 7 échouaient dans `inventory/tests.py`.

**Cause racine :**
Dans la méthode `setUp` des tests, le champ `equipment_type` (un `ForeignKey` vers le modèle `EquipmentType`) recevait une chaîne de caractères (`"elevator"`) au lieu d'une instance du modèle. Ce bug était masqué auparavant car la CI ne dépassait jamais l'étape des migrations.

**Solution apportée :**
Correction de `inventory/tests.py` :
- Import ajouté : `from .models import ..., EquipmentType`
- Création d'une instance `EquipmentType` dans `setUp` : `self.equipment_type = EquipmentType.objects.create(name="elevator")`
- Utilisation de l'instance dans `Equipment.objects.create(equipment_type=self.equipment_type, ...)`
- Mise à jour de l'assertion `test_equipment_creation` pour comparer avec l'instance et non la chaîne.

### Résultat
```
Ran 7 tests in 1.017s
OK
```
La CI passe désormais 7/7 tests avec succès sur une base SQLite fraîche (environnement identique à GitHub Actions).

### Suite de la séance du 05/06/2026 (Application Technicien)

1.  **Phase 1 & 2 : Dashboard Mobile-First :**
    *   Initialisation de l'application Django `technician`.
    *   Mise en place d'un routage dédié (`/technician/`) indépendant du dashboard gestionnaire.
    *   Création d'une interface responsive (Tailwind CSS) avec menu hamburger et horloge temps réel.
    *   Implémentation du filtrage dynamique : Vue "Aujourd'hui" vs Vue "Semaine" (J+7) pour l'anticipation du planning.

2.  **Phase 3 : Vue Détail Intervention :**
    *   Développement d'une vue Single Page Scroll compacte pour le terrain.
    *   Intégration d'un bouton intelligent "Ouvrir dans Maps" basé sur les coordonnées du bâtiment.
    *   Mise en place d'un bouton d'action flottant (FAB) pour le démarrage de l'intervention.
    *   Sécurisation des accès : Un technicien ne peut consulter que les interventions qui lui sont personnellement assignées.

3.  **Administration :**
    *   Enregistrement du modèle `CustomUser` dans l'admin Django avec gestion des rôles (`technician`, `manager`, etc.).

### Prochaines étapes
*   Phase 4 : Implémentation de la logique de changement de statut (Démarrer / Terminer).
*   Phase 5 : Formulaire de saisie du rapport d'intervention et signature client.
