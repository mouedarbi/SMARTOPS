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
