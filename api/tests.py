"""
Tests de l'API REST SMARTOPS v0.2.0.
Couvre : Auth JWT, Inventaire, Maintenance (start/stop), accès technicien.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import CustomUser
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician, MaintenanceTicket


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class JWTAuthTestCase(TestCase):
    def setUp(self):
        self.client_http = APIClient()
        self.manager = CustomUser.objects.create_user(
            username='manager1', password='testpass123', role='manager'
        )

    def test_obtain_token(self):
        response = self.client_http.post('/api/v1/auth/token/', {
            'username': 'manager1', 'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_me_endpoint(self):
        response = self.client_http.post('/api/v1/auth/token/', {
            'username': 'manager1', 'password': 'testpass123'
        })
        token = response.data['access']
        self.client_http.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        me = self.client_http.get('/api/v1/auth/me/')
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data['username'], 'manager1')

    def test_protected_endpoint_without_token(self):
        response = self.client_http.get('/api/v1/clients/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class InventoryAPITestCase(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.manager = CustomUser.objects.create_user(
            username='mgr', password='pass', role='manager'
        )
        resp = self.api.post('/api/v1/auth/token/', {'username': 'mgr', 'password': 'pass'})
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

        self.client_obj = Client.objects.create(
            name='ACME Corp', address='1 rue Test', contact_name='Jean',
            email='jean@acme.fr'
        )
        self.building = Building.objects.create(
            client=self.client_obj, name='Siège', address='1 rue Test'
        )
        self.eq_type = EquipmentType.objects.create(name='Ascenseur')
        self.equipment = Equipment.objects.create(
            building=self.building, name='Ascenseur A1',
            equipment_type=self.eq_type, serial_number='SN-001',
            installed_at='2024-01-01'
        )

    def test_list_clients(self):
        r = self.api.get('/api/v1/clients/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_create_client(self):
        r = self.api.post('/api/v1/clients/', {
            'name': 'New Client', 'address': '2 rue Dev',
            'contact_name': 'Alice', 'email': 'alice@new.fr'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_list_buildings_filtered_by_client(self):
        r = self.api.get(f'/api/v1/buildings/?client={self.client_obj.id}')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_list_equipment_types(self):
        r = self.api.get('/api/v1/equipment-types/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_list_equipments(self):
        r = self.api.get('/api/v1/equipments/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_patch_client(self):
        """Vérifie la mise à jour partielle (PATCH) d'un client."""
        r = self.api.patch(f'/api/v1/clients/{self.client_obj.id}/', {
            'phone': '+32 2 123 45 67',
            'contact_name': 'Jean Dupont (Modifié)'
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.phone, '+32 2 123 45 67')
        self.assertEqual(self.client_obj.contact_name, 'Jean Dupont (Modifié)')

    def test_create_building(self):
        """Vérifie la création d'un bâtiment rattaché à un client existant."""
        r = self.api.post('/api/v1/buildings/', {
            'client': self.client_obj.id,
            'name': 'Entrepôt Logistique Sud',
            'address': 'Zone Industrielle 4, 1000 Bruxelles'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Building.objects.filter(name='Entrepôt Logistique Sud').count(), 1)

    def test_create_equipment_type(self):
        """Vérifie la création d'un type d'équipement."""
        r = self.api.post('/api/v1/equipment-types/', {
            'name': 'Centrale Traitement Air'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EquipmentType.objects.filter(name='Centrale Traitement Air').count(), 1)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class TicketAPITestCase(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.manager = CustomUser.objects.create_user(
            username='mgr2', password='pass', role='manager'
        )
        self.tech_user = CustomUser.objects.create_user(
            username='tech1', password='pass', role='technician'
        )
        tech_token = self.api.post('/api/v1/auth/token/', {'username': 'tech1', 'password': 'pass'})
        self.tech_token = tech_token.data['access']

        mgr_token = self.api.post('/api/v1/auth/token/', {'username': 'mgr2', 'password': 'pass'})
        self.mgr_token = mgr_token.data['access']

        client_obj = Client.objects.create(
            name='Test Corp', address='Rue A', contact_name='Bob', email='b@t.fr'
        )
        building = Building.objects.create(client=client_obj, name='Bâtiment B', address='Rue A')
        eq_type = EquipmentType.objects.create(name='HVAC')
        equipment = Equipment.objects.create(
            building=building, name='Clim 1', equipment_type=eq_type,
            serial_number='SN-002', installed_at='2024-06-01'
        )
        tech_profile = Technician.objects.get(user=self.tech_user)
        now = timezone.now()
        self.ticket = MaintenanceTicket.objects.create(
            equipment=equipment,
            technician=tech_profile,
            type='maintenance',
            planned_start=now,
            planned_end=now + timedelta(hours=2),
            status='planned',
        )

    def test_manager_sees_all_tickets(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.mgr_token}')
        r = self.api.get('/api/v1/tickets/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_technician_sees_own_tickets_only(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        r = self.api.get('/api/v1/tickets/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_start_stop_intervention(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')

        # Démarrage
        r = self.api.post(f'/api/v1/tickets/{self.ticket.id}/start/', {})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'in_progress')

        # Double démarrage interdit
        r2 = self.api.post(f'/api/v1/tickets/{self.ticket.id}/start/', {})
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

        # Arrêt avec rapport
        r3 = self.api.post(f'/api/v1/tickets/{self.ticket.id}/stop/', {
            'intervention_report': 'Remplacement filtre effectué.',
            'status': 'done',
        })
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertEqual(r3.data['status'], 'done')
        self.assertIn('Remplacement', r3.data['intervention_report'])

    def test_stop_to_reschedule_creates_follow_up(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        self.api.post(f'/api/v1/tickets/{self.ticket.id}/start/', {})
        r = self.api.post(f'/api/v1/tickets/{self.ticket.id}/stop/', {
            'intervention_report': 'Pièce manquante.',
            'status': 'to_reschedule',
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'to_reschedule')
        follow_up = MaintenanceTicket.objects.exclude(pk=self.ticket.pk).get()
        self.assertEqual(follow_up.status, 'pending')
        self.assertIsNone(follow_up.technician)

        # Le ticket clôturé ne peut plus être démarré
        r2 = self.api.post(f'/api/v1/tickets/{self.ticket.id}/start/', {})
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_my_interventions_uses_effective_date(self):
        now = timezone.now()
        self.ticket.planned_start = now + timedelta(days=1)
        self.ticket.planned_end = now + timedelta(days=1, hours=1)
        self.ticket.effective_start = now - timedelta(minutes=50)
        self.ticket.effective_end = now - timedelta(minutes=10)
        self.ticket.status = 'done'
        self.ticket.save()

        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        r = self.api.get('/api/v1/my/interventions/?range=today')
        self.assertEqual([t['id'] for t in r.data], [self.ticket.id])

    def test_my_interventions_endpoint(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        r = self.api.get('/api/v1/my/interventions/?range=today')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_manager_forbidden_on_my_interventions(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.mgr_token}')
        r = self.api.get('/api/v1/my/interventions/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_ticket_by_manager(self):
        """Vérifie la création et planification d'un ticket par un gestionnaire."""
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.mgr_token}')
        tech_profile = Technician.objects.get(user=self.tech_user)
        now = timezone.now()
        r = self.api.post('/api/v1/tickets/', {
            'equipment': self.ticket.equipment.id,
            'technician': tech_profile.id,
            'type': 'repair',
            'planned_start': now.isoformat(),
            'planned_end': (now + timedelta(hours=3)).isoformat(),
            'description': 'Panne de climatisation signalée au 2ème étage.'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MaintenanceTicket.objects.filter(description__contains='Panne de climatisation').count(), 1)

    def test_start_intervention_with_geolocation(self):
        """Vérifie le démarrage d'intervention avec enregistrement des coordonnées GPS."""
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        r = self.api.post(f'/api/v1/tickets/{self.ticket.id}/start/', {
            'latitude': 50.850346,
            'longitude': 4.351710
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'in_progress')
        self.assertAlmostEqual(float(self.ticket.start_latitude), 50.850346, places=5)
        self.assertAlmostEqual(float(self.ticket.start_longitude), 4.351710, places=5)

    def test_technician_uploads_and_lists_intervention_photos(self):
        """L'endpoint photos accepte l'ajout (multipart) et renvoie la liste."""
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), '#10b981').save(buf, format='PNG')
        img = SimpleUploadedFile('field.png', buf.getvalue(), content_type='image/png')

        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        with override_settings(MEDIA_ROOT='/tmp/smartops_api_test_media'):
            r = self.api.post(
                f'/api/v1/tickets/{self.ticket.id}/photos/',
                {'image': img, 'phase': 'after', 'caption': 'Résultat'},
                format='multipart',
            )
            self.assertEqual(r.status_code, status.HTTP_201_CREATED)
            self.assertEqual(r.data['phase'], 'after')

            r = self.api.get(f'/api/v1/tickets/{self.ticket.id}/photos/')
            self.assertEqual(r.status_code, status.HTTP_200_OK)
            self.assertEqual(len(r.data), 1)

        import shutil
        shutil.rmtree('/tmp/smartops_api_test_media', ignore_errors=True)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class RolePermissionsAPITestCase(TestCase):
    """Droits d'accès à l'API par rôle (dossier technique §4.3.1)."""

    def setUp(self):
        self.api = APIClient()
        for username, role in (('mgr3', 'manager'), ('tech_a', 'technician'), ('tech_b', 'technician')):
            CustomUser.objects.create_user(username=username, password='pass', role=role)
        self.tokens = {
            name: self.api.post('/api/v1/auth/token/', {'username': name, 'password': 'pass'}).data['access']
            for name in ('mgr3', 'tech_a', 'tech_b')
        }
        client_obj = Client.objects.create(name='Perm Corp', address='Rue P', contact_name='Eve', email='e@p.fr')
        self.building = Building.objects.create(client=client_obj, name='Bâtiment P', address='Rue P')
        self.eq_type = EquipmentType.objects.create(name='Pompe')
        self.equipment = Equipment.objects.create(
            building=self.building, name='Pompe 1', equipment_type=self.eq_type,
            serial_number='SN-P01', installed_at='2024-01-01'
        )
        now = timezone.now()
        self.tech_a = Technician.objects.get(user__username='tech_a')
        self.tech_b = Technician.objects.get(user__username='tech_b')
        self.ticket_a = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech_a, type='maintenance',
            planned_start=now, planned_end=now + timedelta(hours=1), status='planned',
        )
        self.ticket_b = MaintenanceTicket.objects.create(
            equipment=self.equipment, technician=self.tech_b, type='maintenance',
            planned_start=now, planned_end=now + timedelta(hours=1), status='planned',
        )

    def login_as(self, username):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens[username]}')

    def equipment_payload(self, serial):
        return {
            'building': self.building.id, 'name': 'Pompe 2', 'equipment_type': self.eq_type.id,
            'serial_number': serial, 'installed_at': '2024-02-01',
        }

    def ticket_payload(self):
        now = timezone.now()
        return {
            'equipment': self.equipment.id, 'technician': self.tech_a.id, 'type': 'repair',
            'planned_start': now.isoformat(), 'planned_end': (now + timedelta(hours=1)).isoformat(),
        }

    def test_technician_cannot_access_equipments(self):
        self.login_as('tech_a')
        url = f'/api/v1/equipments/{self.equipment.id}/'
        self.assertEqual(self.api.get('/api/v1/equipments/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.api.post('/api/v1/equipments/', self.equipment_payload('SN-P02')).status_code,
                         status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.api.patch(url, {'name': 'Renommé'}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.api.delete(url).status_code, status.HTTP_403_FORBIDDEN)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.name, 'Pompe 1')

    def test_manager_creates_equipment(self):
        self.login_as('mgr3')
        r = self.api.post('/api/v1/equipments/', self.equipment_payload('SN-P03'))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_technician_cannot_create_or_edit_tickets(self):
        self.login_as('tech_a')
        self.assertEqual(self.api.post('/api/v1/tickets/', self.ticket_payload()).status_code,
                         status.HTTP_403_FORBIDDEN)
        r = self.api.patch(f'/api/v1/tickets/{self.ticket_a.id}/', {'status': 'done', 'technician': self.tech_b.id})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.ticket_a.refresh_from_db()
        self.assertEqual((self.ticket_a.status, self.ticket_a.technician), ('planned', self.tech_a))

    def test_manager_creates_ticket(self):
        self.login_as('mgr3')
        self.assertEqual(self.api.post('/api/v1/tickets/', self.ticket_payload()).status_code,
                         status.HTTP_201_CREATED)

    def test_technician_gets_404_on_colleague_ticket(self):
        self.login_as('tech_a')
        for method, suffix in (('get', ''), ('post', 'start/'), ('post', 'stop/'), ('get', 'photos/')):
            r = getattr(self.api, method)(f'/api/v1/tickets/{self.ticket_b.id}/{suffix}')
            self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, suffix or 'retrieve')
        self.ticket_b.refresh_from_db()
        self.assertEqual(self.ticket_b.status, 'planned')

    def test_technician_starts_and_stops_own_ticket(self):
        self.login_as('tech_a')
        r = self.api.post(f'/api/v1/tickets/{self.ticket_a.id}/start/', {})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.api.post(f'/api/v1/tickets/{self.ticket_a.id}/stop/', {'status': 'done'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'done')


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class OpenAPISchemaTestCase(TestCase):
    def setUp(self):
        self.api = APIClient()
        user = CustomUser.objects.create_user(username='admin1', password='pass', role='admin')
        resp = self.api.post('/api/v1/auth/token/', {'username': 'admin1', 'password': 'pass'})
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')

    def test_schema_endpoint_accessible(self):
        r = self.api.get('/api/v1/schema/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_swagger_ui_accessible(self):
        r = self.api.get('/api/v1/docs/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
