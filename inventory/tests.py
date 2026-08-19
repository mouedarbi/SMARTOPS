from django.test import TestCase, Client as HttpClient, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from accounts.models import CustomUser
from maintenance.models import MaintenanceTicket
from .models import Client, Building, Equipment, EquipmentType, EquipmentTypeField


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class InventoryModelsTest(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="Client Test",
            address="123 Rue de Paris",
            contact_name="Jean Dupont",
            email="jean@test.com",
            phone="0123456789",
            vat_number="FR123456789"
        )
        self.building = Building.objects.create(
            client=self.client_obj,
            name="Bâtiment A",
            address="456 Avenue de Lyon"
        )
        self.equipment_type = EquipmentType.objects.create(name="elevator")
        self.equipment = Equipment.objects.create(
            building=self.building,
            name="Ascenseur 1",
            equipment_type=self.equipment_type,
            serial_number="SN123456",
            installed_at=date(2025, 1, 1)
        )

    def test_client_creation(self):
        self.assertEqual(str(self.client_obj), "Client Test")
        self.assertTrue(self.client_obj.is_active)
        self.assertEqual(self.client_obj.phone, "0123456789")
        self.assertEqual(self.client_obj.vat_number, "FR123456789")

    def test_building_creation(self):
        self.assertEqual(str(self.building), "Bâtiment A (Client Test)")
        self.assertEqual(self.building.client, self.client_obj)

    def test_equipment_creation(self):
        self.assertEqual(str(self.equipment), "Ascenseur 1 (SN123456)")
        self.assertEqual(self.equipment.building, self.building)
        self.assertEqual(self.equipment.equipment_type, self.equipment_type)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class InventoryWebViewsTestCase(TestCase):
    def setUp(self):
        self.manager = CustomUser.objects.create_user(
            username='inventory_manager',
            password='Password123!',
            role='manager'
        )
        self.client_obj = Client.objects.create(
            name="Société Alpha SPRL",
            address="Rue Royale 10, 1000 Bruxelles",
            contact_name="Marc Lambert",
            email="contact@alpha.be",
            phone="+32 2 123 45 67",
            vat_number="BE0123456789"
        )
        self.building = Building.objects.create(
            client=self.client_obj,
            name="Siège Social",
            address="Rue Royale 10, 1000 Bruxelles"
        )
        self.eq_type = EquipmentType.objects.create(name="Centrale Incendie")
        self.equipment = Equipment.objects.create(
            building=self.building,
            name="Centrale SSI Nord",
            equipment_type=self.eq_type,
            serial_number="SSI-2025-001",
            installed_at=date(2025, 3, 1)
        )
        self.http_client = HttpClient()
        self.http_client.login(username='inventory_manager', password='Password123!')

    def test_client_update_view_post_by_manager(self):
        """F2 : Vérifie la mise à jour des coordonnées d'un client par un gestionnaire via l'IHM."""
        url = reverse('client_update', kwargs={'pk': self.client_obj.id})
        data = {
            'name': 'Société Alpha SPRL (Modifiée)',
            'address': 'Avenue Louise 50, 1050 Bruxelles',
            'contact_name': 'Marc Lambert Senior',
            'email': 'direction@alpha.be',
            'phone': '+32 2 987 65 43',
            'vat_number': 'BE0123456789',
            'is_active': True
        }
        response = self.http_client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.name, 'Société Alpha SPRL (Modifiée)')
        self.assertEqual(self.client_obj.contact_name, 'Marc Lambert Senior')
        self.assertEqual(self.client_obj.email, 'direction@alpha.be')

    def test_equipment_detail_view_shows_intervention_history(self):
        """F3 : Vérifie que la vue détail d'un équipement transmet l'historique de ses tickets d'intervention."""
        now = timezone.now()
        ticket1 = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            type='repair',
            status='done',
            planned_start=now - timedelta(days=2),
            planned_end=now - timedelta(days=2, hours=-2),
            effective_start=now - timedelta(days=2),
            effective_end=now - timedelta(days=2, hours=-1),
            description='Remplacement batterie backup'
        )
        ticket2 = MaintenanceTicket.objects.create(
            equipment=self.equipment,
            type='maintenance',
            status='planned',
            planned_start=now + timedelta(days=5),
            planned_end=now + timedelta(days=5, hours=2),
            description='Contrôle annuel des détecteurs'
        )

        url = reverse('equipment_detail', kwargs={'pk': self.equipment.id})
        response = self.http_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['equipment'], self.equipment)
        tickets_in_context = list(response.context['tickets'])
        self.assertIn(ticket1, tickets_in_context)
        self.assertIn(ticket2, tickets_in_context)

    def test_equipment_type_create_and_custom_field_addition(self):
        """F4 : Vérifie la création d'un type d'équipement et l'ajout de champs personnalisés (typés)."""
        # 1. Création d'un nouveau type
        type_url = reverse('equipment_type_list')
        response = self.http_client.post(type_url, {'name': 'Groupe Électrogène'}, follow=True)
        self.assertEqual(response.status_code, 200)
        new_type = EquipmentType.objects.get(name='Groupe Électrogène')

        # 2. Ajout d'un champ personnalisé (type number)
        field_url = reverse('equipment_type_detail', kwargs={'pk': new_type.id})
        field_data = {
            'field_name': 'Puissance (kVA)',
            'field_type': 'number',
            'required': True
        }
        response = self.http_client.post(field_url, field_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Vérification en base
        custom_field = EquipmentTypeField.objects.filter(equipment_type=new_type, field_name='Puissance (kVA)').first()
        self.assertIsNotNone(custom_field)
        self.assertEqual(custom_field.field_type, 'number')
        self.assertTrue(custom_field.required)

