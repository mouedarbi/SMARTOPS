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
