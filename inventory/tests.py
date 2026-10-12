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
                                  {'name': 'Entrepôt', 'street': 'Rue du Port', 'house_number': '2', 'postal_code': '1000',
                                   'city': 'Bruxelles', 'country': 'BE', 'client': self.beta.pk})
        self.assertRedirects(response, reverse('client_detail', args=[self.alpha.pk]), fetch_redirect_response=False)
        self.assertEqual(Building.objects.get(name='Entrepôt').client, self.alpha)

    def test_building_creation_without_client_goes_back_to_the_list(self):
        for query in ('', '?client=999', '?client=abc'):
            response = self.http.get(reverse('building_create') + query)
            self.assertRedirects(response, reverse('building_list'), fetch_redirect_response=False)
        self.assertEqual(Building.objects.count(), 1)

    def test_building_update_never_changes_its_client(self):
        self.http.post(reverse('building_update', args=[self.building.pk]),
                       {'name': 'Siège rénové', 'street': 'Rue Royale', 'house_number': '10', 'postal_code': '1000',
                        'city': 'Bruxelles', 'country': 'BE', 'client': self.beta.pk})
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


@override_settings(SECURE_SSL_REDIRECT=False)
class EquipmentPublicReportTests(TestCase):
    """Page publique du certificat (scan QR) : conformité et échéances, sans propriétaire ni interventions."""

    def setUp(self):
        from datetime import date, timedelta
        from django.utils import timezone
        from accounts.models import CustomUser
        from maintenance.models import MaintenanceTicket
        from system.models import SystemConfiguration
        self.timedelta, self.timezone, self.Ticket = timedelta, timezone, MaintenanceTicket
        client = Client.objects.create(name='Hôtel Confidentiel', address='1 rue Secrète')
        building = Building.objects.create(client=client, name='Aile Est', address='12 avenue Privée')
        self.equipment = Equipment.objects.create(
            building=building, name='Extincteur couloir', equipment_type=EquipmentType.objects.create(name='Extincteur'),
            serial_number='SN-EXT-001-01-1234', installed_at=date(2024, 3, 1),
        )
        self.tech = CustomUser.objects.create_user(
            username='tech_pub', password='x', role='technician', first_name='Jeanne', last_name='Martin',
        ).technician_profile
        config = SystemConfiguration.get_instance()
        config.company_name, config.company_phone = 'Maintenance SA', '+32 2 000 00 00'
        config.save()
        self.url = reverse('equipment_public_report', args=[self.equipment.serial_number])

    def _done(self, type_, days_ago):
        end = self.timezone.now() - self.timedelta(days=days_ago)
        return self.Ticket.objects.create(
            equipment=self.equipment, technician=self.tech, type=type_, status='done',
            planned_start=end - self.timedelta(hours=1), planned_end=end,
            effective_start=end - self.timedelta(hours=1), effective_end=end,
            intervention_report='Rapport confidentiel',
        )

    def test_only_maintenance_makes_the_device_compliant(self):
        self._done('repair', 10)
        self.assertContains(self.client.get(self.url), 'NON CONFORME')
        self._done('maintenance', 30)
        self.assertNotContains(self.client.get(self.url), 'NON CONFORME')
        self.assertContains(self.client.get(self.url), 'CONFORME')

    def test_expired_maintenance_is_not_compliant(self):
        self._done('maintenance', 400)
        response = self.client.get(self.url)
        self.assertContains(response, 'NON CONFORME')
        self.assertContains(response, 'Visite expirée')

    def test_no_owner_location_or_intervention_data(self):
        self._done('maintenance', 30)
        response = self.client.get(self.url)
        for private in ('Hôtel Confidentiel', '12 avenue Privée', 'Aile Est', 'Extincteur couloir',
                        'Jeanne', 'Martin', 'Rapport confidentiel', 'INT-'):
            self.assertNotContains(response, private)
        self.assertContains(response, 'SN-EXT-001-01-1234')
        self.assertContains(response, '01/03/2024')
        self.assertContains(response, 'Maintenance SA')


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class StructuredAddressTests(TestCase):
    """Adresse d'un lieu en champs séparés (format OpenStreetMap) et lien d'itinéraire du technicien."""

    def setUp(self):
        CustomUser.objects.create_user(username='gestion_adr', password='Password123!', role='manager')
        self.client_obj = Client.objects.create(name="Hôtel Ibis", address="Rue Neuve 1, 1000 Bruxelles, Belgique",
                                                contact_name="Marc", email="ibis@example.be", phone="0",
                                                vat_number="BE0111222333")
        self.http = HttpClient()
        self.http.login(username='gestion_adr', password='Password123!')

    def test_parse_and_format(self):
        from .addresses import parse_address, format_address
        parts = parse_address('Rue de la Loi 12 bte 3, 1000 Bruxelles, Belgique')
        self.assertEqual(parts, {'street': 'Rue de la Loi', 'house_number': '12', 'box': '3',
                                 'postal_code': '1000', 'city': 'Bruxelles', 'country': 'BE'})
        self.assertEqual(format_address(**parts), 'Rue de la Loi 12 bte 3, 1000 Bruxelles, Belgique')
        self.assertEqual(parse_address('Meir 16, 2000 Anvers')['country'], 'BE')
        for text in ('Test', 'rue de la poste 56 1000 Bruxelles', 'rue de la praire 25',
                     '24 rue de la poste 128 à 1000 Bruxelles'):
            self.assertIsNone(parse_address(text), text)

    def test_full_address_and_navigation_link_are_composed(self):
        building = Building.objects.create(client=self.client_obj, name="Hôtel", street="Rue Neuve",
                                           house_number="1", postal_code="1000", city="Bruxelles")
        self.assertEqual(building.address, 'Rue Neuve 1, 1000 Bruxelles, Belgique')
        self.assertTrue(building.is_address_complete)
        self.assertEqual(building.navigation_url,
                         'https://www.google.com/maps/dir/?api=1&destination=Rue+Neuve+1%2C+1000+Bruxelles%2C+Belgique')

    def test_old_free_address_is_kept_and_flagged(self):
        building = Building.objects.create(client=self.client_obj, name="Ancien", address="rue de la praire 25")
        self.assertEqual(building.address, 'rue de la praire 25')
        self.assertFalse(building.is_address_complete)
        response = self.http.get(reverse('building_detail', args=[building.pk]))
        self.assertContains(response, 'Adresse à compléter')

    def test_form_requires_structured_address(self):
        url = reverse('building_create') + f'?client={self.client_obj.pk}'
        response = self.http.post(url, {'name': 'Dépôt', 'street': 'Rue du Port', 'country': 'BE'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Building.objects.filter(name='Dépôt').exists())
        response = self.http.post(url, {'name': 'Dépôt', 'street': 'Rue du Port', 'house_number': '2',
                                        'postal_code': '10A0', 'city': 'Bruxelles', 'country': 'BE'})
        self.assertContains(response, 'Code postal invalide')
        self.http.post(url, {'name': 'Dépôt', 'street': 'Rue du Port', 'house_number': '2', 'box': '4',
                             'postal_code': '1000', 'city': 'Bruxelles', 'country': 'BE',
                             'access_notes': 'Quai de livraison'})
        building = Building.objects.get(name='Dépôt')
        self.assertEqual(building.address, 'Rue du Port 2 bte 4, 1000 Bruxelles, Belgique')
        self.assertEqual(building.access_notes, 'Quai de livraison')

    def test_data_migration_splits_existing_addresses(self):
        import importlib
        from django.apps import apps
        migration = importlib.import_module('inventory.migrations.0005_adresse_structuree_lieu')
        ok = Building.objects.create(client=self.client_obj, name="A", address="Meir 16, 2000 Anvers, Belgique")
        bad = Building.objects.create(client=self.client_obj, name="B", address="24 rue de la poste 128 à 1000 Bruxelles")
        migration.split_addresses(apps, None)
        ok.refresh_from_db()
        bad.refresh_from_db()
        self.assertEqual((ok.street, ok.house_number, ok.postal_code, ok.city, ok.country),
                         ('Meir', '16', '2000', 'Anvers', 'BE'))
        self.assertTrue(ok.is_address_complete)
        self.assertEqual(bad.street, '24 rue de la poste 128 à 1000 Bruxelles')
        self.assertFalse(bad.is_address_complete)
        self.assertEqual(bad.address, '24 rue de la poste 128 à 1000 Bruxelles')

    def test_technician_page_has_navigation_link_and_access_notes(self):
        from maintenance.models import Technician
        building = Building.objects.create(client=self.client_obj, name="Hôtel", street="Rue Neuve",
                                           house_number="1", postal_code="1000", city="Bruxelles",
                                           access_notes="Code porte 1234")
        equipment = Equipment.objects.create(building=building, name="Clim", serial_number="SN-ADR",
                                             equipment_type=EquipmentType.objects.create(name="HVAC-ADR"),
                                             installed_at=date(2024, 1, 1))
        tech_user = CustomUser.objects.create_user(username='tech_adr', password='Password123!', role='technician')
        ticket = MaintenanceTicket.objects.create(
            equipment=equipment, technician=Technician.objects.get(user=tech_user), type='maintenance',
            planned_start=timezone.now(), planned_end=timezone.now() + timedelta(hours=1))
        http = HttpClient()
        http.login(username='tech_adr', password='Password123!')
        response = http.get(reverse('technician_ticket_detail', args=[ticket.pk]))
        self.assertContains(response, building.navigation_url.replace('&', '&amp;'))
        self.assertContains(response, 'Code porte 1234')
        self.assertContains(response, '1000 Bruxelles')

    def test_api_exposes_structured_address(self):
        from rest_framework.test import APIClient
        building = Building.objects.create(client=self.client_obj, name="Hôtel", street="Rue Neuve",
                                           house_number="1", postal_code="1000", city="Bruxelles")
        api = APIClient()
        token = api.post('/api/v1/auth/token/', {'username': 'gestion_adr', 'password': 'Password123!'}).data['access']
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        data = api.get(f'/api/v1/buildings/{building.pk}/').data
        self.assertEqual(data['address'], 'Rue Neuve 1, 1000 Bruxelles, Belgique')
        self.assertEqual((data['street'], data['postal_code'], data['country']), ('Rue Neuve', '1000', 'BE'))
        self.assertTrue(data['is_address_complete'])
        self.assertTrue(data['navigation_url'].startswith('https://www.google.com/maps/dir/?api=1&destination='))


@override_settings(
    SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class InventoryTranslationTests(TestCase):
    """Traduction FR / NL / EN des écrans de l'inventaire (langue du profil de l'utilisateur)."""

    def setUp(self):
        self.manager = CustomUser.objects.create_user(username='gestion_i18n', password='Password123!', role='manager')
        self.client_obj = Client.objects.create(name="Hôtel Ibis", address="Rue Neuve 1, 1000 Bruxelles",
                                                contact_name="Marc", email="ibis@example.be")
        self.http = HttpClient()
        self.http.login(username='gestion_i18n', password='Password123!')

    def _check(self, url, expected):
        for language, texts in expected.items():
            self.manager.language = language
            self.manager.save()
            response = self.http.get(url)
            for text in texts:
                self.assertContains(response, text, msg_prefix=f"{language} {url}")

    def test_client_screens(self):
        self._check(reverse('client_list'), {
            'fr': ('Gestion des Clients', 'Nom du Client'), 'nl': ('Klantenbeheer', 'Naam van de klant'),
            'en': ('Customer management', 'Customer name')})
        self._check(reverse('client_detail', args=[self.client_obj.pk]), {
            'fr': ('Fiche de Contact', 'Lieux associés'), 'nl': ('Contactfiche', 'Gekoppelde locaties'),
            'en': ('Contact details', 'Linked sites')})
        self._check(reverse('client_update', args=[self.client_obj.pk]), {
            'fr': ('Modifier Client', 'Numéro de TVA'), 'nl': ('Klant wijzigen', 'Btw-nummer'),
            'en': ('Edit customer', 'VAT number')})
