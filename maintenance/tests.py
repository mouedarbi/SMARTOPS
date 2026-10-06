"""
Fichier : tests.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
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

    def test_ticket_form_builds_options_as_text(self):
        """Les noms de lieux reçus en JSON sont insérés comme texte (new Option), jamais comme HTML."""
        response = self.http_client.get(reverse('ticket_create'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('buildingSelect.add(new Option(b.name, b.id))', html)
        self.assertNotIn('${b.name}', html)

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

    def test_export_pdf_button_prints_and_layout_has_print_stylesheet(self):
        """Le bouton « Exporter PDF » déclenche l'impression ; la mise en page masque menu et en-tête (issue #5)."""
        http = HttpClient()
        http.login(username='mgr_photo', password='Password123!')
        html = http.get(reverse('ticket_detail', kwargs={'pk': self.ticket.id})).content.decode()
        button = html[html.index('Exporter PDF') - 600:html.index('Exporter PDF')]
        self.assertIn('window.print()', button)
        self.assertIn('@media print', html)
        self.assertIn('app-sidebar', html)
        self.assertIn('no-print', html)

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

    def test_detail_timeline_reflects_lifecycle(self):
        """L'onglet Historique liste les évènements clés dérivés des horodatages."""
        self.ticket.effective_end = timezone.now() + timedelta(hours=1)
        self.ticket.status = 'done'
        self.ticket.save()

        http = HttpClient()
        http.login(username='mgr_photo', password='Password123!')
        resp = http.get(reverse('ticket_detail', kwargs={'pk': self.ticket.id}))
        self.assertEqual(resp.status_code, 200)
        timeline = resp.context['timeline']
        labels = [e['label'] for e in timeline]
        self.assertIn("Ticket créé", labels)
        self.assertIn("Démarrage terrain", labels)
        self.assertIn("Clôture terrain", labels)
        # Ordre chronologique
        self.assertEqual([e['at'] for e in timeline], sorted(e['at'] for e in timeline))

    def test_technician_uploads_photo_on_own_ticket(self):
        http = HttpClient()
        http.login(username='tech_photo', password='Password123!')
        url = reverse('technician_ticket_detail', kwargs={'pk': self.ticket.id})

        resp = http.post(url, {'action': 'add_photo', 'phase': 'during', 'image': _tiny_png()})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.ticket.photos.count(), 1)
        self.assertEqual(self.ticket.photos.first().uploaded_by, self.tech_user)

    def test_upload_rejects_non_image_files(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        tech = HttpClient()
        tech.login(username='tech_photo', password='Password123!')
        manager = HttpClient()
        manager.force_login(self.manager)
        for http, url_name in ((tech, 'technician_ticket_detail'), (manager, 'ticket_detail')):
            fake = SimpleUploadedFile('photo.jpg', b'not an image', content_type='image/jpeg')
            http.post(reverse(url_name, kwargs={'pk': self.ticket.id}),
                      {'action': 'add_photo', 'phase': 'during', 'image': fake})
        self.assertEqual(self.ticket.photos.count(), 0)

    def tearDown(self):
        import shutil
        shutil.rmtree('/tmp/smartops_test_media', ignore_errors=True)



@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class TicketListSectionsTestCase(TestCase):
    """Liste des interventions : à replanifier, du jour, puis toutes les autres."""

    def setUp(self):
        from maintenance.services import reschedule_ticket
        CustomUser.objects.create_user(username='chef', password='Password123!', role='manager')
        self.tech = CustomUser.objects.create_user(username='tech_s', password='Password123!', role='technician').technician_profile
        client = Client.objects.create(name='Client S', address='1 rue S')
        building = Building.objects.create(client=client, name='Site S', address='1 rue S')
        self.equipment = Equipment.objects.create(
            building=building, name='Chaudière', equipment_type=EquipmentType.objects.create(name='Chaudière'),
            serial_number='CH-1', installed_at=date(2025, 1, 1),
        )
        # Heure fixée à 10:00 (heure locale) : le résultat ne dépend pas de l'heure du test.
        from unittest import mock
        now = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
        patcher = mock.patch('django.utils.timezone.now', return_value=now)
        patcher.start()
        self.addCleanup(patcher.stop)
        today_noon = now.replace(hour=12)

        # Intervention clôturée « à replanifier » : crée une suite sans technicien.
        origin = self._ticket(now - timedelta(days=2), status='in_progress', technician=self.tech, effective_start=now - timedelta(days=2))
        self.follow_up = reschedule_ticket(origin, report='Pièce manquante.')
        self.origin = origin
        self.late = self._ticket(now - timedelta(days=1), status='planned', technician=self.tech)
        self.started_early = self._ticket(now + timedelta(days=1), status='in_progress', technician=self.tech, effective_start=now)
        self.today = self._ticket(today_noon, status='planned', technician=self.tech)
        self.future = self._ticket(now + timedelta(days=20), status='planned', technician=self.tech)
        self.unassigned = self._ticket(now + timedelta(days=5), status='pending')
        self.done = self._ticket(now - timedelta(days=3), status='done', technician=self.tech, effective_start=now - timedelta(days=3), effective_end=now - timedelta(days=3) + timedelta(hours=1))
        self.old_late = self._ticket(now - timedelta(days=10), status='planned', technician=self.tech)
        self.done_today = self._ticket(now - timedelta(hours=3), status='done', technician=self.tech,
                                       effective_start=now - timedelta(hours=2), effective_end=now - timedelta(hours=1))

        self.http = HttpClient()
        self.http.login(username='chef', password='Password123!')

    def _ticket(self, start, **kwargs):
        return MaintenanceTicket.objects.create(
            equipment=self.equipment, type='maintenance', planned_start=start, planned_end=start + timedelta(hours=1), **kwargs,
        )

    def _ids(self, rows):
        return [t.pk for t in rows]

    def test_sections_without_filter(self):
        response = self.http.get(reverse('ticket_list'))
        ctx = response.context
        self.assertEqual(self._ids(ctx['to_reschedule']), [self.follow_up.pk, self.late.pk])
        self.assertEqual([t.reschedule_reason for t in ctx['to_reschedule']], ['follow_up', 'late'])
        self.assertEqual(ctx['to_reschedule'][0].origin_id, self.origin.pk)

        # Démarrée en avance (prévue demain) : en tête des interventions du jour.
        of_the_day = self._ids(ctx['of_the_day'])
        self.assertEqual(of_the_day[0], self.started_early.pk)
        self.assertEqual(of_the_day, [self.started_early.pk, self.today.pk, self.done_today.pk])
        self.assertEqual(ctx['older_late'], 1)

        rest = self._ids(ctx['tickets'])
        for ticket in (self.follow_up, self.late, self.started_early):
            self.assertNotIn(ticket.pk, rest)
        for ticket in (self.future, self.unassigned, self.done, self.origin, self.old_late):
            self.assertIn(ticket.pk, rest)
        self.assertNotIn(self.done_today.pk, rest)
        self.assertEqual(ctx['unassigned_count'], 2)  # la suite + le ticket à venir non assigné

        html = response.content.decode()
        self.assertIn('Interventions à replanifier', html)
        self.assertIn(f"Suite de l'intervention #{self.origin.pk}", html)
        self.assertIn('Créneau dépassé, non démarrée', html)
        self.assertIn('Interventions du jour', html)

    def test_assigned_follow_up_leaves_the_reschedule_section(self):
        self.follow_up.technician = self.tech
        self.follow_up.status = 'planned'
        self.follow_up.planned_start = timezone.now() + timedelta(days=2)
        self.follow_up.planned_end = self.follow_up.planned_start + timedelta(hours=1)
        self.follow_up.save()
        response = self.http.get(reverse('ticket_list'))
        self.assertEqual(self._ids(response.context['to_reschedule']), [self.late.pk])

    def test_filters_show_a_single_result_list(self):
        response = self.http.get(reverse('ticket_list'), {'status': 'in_progress'})
        self.assertTrue(response.context['filtering'])
        self.assertEqual(response.context['to_reschedule'], [])
        self.assertEqual(self._ids(response.context['tickets']), [self.started_early.pk])
        self.assertNotIn('Interventions du jour', response.content.decode())

    def test_unassigned_filter(self):
        response = self.http.get(reverse('ticket_list'), {'technician': 'none'})
        self.assertEqual(set(self._ids(response.context['tickets'])), {self.follow_up.pk, self.unassigned.pk})

    def test_date_filter_uses_local_day(self):
        """Filtre par date en heure locale, sans recherche __date (inopérante sur MySQL sans fuseaux)."""
        day = timezone.localdate(self.today.planned_start).isoformat()
        response = self.http.get(reverse('ticket_list'), {'date': day})
        self.assertIn(self.today.pk, self._ids(response.context['tickets']))
        self.assertNotIn(self.future.pk, self._ids(response.context['tickets']))

    def test_invalid_date_filter_is_ignored(self):
        response = self.http.get(reverse('ticket_list'), {'date': 'pas-une-date'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filtering'])


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class ScheduleConflictTestCase(TestCase):
    """Un technicien ne peut pas avoir deux interventions sur des créneaux qui se chevauchent."""

    def setUp(self):
        from rest_framework.test import APIClient
        self.manager = CustomUser.objects.create_user(username='chef_c', password='Password123!', role='manager')
        self.tech = CustomUser.objects.create_user(username='tech_c', password='Password123!', role='technician').technician_profile
        self.other_tech = CustomUser.objects.create_user(username='tech_d', password='Password123!', role='technician').technician_profile
        self.client_obj = Client.objects.create(name='Client C', address='1 rue C')
        self.building = Building.objects.create(client=self.client_obj, name='Site C', address='1 rue C')
        self.equipment = Equipment.objects.create(
            building=self.building, name='Pompe', equipment_type=EquipmentType.objects.create(name='Pompe'),
            serial_number='PO-1', installed_at=date(2025, 1, 1),
        )
        # Intervention existante : 15/12/2026 de 09:00 à 10:30 (heure locale).
        self.start = timezone.make_aware(timezone.datetime(2026, 12, 15, 9, 0))
        self.existing = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech, type='maintenance', status='planned',
            planned_start=self.start, planned_end=self.start + timedelta(minutes=90),
        )
        self.http = HttpClient()
        self.http.login(username='chef_c', password='Password123!')
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def _form_data(self, **overrides):
        data = {
            'client': self.client_obj.id, 'building': self.building.id, 'equipment': self.equipment.id,
            'technician': self.tech.id, 'type': 'maintenance', 'status': 'planned',
            'planned_date': '2026-12-15', 'start_time_slot': '10:00', 'duration_seconds': 3600,
            'description': 'Contrôle',
        }
        data.update(overrides)
        return data

    def test_form_refuses_overlapping_slot(self):
        response = self.http.post(reverse('ticket_create'), self._form_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MaintenanceTicket.objects.count(), 1)
        html = response.content.decode()
        self.assertIn('Conflit de planning', html)
        self.assertIn(f'#{self.existing.pk}', html)
        self.assertIn(reverse('ticket_detail', args=[self.existing.pk]), html)
        self.assertIn('le 15/12 de 09:00 à 10:30', html)

    def test_form_accepts_adjacent_slot_other_technician_or_unassigned(self):
        for data in (
            self._form_data(start_time_slot='10:30'),
            self._form_data(technician=self.other_tech.id),
            self._form_data(technician=''),
        ):
            response = self.http.post(reverse('ticket_create'), data)
            self.assertEqual(response.status_code, 302, data)
        self.assertEqual(MaintenanceTicket.objects.count(), 4)

    def test_finished_canceled_or_rescheduled_tickets_do_not_block(self):
        for status in ('done', 'canceled', 'to_reschedule'):
            self.existing.status = status
            self.existing.save()
            self.assertIsNone(self._conflict(self.start, self.start + timedelta(hours=1)), status)

    def test_started_ticket_occupies_its_effective_slot(self):
        """Démarrée à 14:00 pour 1h30 : le créneau prévu de 09:00 est libéré, 14:00–15:30 est occupé."""
        self.existing.status = 'in_progress'
        self.existing.effective_start = self.start.replace(hour=14)
        self.existing.save()
        self.assertIsNone(self._conflict(self.start, self.start + timedelta(hours=1)))
        conflict = self._conflict(self.start.replace(hour=15), self.start.replace(hour=16))
        self.assertEqual(conflict, self.existing)
        self.assertEqual(timezone.localtime(conflict.busy_end).strftime('%H:%M'), '15:30')

    def test_editing_a_ticket_does_not_conflict_with_itself(self):
        response = self.http.post(reverse('ticket_update', args=[self.existing.pk]), self._form_data(start_time_slot='09:00', duration_seconds=5400))
        self.assertEqual(response.status_code, 302)

    def test_moving_a_ticket_onto_another_is_refused(self):
        other = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech, type='maintenance', status='planned',
            planned_start=self.start.replace(hour=14), planned_end=self.start.replace(hour=15),
        )
        response = self.http.post(reverse('ticket_update', args=[other.pk]), self._form_data(start_time_slot='09:30'))
        self.assertEqual(response.status_code, 200)
        other.refresh_from_db()
        self.assertEqual(timezone.localtime(other.planned_start).hour, 14)

    def test_api_refuses_overlapping_slot(self):
        payload = {
            'equipment': self.equipment.id, 'technician': self.tech.id, 'type': 'repair',
            'planned_start': self.start.replace(hour=10).isoformat(), 'planned_end': self.start.replace(hour=11).isoformat(),
        }
        response = self.api.post('/api/v1/tickets/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Conflit de planning', str(response.data['planned_start']))
        payload['planned_start'] = self.start.replace(hour=11).isoformat()
        payload['planned_end'] = self.start.replace(hour=12).isoformat()
        self.assertEqual(self.api.post('/api/v1/tickets/', payload, format='json').status_code, 201)

    def test_api_patch_onto_another_slot_is_refused(self):
        other = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech, type='maintenance', status='planned',
            planned_start=self.start.replace(hour=14), planned_end=self.start.replace(hour=15),
        )
        response = self.api.patch(f'/api/v1/tickets/{other.pk}/', {
            'planned_start': self.start.replace(hour=9, minute=30).isoformat(),
            'planned_end': self.start.replace(hour=10, minute=30).isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def _conflict(self, start, end):
        from maintenance.services import find_schedule_conflict
        return find_schedule_conflict(self.tech, start, end)


@override_settings(SECURE_SSL_REDIRECT=False, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TicketFormLocalTimeTestCase(TestCase):
    """Le formulaire de modification affiche l'heure locale : l'enregistrer sans changement ne décale rien."""

    def test_edit_form_shows_local_time_and_keeps_the_slot(self):
        from maintenance.forms import MaintenanceTicketForm
        CustomUser.objects.create_user(username='chef_t', password='Password123!', role='manager')
        tech = CustomUser.objects.create_user(username='tech_t', password='Password123!', role='technician').technician_profile
        client_obj = Client.objects.create(name='Client T', address='1 rue T')
        building = Building.objects.create(client=client_obj, name='Site T', address='1 rue T')
        equipment = Equipment.objects.create(
            building=building, name='Clim', equipment_type=EquipmentType.objects.create(name='Clim'),
            serial_number='CL-1', installed_at=date(2025, 1, 1),
        )
        # 09:00 heure de Paris en été = 07:00 UTC : l'ancien formulaire affichait 07:00 et réenregistrait 07:00 heure locale.
        start = timezone.make_aware(timezone.datetime(2026, 7, 10, 9, 0))
        ticket = MaintenanceTicket.objects.create(
            equipment=equipment, technician=tech, type='maintenance', status='planned',
            planned_start=start, planned_end=start + timedelta(minutes=90),
        )
        # Relu depuis la base (heure UTC), comme dans la vue de modification.
        form = MaintenanceTicketForm(instance=MaintenanceTicket.objects.get(pk=ticket.pk))
        self.assertEqual(form.fields['planned_date'].initial, '2026-07-10')
        self.assertEqual(form.fields['start_time_slot'].initial, '09:00')

        http = HttpClient()
        http.login(username='chef_t', password='Password123!')
        response = http.post(reverse('ticket_update', args=[ticket.pk]), {
            'client': client_obj.id, 'building': building.id, 'equipment': equipment.id, 'technician': tech.id,
            'type': 'maintenance', 'status': 'planned', 'planned_date': form.fields['planned_date'].initial,
            'start_time_slot': form.fields['start_time_slot'].initial, 'duration_seconds': 5400, 'description': '',
        })
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.planned_start, start)
