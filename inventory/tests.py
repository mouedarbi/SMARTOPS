"""
Fichier : tests.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Tests des vues d'inventaire (clients, lieux, équipements, étiquettes et rapport public).
"""

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
        # Chaque intervention de l'historique ouvre la fiche de son ticket (issue #30).
        for ticket in (ticket1, ticket2):
            self.assertContains(response, f'href="{reverse("ticket_detail", args=[ticket.id])}"')

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


@override_settings(SECURE_SSL_REDIRECT=False, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CreationFromParentTests(TestCase):
    """Un lieu se crée depuis la fiche de son client, un équipement depuis la fiche de son lieu :
    le parent est fixé, jamais choisi dans une liste, et le client d'un lieu ne change pas."""

    def setUp(self):
        CustomUser.objects.create_user(username='gestion', password='Password123!', role='manager')
        self.alpha = Client.objects.create(name="Société Alpha", address="Rue Royale 10", contact_name="Marc",
                                           email="alpha@example.be", phone="0", vat_number="BE0123456789")
        self.beta = Client.objects.create(name="Société Beta", address="Rue Haute 1", contact_name="Anne",
                                          email="beta@example.be", phone="0", vat_number="BE0987654321")
        self.building = Building.objects.create(client=self.alpha, name="Siège", address="Rue Royale 10")
        self.eq_type = EquipmentType.objects.create(name="Centrale Incendie")
        self.http = HttpClient()
        self.http.login(username='gestion', password='Password123!')

    def test_building_form_shows_the_client_without_a_select(self):
        response = self.http.get(reverse('building_create') + f'?client={self.alpha.pk}')
        self.assertContains(response, 'Société Alpha')
        self.assertNotContains(response, 'name="client"')
        self.assertNotContains(response, 'Société Beta')

    def test_building_is_created_for_the_client_of_the_url(self):
        response = self.http.post(reverse('building_create') + f'?client={self.alpha.pk}',
                                  {'name': 'Entrepôt', 'address': 'Rue du Port 2', 'client': self.beta.pk})
        self.assertRedirects(response, reverse('client_detail', args=[self.alpha.pk]), fetch_redirect_response=False)
        self.assertEqual(Building.objects.get(name='Entrepôt').client, self.alpha)

    def test_building_creation_without_client_goes_back_to_the_list(self):
        for query in ('', '?client=999', '?client=abc'):
            response = self.http.get(reverse('building_create') + query)
            self.assertRedirects(response, reverse('building_list'), fetch_redirect_response=False)
        self.assertEqual(Building.objects.count(), 1)

    def test_building_update_never_changes_its_client(self):
        self.http.post(reverse('building_update', args=[self.building.pk]),
                       {'name': 'Siège rénové', 'address': 'Rue Royale 10', 'client': self.beta.pk})
        self.building.refresh_from_db()
        self.assertEqual((self.building.name, self.building.client), ('Siège rénové', self.alpha))

    def test_equipment_form_shows_the_building_and_its_client(self):
        response = self.http.get(reverse('equipment_create') + f'?building={self.building.pk}')
        self.assertContains(response, 'Siège — Société Alpha')
        self.assertNotContains(response, 'name="building"')

    def test_equipment_is_created_in_the_building_of_the_url(self):
        other = Building.objects.create(client=self.beta, name="Usine", address="Rue Haute 1")
        response = self.http.post(reverse('equipment_create') + f'?building={self.building.pk}', {
            'name': 'Centrale Nord', 'equipment_type': self.eq_type.pk, 'serial_number': 'SN-1',
            'installed_at': '2026-01-15', 'building': other.pk})
        self.assertRedirects(response, reverse('building_detail', args=[self.building.pk]), fetch_redirect_response=False)
        self.assertEqual(Equipment.objects.get(serial_number='SN-1').building, self.building)

    def test_equipment_creation_without_building_goes_back_to_the_list(self):
        response = self.http.get(reverse('equipment_create'))
        self.assertRedirects(response, reverse('equipment_list'), fetch_redirect_response=False)

    def test_lists_no_longer_offer_a_creation_button(self):
        self.assertNotContains(self.http.get(reverse('building_list')), reverse('building_create'))
        self.assertNotContains(self.http.get(reverse('equipment_list')), reverse('equipment_create'))


@override_settings(SECURE_SSL_REDIRECT=False, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class EquipmentCustomFieldsFormTests(TestCase):
    """Le formulaire d'ajout d'un équipement propose les champs personnalisés du type choisi, les
    valide (obligation, format) avec un message sous le champ, et les enregistre dans custom_fields."""

    def setUp(self):
        CustomUser.objects.create_user(username='gestion', password='Password123!', role='manager')
        client = Client.objects.create(name="Société Alpha", address="Rue Royale 10", contact_name="Marc",
                                       email="alpha@example.be", phone="0", vat_number="BE0123456789")
        self.building = Building.objects.create(client=client, name="Siège", address="Rue Royale 10")
        self.detector = EquipmentType.objects.create(name="Détecteur de fumée")
        self.battery = EquipmentTypeField.objects.create(equipment_type=self.detector, field_name="Autonomie pile (ans)",
                                                         field_type='number', required=True)
        self.made = EquipmentTypeField.objects.create(equipment_type=self.detector, field_name="Date de fabrication",
                                                      field_type='date', required=True)
        self.note = EquipmentTypeField.objects.create(equipment_type=self.detector, field_name="Remarque",
                                                      field_type='text', required=False)
        self.lift = EquipmentType.objects.create(name="Ascenseur")
        self.capacity = EquipmentTypeField.objects.create(equipment_type=self.lift, field_name="Capacité (kg)",
                                                          field_type='number', required=True)
        self.http = HttpClient()
        self.http.login(username='gestion', password='Password123!')
        self.url = reverse('equipment_create') + f'?building={self.building.pk}'

    def post(self, **custom):
        data = {'name': 'Détecteur hall', 'equipment_type': self.detector.pk, 'serial_number': 'DF-1',
                'installed_at': '2026-01-15', **custom}
        return self.http.post(self.url, data)

    def test_form_offers_the_custom_fields_of_each_type(self):
        response = self.http.get(self.url)
        self.assertContains(response, 'Autonomie pile (ans) *')
        self.assertContains(response, 'Capacité (kg) *')
        self.assertContains(response, f'data-equipment-type="{self.detector.pk}"')

    def test_custom_fields_are_saved_with_their_type(self):
        response = self.post(**{f'cf_{self.battery.pk}': '10', f'cf_{self.made.pk}': '2025-06-01',
                                f'cf_{self.note.pk}': 'Hall d\'entrée'})
        self.assertEqual(response.status_code, 302)
        equipment = Equipment.objects.get(serial_number='DF-1')
        self.assertEqual(equipment.custom_fields, {'Autonomie pile (ans)': 10, 'Date de fabrication': '2025-06-01',
                                                   'Remarque': "Hall d'entrée"})

    def test_missing_required_field_shows_a_message_instead_of_a_server_error(self):
        response = self.post(**{f'cf_{self.battery.pk}': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ce champ est requis pour ce type d&#x27;équipement.")
        self.assertFalse(Equipment.objects.exists())

    def test_invalid_number_or_date_is_refused(self):
        response = self.post(**{f'cf_{self.battery.pk}': 'dix', f'cf_{self.made.pk}': '31/31/2025'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['form'].errors), {f'cf_{self.battery.pk}', f'cf_{self.made.pk}'})
        self.assertFalse(Equipment.objects.exists())

    def test_fields_of_another_type_are_neither_required_nor_saved(self):
        self.post(**{f'cf_{self.battery.pk}': '7.5', f'cf_{self.made.pk}': '2025-06-01',
                     f'cf_{self.capacity.pk}': 'pas un nombre'})
        equipment = Equipment.objects.get(serial_number='DF-1')
        self.assertEqual(equipment.custom_fields, {'Autonomie pile (ans)': 7.5, 'Date de fabrication': '2025-06-01'})
