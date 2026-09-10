"""
Fichier : tests.py
Application : maintenance
Auteur : Mohamed Ouedarbi
Description : Tests unitaires du modèle MaintenanceTicket et des contraintes d'intégrité temporelle.
"""

from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import timedelta, date

from accounts.models import CustomUser
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician, MaintenanceTicket


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class MaintenanceTicketModelTestCase(TestCase):
    def setUp(self):
        self.user_tech = CustomUser.objects.create_user(
            username='tech_test',
            password='testpass123',
            role='technician'
        )
        self.tech_profile = self.user_tech.technician_profile

        self.client_obj = Client.objects.create(
            name='Test Client Corp',
            address='10 Rue du Test',
            contact_name='Alice Dupont',
            email='alice@testcorp.be'
        )
        self.building = Building.objects.create(
            client=self.client_obj,
            name='Bâtiment Principal',
            address='10 Rue du Test'
        )
        self.eq_type = EquipmentType.objects.create(name='Ascenseur')
        self.equipment = Equipment.objects.create(
            building=self.building,
            name='Ascenseur Nord',
            equipment_type=self.eq_type,
            serial_number='SN-ASC-001',
            installed_at=date(2025, 1, 15)
        )

    def test_ticket_creation_and_status_transitions(self):
        """Vérifie la création nominale et la transition des statuts d'un ticket."""
        now = timezone.now()
        ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            technician=self.tech_profile,
            type='maintenance',
            planned_start=now,
            planned_end=now + timedelta(hours=2),
            status='pending'
        )
        self.assertEqual(ticket.status, 'pending')

        # Transition: planned
        ticket.status = 'planned'
        ticket.save()
        self.assertEqual(ticket.status, 'planned')

        # Transition: in_progress avec horodatage de début
        ticket.status = 'in_progress'
        ticket.effective_start = now + timedelta(minutes=5)
        ticket.save()
        self.assertEqual(ticket.status, 'in_progress')

        # Transition: done avec rapport et horodatage de fin
        ticket.status = 'done'
        ticket.effective_end = now + timedelta(hours=1, minutes=30)
        ticket.intervention_report = "Intervention terminée avec succès."
        ticket.full_clean()
        ticket.save()
        self.assertEqual(ticket.status, 'done')

    def test_planned_end_before_planned_start_validation_and_constraint(self):
        """Vérifie que planned_end <= planned_start est rejeté par clean() et par la base de données."""
        now = timezone.now()
        ticket = MaintenanceTicket(
            equipment=self.equipment,
            technician=self.tech_profile,
            planned_start=now,
            planned_end=now - timedelta(minutes=30),
            status='planned'
        )

        # 1. Validation applicative via clean()
        with self.assertRaises(ValidationError):
            ticket.clean()

        # 2. Contrainte d'intégrité DB (CheckConstraint)
        with self.assertRaises(IntegrityError):
            MaintenanceTicket.objects.create(
                equipment=self.equipment,
                technician=self.tech_profile,
                planned_start=now,
                planned_end=now - timedelta(hours=1),
                status='planned'
            )

    def test_effective_end_before_effective_start_validation_and_constraint(self):
        """Vérifie que effective_end <= effective_start est rejeté par clean() et par la base de données."""
        now = timezone.now()
        ticket = MaintenanceTicket(
            equipment=self.equipment,
            technician=self.tech_profile,
            planned_start=now,
            planned_end=now + timedelta(hours=2),
            effective_start=now + timedelta(minutes=10),
            effective_end=now - timedelta(minutes=5),
            status='in_progress'
        )

        # 1. Validation applicative via clean()
        with self.assertRaises(ValidationError):
            ticket.clean()

        # 2. Contrainte d'intégrité DB (CheckConstraint)
        with self.assertRaises(IntegrityError):
            MaintenanceTicket.objects.create(
                equipment=self.equipment,
                technician=self.tech_profile,
                planned_start=now,
                planned_end=now + timedelta(hours=2),
                effective_start=now + timedelta(minutes=10),
                effective_end=now - timedelta(minutes=5),
                status='in_progress'
            )


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class MaintenanceWebViewsTestCase(TestCase):
    def setUp(self):
        self.manager = CustomUser.objects.create_user(
            username='manager_maint',
            password='Password123!',
            role='manager'
        )
        self.tech1_user = CustomUser.objects.create_user(
            username='tech_1',
            password='Password123!',
            role='technician'
        )
        self.tech1 = self.tech1_user.technician_profile

        self.tech2_user = CustomUser.objects.create_user(
            username='tech_2',
            password='Password123!',
            role='technician'
        )
        self.tech2 = self.tech2_user.technician_profile

        self.client_obj = Client.objects.create(name='Client Test SA', address='1 rue Test')
        self.building = Building.objects.create(client=self.client_obj, name='Batiment A', address='1 rue Test')
        self.eq_type = EquipmentType.objects.create(name='Pompe à chaleur')
        self.equipment = Equipment.objects.create(
            building=self.building,
            name='PAC 01',
            equipment_type=self.eq_type,
            serial_number='PAC-999',
            installed_at=date(2025, 2, 1)
        )
        self.http_client = HttpClient()
        self.http_client.login(username='manager_maint', password='Password123!')

    def test_ticket_create_view_post_by_manager(self):
        """F5 : Test de création réelle d'un ticket par un gestionnaire via le formulaire Web."""
        url = reverse('ticket_create')
        data = {
            'client': self.client_obj.id,
            'building': self.building.id,
            'equipment': self.equipment.id,
            'technician': self.tech1.id,
            'type': 'maintenance',
            'status': 'planned',
            'planned_date': '2026-09-15',
            'start_time_slot': '10:00',
            'duration_seconds': 7200,
            'description': 'Maintenance préventive semestrielle.'
        }
        response = self.http_client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Vérification en base
        ticket = MaintenanceTicket.objects.filter(description__contains='Maintenance préventive semestrielle').first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.equipment, self.equipment)
        self.assertEqual(ticket.technician, self.tech1)
        self.assertEqual(ticket.status, 'planned')
        local_start = timezone.localtime(ticket.planned_start)
        local_end = timezone.localtime(ticket.planned_end)
        self.assertEqual(local_start.strftime('%Y-%m-%d %H:%M'), '2026-09-15 10:00')
        self.assertEqual(local_end.strftime('%Y-%m-%d %H:%M'), '2026-09-15 12:00')

    def test_ticket_update_view_reassign_technician_and_reschedule(self):
        """F6 : Test de réaffectation d'un technicien et replanification d'un ticket existant."""
        now = timezone.now()
        ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            technician=self.tech1,
            type='repair',
            status='pending',
            planned_start=now,
            planned_end=now + timedelta(hours=1),
            description='Dépannage PAC'
        )

        url = reverse('ticket_update', kwargs={'pk': ticket.id})
        data = {
            'client': self.client_obj.id,
            'building': self.building.id,
            'equipment': self.equipment.id,
            'technician': self.tech2.id,  # Réaffectation à tech2
            'type': 'repair',
            'status': 'planned',
            'planned_date': '2026-09-20',
            'start_time_slot': '14:00',
            'duration_seconds': 3600,
            'description': 'Dépannage PAC réaffecté.'
        }
        response = self.http_client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        ticket.refresh_from_db()
        self.assertEqual(ticket.technician, self.tech2)  # Nouveau technicien bien affecté
        self.assertEqual(ticket.status, 'planned')
        local_start = timezone.localtime(ticket.planned_start)
        self.assertEqual(local_start.strftime('%Y-%m-%d %H:%M'), '2026-09-20 14:00')

    def test_ticket_update_locked_when_in_progress(self):
        """Sécurité : Vérifie le verrouillage d'édition si l'intervention est en cours."""
        now = timezone.now()
        ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            technician=self.tech1,
            type='repair',
            status='in_progress',
            planned_start=now,
            planned_end=now + timedelta(hours=1),
            effective_start=now,
            description='En cours'
        )
        url = reverse('ticket_update', kwargs={'pk': ticket.id})
        response = self.http_client.get(url, follow=True)
        self.assertRedirects(response, reverse('ticket_detail', kwargs={'pk': ticket.id}))


def _tiny_png(name='photo.png'):
    """Retourne un fichier PNG 1x1 valide pour les tests d'upload."""
    import io
    from django.core.files.uploadedfile import SimpleUploadedFile
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (1, 1), '#3b82f6').save(buf, format='PNG')
        content = buf.getvalue()
    except Exception:
        content = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                   b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00'
                   b'\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82')
    return SimpleUploadedFile(name, content, content_type='image/png')


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    MEDIA_ROOT='/tmp/smartops_test_media',
)
class InterventionPhotoTestCase(TestCase):
    def setUp(self):
        from accounts.models import CustomUser
        self.manager = CustomUser.objects.create_user(username='mgr_photo', password='Password123!', role='manager')
        self.tech_user = CustomUser.objects.create_user(username='tech_photo', password='Password123!', role='technician')
        self.tech = self.tech_user.technician_profile
        self.client_obj = Client.objects.create(name='Client Photo', address='1 rue')
        self.building = Building.objects.create(client=self.client_obj, name='Bat P', address='1 rue')
        self.eq_type = EquipmentType.objects.create(name='Chaudière')
        self.equipment = Equipment.objects.create(
            building=self.building, name='CH 1', equipment_type=self.eq_type,
            serial_number='CH-1', installed_at=date(2025, 1, 1),
        )
        now = timezone.now()
        self.ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech, type='maintenance',
            status='in_progress', planned_start=now, planned_end=now + timedelta(hours=2),
            effective_start=now,
        )

    def test_manager_can_upload_and_delete_photo(self):
        http = HttpClient()
        http.login(username='mgr_photo', password='Password123!')
        url = reverse('ticket_detail', kwargs={'pk': self.ticket.id})

        resp = http.post(url, {'action': 'add_photo', 'phase': 'after', 'caption': 'Test',
                               'image': _tiny_png()})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.ticket.photos.count(), 1)
        photo = self.ticket.photos.first()
        self.assertEqual(photo.phase, 'after')
        self.assertEqual(photo.uploaded_by, self.manager)

        resp = http.post(url, {'action': 'delete_photo', 'photo_id': photo.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.ticket.photos.count(), 0)

    def test_technician_uploads_photo_on_own_ticket(self):
        http = HttpClient()
        http.login(username='tech_photo', password='Password123!')
        url = reverse('technician_ticket_detail', kwargs={'pk': self.ticket.id})

        resp = http.post(url, {'action': 'add_photo', 'phase': 'during', 'image': _tiny_png()})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.ticket.photos.count(), 1)
        self.assertEqual(self.ticket.photos.first().uploaded_by, self.tech_user)

    def tearDown(self):
        import shutil
        shutil.rmtree('/tmp/smartops_test_media', ignore_errors=True)

