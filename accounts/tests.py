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
            'email': 'ma@example.com', 'role': 'admin', 'username': 'pirate',
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
