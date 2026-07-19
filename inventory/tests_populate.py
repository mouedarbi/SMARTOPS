from django.test import TestCase
from django.contrib.auth import get_user_model
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician
from inventory.populate_data import run_population

User = get_user_model()

class PopulateDataTests(TestCase):
    def test_run_population(self):
        """
        Test that running the populate script creates all expected objects
        without raising any errors, and that count assertions are satisfied.
        """
        # Run population in the test environment (using a clean in-memory test database)
        run_population()

        # 1. Assert Users
        # Admin: we expect 1 admin (since we clean the DB before tests, there are no existing users)
        admin_count = User.objects.filter(role='admin').count()
        self.assertEqual(admin_count, 1)

        # Managers: we expect 2 managers
        manager_count = User.objects.filter(role='manager').count()
        self.assertEqual(manager_count, 2)

        # Technicians: we expect 20 technicians
        technician_user_count = User.objects.filter(role='technician').count()
        self.assertEqual(technician_user_count, 20)

        # Profiles: Technician profile is automatically created via django post_save signal
        technician_profile_count = Technician.objects.count()
        self.assertEqual(technician_profile_count, 20)

        # 2. Assert Categories (EquipmentType)
        # We expect 5 categories (Elevator, CVC, Smoke detector, Fire extinguisher, Fire alarm)
        self.assertEqual(EquipmentType.objects.count(), 5)

        # 3. Assert Clients
        # We expect 50 clients
        self.assertEqual(Client.objects.count(), 50)

        # 4. Assert Buildings
        # We expect at least 1 building per client (so 50 buildings)
        self.assertEqual(Building.objects.count(), 50)

        # 5. Assert Equipments
        # We expect 10 equipments per client (so 500 equipments)
        self.assertEqual(Equipment.objects.count(), 500)

        # 6. Verify that an equipment has custom fields
        sample_equipment = Equipment.objects.first()
        self.assertIsNotNone(sample_equipment)
        self.assertGreater(len(sample_equipment.custom_fields), 0)
        print(f"Test vérifié avec succès : {sample_equipment.name} possède des attributs personnalisés : {sample_equipment.custom_fields}")
