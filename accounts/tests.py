"""
Fichier : tests.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Tests du modèle utilisateur personnalisé (rôles et suppression logique).
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

class CustomUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='password123',
            role='technician'
        )

    def test_create_user(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.role, 'technician')
        self.assertTrue(self.user.is_active)

    def test_role_properties(self):
        self.assertTrue(self.user.is_technician)
        self.assertFalse(self.user.is_admin)
        
        self.user.role = 'admin'
        self.user.save()
        self.assertTrue(self.user.is_admin)
        self.assertFalse(self.user.is_technician)

    def test_soft_delete(self):
        self.assertFalse(self.user.is_deleted)
        self.user.soft_delete()
        self.assertTrue(self.user.is_deleted)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertLessEqual(self.user.deleted_at, timezone.now())

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser (Technicien)")


@override_settings(SECURE_SSL_REDIRECT=False)
class MyProfileTests(TestCase):
    """« Mon profil » : données du compte, nom/e-mail et mot de passe de l'utilisateur connecté."""

    def setUp(self):
        self.manager = User.objects.create_user(
            username='chef', password='Ancien-Mdp-2026', role='manager',
            first_name='Marie', last_name='Durand', email='marie@example.com',
        )
        self.client.force_login(self.manager)

    def test_initials(self):
        self.assertEqual(self.manager.initials, 'MD')
        self.assertEqual(User(username='bob').initials, 'BO')

    def test_profile_page_shows_account(self):
        r = self.client.get(reverse('my_profile'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '@chef')
        self.assertContains(r, 'marie@example.com')
        self.assertContains(r, 'Gestionnaire')
        # En-tête : avatar aux initiales, menu avec le profil et la déconnexion.
        self.assertContains(r, 'id="user-menu"')
        self.assertContains(r, '>MD</span>')
        self.assertContains(r, reverse('logout'))

    def test_update_own_details_only(self):
        r = self.client.post(reverse('my_profile'), {
            'action': 'profile', 'first_name': 'Marie-Anne', 'last_name': 'Durand',
            'email': 'ma@example.com', 'language': 'fr', 'role': 'admin', 'username': 'pirate',
        })
        self.assertRedirects(r, reverse('my_profile'))
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.first_name, 'Marie-Anne')
        self.assertEqual(self.manager.email, 'ma@example.com')
        # Le rôle et l'identifiant ne se changent pas depuis son propre profil.
        self.assertEqual(self.manager.role, 'manager')
        self.assertEqual(self.manager.username, 'chef')

    def test_change_password_keeps_session(self):
        r = self.client.post(reverse('my_profile'), {
            'action': 'password', 'old_password': 'Ancien-Mdp-2026',
            'new_password1': 'Nouveau-Mdp-2026!', 'new_password2': 'Nouveau-Mdp-2026!',
        })
        self.assertRedirects(r, reverse('my_profile'))
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.check_password('Nouveau-Mdp-2026!'))
        self.assertEqual(self.client.get(reverse('my_profile')).status_code, 200)

    def test_wrong_old_password_is_refused(self):
        r = self.client.post(reverse('my_profile'), {
            'action': 'password', 'old_password': 'faux',
            'new_password1': 'Nouveau-Mdp-2026!', 'new_password2': 'Nouveau-Mdp-2026!',
        })
        self.assertEqual(r.status_code, 200)
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.check_password('Ancien-Mdp-2026'))

    def test_technician_is_sent_to_field_profile(self):
        tech = User.objects.create_user(username='tech_p', password='x', role='technician')
        self.client.force_login(tech)
        r = self.client.get(reverse('my_profile'))
        self.assertRedirects(r, reverse('technician_profile'), fetch_redirect_response=False)

    def test_menu_sections(self):
        """Opérations toujours ouverte (non repliable) ; les autres sections sont repliables, ouvertes par défaut."""
        r = self.client.get(reverse('ticket_list'))
        self.assertNotContains(r, 'data-section="operations"')
        self.assertContains(r, 'data-section="referentiel" open>')
        self.assertContains(r, 'data-section="parametres" open>')
        r = self.client.get(reverse('equipment_type_list'))
        self.assertContains(r, 'data-section="parametres" open data-active>')


@override_settings(SECURE_SSL_REDIRECT=False)
class UserLanguageTests(TestCase):
    """Langue de l'interface : celle du profil de l'utilisateur, le français sans connexion."""

    def setUp(self):
        self.manager = User.objects.create_user(username='chef_nl', password='x', role='manager', language='nl')

    def test_user_language_is_active(self):
        self.client.force_login(self.manager)
        r = self.client.get(reverse('my_profile'))
        self.assertEqual(r.headers['Content-Language'], 'nl')
        self.assertContains(r, '<html lang="nl">')
        # Pas de fuite : la langue par défaut est rétablie après la requête.
        from django.utils import translation
        self.assertEqual(translation.get_language(), 'fr')

    def test_anonymous_pages_are_in_french(self):
        r = self.client.get(reverse('login'))
        self.assertEqual(r.headers['Content-Language'], 'fr')

    def test_anonymous_pages_follow_the_browser_language(self):
        """Sans connexion : langue du navigateur (FR / NL / EN), français si elle n'est pas proposée."""
        for header, language, text in (('nl-BE,nl;q=0.9', 'nl', 'Beveiligde beheerconsole'),
                                       ('en-GB,en;q=0.9', 'en', 'Secure administration console'),
                                       ('de-DE,de;q=0.9', 'fr', "Console d'administration sécurisée")):
            r = self.client.get(reverse('login'), HTTP_ACCEPT_LANGUAGE=header)
            self.assertEqual(r.headers['Content-Language'], language)
            self.assertContains(r, text)
            self.assertIn('Accept-Language', r.headers['Vary'])
        r = self.client.post(reverse('login'), {'username': 'x', 'password': 'y'}, HTTP_ACCEPT_LANGUAGE='nl')
        self.assertContains(r, 'Onjuiste gebruikersnaam of wachtwoord.')
        r = self.client.post(reverse('technician_login'), {'username': 'x', 'password': 'y'}, HTTP_ACCEPT_LANGUAGE='en')
        self.assertContains(r, 'Incorrect credentials.')

    def test_password_change_message_is_translated(self):
        self.manager.set_password('Ancien-Mdp-2026')
        self.manager.save()
        self.client.force_login(self.manager)
        r = self.client.post(reverse('my_profile'), {
            'action': 'password', 'old_password': 'Ancien-Mdp-2026',
            'new_password1': 'Nouveau-Mdp-2026!', 'new_password2': 'Nouveau-Mdp-2026!'}, follow=True)
        self.assertContains(r, 'Wachtwoord gewijzigd.')

    def test_language_is_changed_from_the_profile(self):
        self.client.force_login(self.manager)
        self.client.post(reverse('my_profile'), {'action': 'profile', 'first_name': '', 'last_name': '',
                                                 'email': '', 'language': 'en'})
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.language, 'en')
        self.assertEqual(self.client.get(reverse('my_profile')).headers['Content-Language'], 'en')

    def test_layout_and_profile_are_translated(self):
        """Étape 1 : menu, en-tête, menu utilisateur et « Mon profil » en FR / NL / EN."""
        expected = {
            'fr': ('Mon profil', 'Équipements', 'Déconnexion', 'Mes informations', 'Gestionnaire'),
            'nl': ('Mijn profiel', 'Toestellen', 'Afmelden', 'Mijn gegevens', 'Planner'),
            'en': ('My profile', 'Equipment', 'Log out', 'My details', 'Manager'),
        }
        self.client.force_login(self.manager)
        for language, texts in expected.items():
            self.manager.language = language
            self.manager.save()
            r = self.client.get(reverse('my_profile'))
            for text in texts:
                self.assertContains(r, text, msg_prefix=language)

    def test_settings_screens_are_translated(self):
        """Étape 9 : société, utilisateurs et modules en FR / NL / EN."""
        from system.models import SystemConfiguration
        config = SystemConfiguration.get_instance()
        config.company_name = 'Demo'
        config.save()
        admin = User.objects.create_user(username='admin_i18n', password='x', role='admin')
        self.client.force_login(admin)
        expected = {
            'system_config': {'fr': 'Informations de l&#x27;Entreprise', 'nl': 'Bedrijfsgegevens', 'en': 'Company details'},
            'user_list': {'fr': 'Nouvel Utilisateur', 'nl': 'Nieuwe gebruiker', 'en': 'New user'},
            'plugin_list': {'fr': 'Activer un nouveau module', 'nl': 'Een nieuwe module activeren', 'en': 'Activate a new module'},
        }
        for url_name, texts in expected.items():
            for language, text in texts.items():
                admin.language = language
                admin.save()
                response = self.client.get(reverse(url_name))
                self.assertContains(response, text.replace('&#x27;', "'"), msg_prefix=f'{language} {url_name}')
