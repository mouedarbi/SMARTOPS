from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from maintenance.models import MaintenanceTicket, Technician
from inventory.models import Equipment, EquipmentType, Building, Client as CompanyClient
from datetime import timedelta

User = get_user_model()

@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class TechnicianInterventionTests(TestCase):
    def setUp(self):
        # 1. Create Technician User
        self.tech_user = User.objects.create_user(
            username='tech1',
            password='password123',
            role='technician'
        )
        # Profil is created by signal automatically
        self.tech_profile = self.tech_user.technician_profile

        # 2. Create Inventory Hierarchy
        self.client = CompanyClient.objects.create(name="Test Client")
        self.building = Building.objects.create(name="Test Building", client=self.client)
        self.eq_type = EquipmentType.objects.create(name="Test Type")
        self.equipment = Equipment.objects.create(
            name="Test Equipment",
            equipment_type=self.eq_type,
            building=self.building,
            serial_number="SN12345",
            installed_at=timezone.now().date()
        )

        # 3. Create Ticket
        self.ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            technician=self.tech_profile,
            status='planned',
            planned_start=timezone.now(),
            planned_end=timezone.now() + timedelta(hours=1)
        )

        self.client_http = HttpClient()
        self.client_http.login(username='tech1', password='password123')

    def test_start_intervention(self):
        """Test starting an intervention updates status and timestamp."""
        url = reverse('start_intervention', args=[self.ticket.id])
        response = self.client_http.get(url)
        
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, 'in_progress')
        self.assertIsNotNone(self.ticket.effective_start)
        self.assertIsNone(self.ticket.effective_end)

    def test_stop_intervention_shows_report_form(self):
        """Phase 5 : le GET sur la clôture affiche le formulaire de rapport (pas de transition)."""
        self.ticket.status = 'in_progress'
        self.ticket.effective_start = timezone.now()
        self.ticket.save()

        url = reverse('stop_intervention', args=[self.ticket.id])
        response = self.client_http.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'intervention_report')
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')  # Toujours pas clôturé

    def test_stop_intervention_with_report(self):
        """Phase 5 : le POST avec rapport clôture l'intervention et enregistre le compte rendu."""
        self.ticket.status = 'in_progress'
        self.ticket.effective_start = timezone.now()
        self.ticket.save()

        url = reverse('stop_intervention', args=[self.ticket.id])
        response = self.client_http.post(url, {
            'intervention_report': 'Remplacement du contacteur, test de fonctionnement OK.',
            'final_status': 'done',
        })

        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, 'done')
        self.assertIsNotNone(self.ticket.effective_end)
        self.assertIn('contacteur', self.ticket.intervention_report)

    def test_stop_intervention_requires_report(self):
        """Phase 5 : un rapport vide n'autorise pas la clôture."""
        self.ticket.status = 'in_progress'
        self.ticket.effective_start = timezone.now()
        self.ticket.save()

        url = reverse('stop_intervention', args=[self.ticket.id])
        response = self.client_http.post(url, {'intervention_report': '   ', 'final_status': 'done'})

        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')

    def test_stop_intervention_to_reschedule(self):
        """Phase 5 : le technicien peut clôturer en « à replanifier »."""
        self.ticket.status = 'in_progress'
        self.ticket.effective_start = timezone.now()
        self.ticket.save()

        url = reverse('stop_intervention', args=[self.ticket.id])
        self.client_http.post(url, {
            'intervention_report': 'Pièce manquante, seconde visite nécessaire.',
            'final_status': 'to_reschedule',
        })

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'to_reschedule')
        self.assertIsNotNone(self.ticket.effective_end)

    def test_cannot_start_already_done_ticket(self):
        """Test that we cannot start a ticket that is already done."""
        self.ticket.status = 'done'
        self.ticket.save()

        url = reverse('start_intervention', args=[self.ticket.id])
        self.client_http.get(url)
        
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'done') # No change

    def test_security_access(self):
        """Test that a technician cannot access/start another technician's ticket."""
        other_tech_user = User.objects.create_user(
            username='tech2',
            password='password123',
            role='technician'
        )
        other_tech_profile = other_tech_user.technician_profile
        
        other_ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            technician=other_tech_profile,
            status='planned',
            planned_start=timezone.now(),
            planned_end=timezone.now() + timedelta(hours=1)
        )

        url = reverse('start_intervention', args=[other_ticket.id])
        response = self.client_http.get(url)
        
        self.assertEqual(response.status_code, 404) # Not found because of filter in view


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class TechnicianMenuPagesTests(TestCase):
    """Pages « Historique » et « Mon Profil » du menu technicien (issue #4)."""

    def setUp(self):
        self.tech_user = User.objects.create_user(username='tech1', password='password123', role='technician', first_name='Ali')
        self.tech_profile = self.tech_user.technician_profile
        self.tech_profile.specialties = ['Electrique', 'Hydraulique']
        self.tech_profile.save()
        other_user = User.objects.create_user(username='tech2', password='password123', role='technician')
        self.other_profile = other_user.technician_profile

        company = CompanyClient.objects.create(name="Client")
        building = Building.objects.create(name="Bâtiment Nord", client=company)
        eq_type = EquipmentType.objects.create(name="Type")
        self.equipment = Equipment.objects.create(
            name="Pompe A", equipment_type=eq_type, building=building,
            serial_number="SN1", installed_at=timezone.now().date(),
        )
        now = timezone.now()
        def ticket(profile, status, days_ago):
            return MaintenanceTicket.objects.create(
                equipment=self.equipment, technician=profile, status=status,
                planned_start=now - timedelta(days=days_ago), planned_end=now - timedelta(days=days_ago) + timedelta(hours=1),
            )
        self.done = ticket(self.tech_profile, 'done', 3)
        self.canceled = ticket(self.tech_profile, 'canceled', 5)
        self.planned = ticket(self.tech_profile, 'planned', -1)
        self.in_progress = ticket(self.tech_profile, 'in_progress', 0)
        self.foreign_done = ticket(self.other_profile, 'done', 2)
        self.client_http = HttpClient()
        self.client_http.login(username='tech1', password='password123')

    def test_menu_links_point_to_real_pages(self):
        html = self.client_http.get(reverse('technician_dashboard')).content.decode()
        self.assertIn(f'href="{reverse("technician_history")}"', html)
        self.assertIn(f'href="{reverse("technician_profile")}"', html)
        self.assertNotIn('href="#"', html)

    def test_history_lists_only_own_finished_tickets(self):
        response = self.client_http.get(reverse('technician_history'))
        self.assertEqual(response.status_code, 200)
        ids = {t.id for t in response.context['page']}
        self.assertEqual(ids, {self.done.id, self.canceled.id})
        self.assertNotIn(self.foreign_done.id, ids)
        self.assertContains(response, 'Pompe A')

    def test_history_empty_state(self):
        MaintenanceTicket.objects.filter(technician=self.tech_profile).delete()
        self.assertContains(self.client_http.get(reverse('technician_history')), "Aucune intervention dans l'historique")

    def test_profile_shows_identity_specialties_and_counts(self):
        response = self.client_http.get(reverse('technician_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ali')
        self.assertContains(response, 'Hydraulique')
        self.assertEqual(response.context['stats'], {'done': 1, 'in_progress': 1, 'upcoming': 1})

    def test_pages_require_technician_login(self):
        anonymous = HttpClient()
        manager = User.objects.create_user(username='boss', password='password123', role='manager')
        manager_client = HttpClient()
        manager_client.login(username='boss', password='password123')
        for name in ('technician_history', 'technician_profile'):
            self.assertEqual(anonymous.get(reverse(name)).status_code, 302)
            self.assertEqual(manager_client.get(reverse(name)).status_code, 302)
