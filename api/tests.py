"""
Tests de l'API REST SMARTOPS v0.2.0.
Couvre : Auth JWT, Inventaire, Maintenance (start/stop), accès technicien.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

from accounts.models import CustomUser
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician, MaintenanceTicket


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

    def test_my_interventions_endpoint(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tech_token}')
        r = self.api.get('/api/v1/my/interventions/?range=today')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_manager_forbidden_on_my_interventions(self):
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {self.mgr_token}')
        r = self.api.get('/api/v1/my/interventions/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


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
