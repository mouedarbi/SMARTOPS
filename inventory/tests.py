"""
Fichier : tests.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Tests unitaires pour les modèles de l'application inventaire.
"""

from django.test import TestCase
from .models import Client, Building, Equipment
from datetime import date

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
        self.equipment = Equipment.objects.create(
            building=self.building,
            name="Ascenseur 1",
            equipment_type="elevator",
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
        self.assertEqual(self.equipment.equipment_type, "elevator")
