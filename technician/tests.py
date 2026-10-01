from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from maintenance.models import MaintenanceTicket, Technician, InterventionPhoto
from inventory.models import Equipment, EquipmentType, Building, Client as CompanyClient
from datetime import timedelta, datetime, timezone as dt_timezone
from unittest import mock
import zoneinfo
from decimal import Decimal
import os
import shutil
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

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
        response = self.client_http.post(url)
        
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, 'in_progress')
        self.assertIsNotNone(self.ticket.effective_start)
        self.assertIsNone(self.ticket.effective_end)

    def test_start_intervention_requires_post(self):
        """Une simple requête GET ne démarre pas l'intervention."""
        response = self.client_http.get(reverse('start_intervention', args=[self.ticket.id]))

        self.assertEqual(response.status_code, 405)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'planned')

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
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()
        self.assertEqual(follow_up.status, 'pending')
        self.assertIsNone(follow_up.technician)

    def test_today_uses_local_time_zone(self):
        """« Aujourd'hui » suit le fuseau local : à 00:30 (Paris), la veille au soir n'en fait plus partie."""
        paris = zoneinfo.ZoneInfo('Europe/Paris')
        fake_now = datetime(2026, 7, 10, 0, 30, tzinfo=paris).astimezone(dt_timezone.utc)
        self.ticket.planned_start = datetime(2026, 7, 10, 8, 0, tzinfo=paris)
        self.ticket.planned_end = self.ticket.planned_start + timedelta(hours=1)
        self.ticket.save()
        yesterday = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech_profile, status='planned',
            planned_start=datetime(2026, 7, 9, 20, 0, tzinfo=paris),
            planned_end=datetime(2026, 7, 9, 21, 0, tzinfo=paris),
        )

        with mock.patch('django.utils.timezone.now', return_value=fake_now):
            response = self.client_http.get(reverse('technician_dashboard'))

        today = list(response.context['tickets_today'])
        self.assertIn(self.ticket, today)
        self.assertNotIn(yesterday, today)

    def test_rescheduled_ticket_cannot_be_started(self):
        """Un ticket « à replanifier » est clôturé : seul le ticket de suite pourra être démarré."""
        self.ticket.status = 'to_reschedule'
        self.ticket.save()

        self.client_http.post(reverse('start_intervention', args=[self.ticket.id]))

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'to_reschedule')
        detail = self.client_http.get(reverse('technician_ticket_detail', args=[self.ticket.id]))
        self.assertNotContains(detail, 'id="start-intervention-form"')

    def test_cannot_start_already_done_ticket(self):
        """Test that we cannot start a ticket that is already done."""
        self.ticket.status = 'done'
        self.ticket.save()

        url = reverse('start_intervention', args=[self.ticket.id])
        self.client_http.post(url)
        
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
        response = self.client_http.post(url)
        
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

    def test_dashboard_lists_overdue_unclosed_tickets(self):
        """Une intervention non clôturée d'un jour précédent reste visible dans le planning (issue #16)."""
        now = timezone.now()
        overdue = {}
        for status in ('pending', 'planned', 'in_progress', 'done', 'to_reschedule', 'canceled'):
            overdue[status] = MaintenanceTicket.objects.create(
                equipment=self.equipment, technician=self.tech_profile, status=status,
                planned_start=now - timedelta(days=2), planned_end=now - timedelta(days=2) + timedelta(hours=1),
            )

        response = self.client_http.get(reverse('technician_dashboard'))
        listed = list(response.context['tickets_overdue'])
        for status in ('pending', 'planned', 'in_progress'):
            self.assertIn(overdue[status], listed)
        for status in ('done', 'to_reschedule', 'canceled'):
            self.assertNotIn(overdue[status], listed)
        self.assertNotIn(self.planned, listed)  # demain : pas en retard
        self.assertContains(response, 'En retard')

    def test_ticket_done_ahead_of_schedule_is_dated_by_effective_start(self):
        """Prévue demain mais réalisée aujourd'hui : datée du jour réel (issue #18)."""
        now = timezone.now()
        early = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech_profile, status='done',
            planned_start=now + timedelta(days=1), planned_end=now + timedelta(days=1, hours=1),
            effective_start=now - timedelta(minutes=50), effective_end=now - timedelta(minutes=10),
        )

        dashboard = self.client_http.get(reverse('technician_dashboard'))
        self.assertIn(early, list(dashboard.context['tickets_today']))
        self.assertContains(dashboard, timezone.localtime(early.effective_start).strftime('%H:%M'))

        history = self.client_http.get(reverse('technician_history'))
        tickets = list(history.context['page'].object_list)
        self.assertEqual(tickets[0], early)  # le plus récent en date effective

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


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class RescheduleFollowUpTests(TestCase):
    """Clôture « à replanifier » : le ticket est conservé et un ticket de suite est créé (issue #15)."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.tech_user = User.objects.create_user(username='tech1', password='password123', role='technician')
        self.tech_profile = self.tech_user.technician_profile
        company = CompanyClient.objects.create(name="Client")
        building = Building.objects.create(name="Bâtiment Nord", client=company)
        eq_type = EquipmentType.objects.create(name="Type")
        self.equipment = Equipment.objects.create(
            name="Pompe A", equipment_type=eq_type, building=building,
            serial_number="SN1", installed_at=timezone.now().date(),
        )
        now = timezone.now()
        self.ticket = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech_profile, type='repair',
            status='in_progress', description="Fuite sur la vanne",
            planned_start=now - timedelta(hours=1), planned_end=now + timedelta(hours=1),
            effective_start=now - timedelta(minutes=30),
            start_latitude=Decimal('50.850000'), start_longitude=Decimal('4.350000'),
        )
        self.photo = InterventionPhoto.objects.create(
            ticket=self.ticket, caption="Vanne", phase='before', uploaded_by=self.tech_user,
            image=SimpleUploadedFile('vanne.jpg', b'photo-bytes', content_type='image/jpeg'),
        )
        self.client_http = HttpClient()
        self.client_http.login(username='tech1', password='password123')

    def close_to_reschedule(self):
        return self.client_http.post(reverse('stop_intervention', args=[self.ticket.id]), {
            'intervention_report': 'Pièce manquante.',
            'final_status': 'to_reschedule',
        })

    def test_original_ticket_keeps_field_data(self):
        self.close_to_reschedule()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'to_reschedule')
        self.assertIsNotNone(self.ticket.effective_start)
        self.assertIsNotNone(self.ticket.effective_end)
        self.assertEqual(self.ticket.start_latitude, Decimal('50.850000'))
        self.assertEqual(self.ticket.intervention_report, 'Pièce manquante.')
        self.assertEqual(self.ticket.photos.count(), 1)

    def test_follow_up_ticket_goes_back_to_dispatching(self):
        self.close_to_reschedule()
        self.ticket.refresh_from_db()
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()

        self.assertEqual(follow_up.status, 'pending')
        self.assertIsNone(follow_up.technician)
        self.assertEqual(follow_up.equipment, self.equipment)
        self.assertEqual(follow_up.type, 'repair')
        self.assertIsNone(follow_up.effective_start)
        self.assertIsNone(follow_up.effective_end)
        self.assertIsNone(follow_up.start_latitude)
        self.assertIn(f"Suite de l'intervention #{self.ticket.id}", follow_up.description)
        self.assertIn("Fuite sur la vanne", follow_up.description)
        self.assertIn("Pièce manquante.", follow_up.description)
        self.assertIn(f"ticket #{follow_up.id}", self.ticket.description)

    def test_photos_are_copied_to_their_own_files(self):
        self.close_to_reschedule()
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()
        copy = follow_up.photos.get()

        self.assertNotEqual(copy.image.name, self.photo.image.name)
        self.assertEqual((copy.caption, copy.phase, copy.uploaded_by), ("Vanne", 'before', self.tech_user))
        copy.delete()
        self.assertTrue(os.path.exists(self.photo.image.path))

    def test_follow_up_can_be_started_once_dispatched(self):
        self.close_to_reschedule()
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()
        follow_up.technician = self.tech_profile
        follow_up.status = 'planned'
        follow_up.save()

        self.client_http.post(reverse('start_intervention', args=[follow_up.id]))
        follow_up.refresh_from_db()
        self.assertEqual(follow_up.status, 'in_progress')

    def test_description_links_only_to_own_tickets(self):
        self.close_to_reschedule()
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()
        html = self.client_http.get(reverse('technician_ticket_detail', args=[self.ticket.id])).content.decode()
        # Le ticket de suite n'est pas encore attribué : pas de lien
        self.assertNotIn(reverse('technician_ticket_detail', args=[follow_up.id]), html)

        follow_up.technician = self.tech_profile
        follow_up.save()
        html = self.client_http.get(reverse('technician_ticket_detail', args=[follow_up.id])).content.decode()
        self.assertIn(f'href="{reverse("technician_ticket_detail", args=[self.ticket.id])}"', html)

    def test_manager_cannot_edit_rescheduled_ticket(self):
        self.close_to_reschedule()
        manager = User.objects.create_user(username='mgr', password='password123', role='manager')
        self.client_http.force_login(manager)
        response = self.client_http.get(reverse('ticket_update', args=[self.ticket.id]))
        self.assertRedirects(response, reverse('ticket_detail', args=[self.ticket.id]))
