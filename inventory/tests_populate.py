"""
Fichier : tests_populate.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Tests du script de peuplement des données de démonstration.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician
from inventory.populate_data import run_population

User = get_user_model()

class PopulateDataTests(TestCase):
    def test_run_population(self):
        """
        Le script de peuplement crée tous les objets attendus, sans erreur,
        et dans les quantités prévues.
        """
        # Peuplement dans l'environnement de test (base de test vide, en mémoire)
        run_population()

        # 1. Utilisateurs
        # Administrateur : 1 attendu (la base de test est vide au départ)
        admin_count = User.objects.filter(role='admin').count()
        self.assertEqual(admin_count, 1)

        # Gestionnaires : 2 attendus
        manager_count = User.objects.filter(role='manager').count()
        self.assertEqual(manager_count, 2)

        # Techniciens : 20 attendus
        technician_user_count = User.objects.filter(role='technician').count()
        self.assertEqual(technician_user_count, 20)

        # Profils : le profil technicien est créé automatiquement par le signal post_save
        technician_profile_count = Technician.objects.count()
        self.assertEqual(technician_profile_count, 20)

        # 2. Catégories (EquipmentType)
        # 5 catégories attendues (ascenseur, CVC, détecteur de fumée, extincteur, alarme incendie)
        self.assertEqual(EquipmentType.objects.count(), 5)

        # 3. Clients
        # 50 clients attendus
        self.assertEqual(Client.objects.count(), 50)

        # 4. Lieux
        # Au moins 1 lieu par client (soit 50 lieux)
        self.assertEqual(Building.objects.count(), 50)

        # 5. Équipements
        # 10 équipements par client (soit 500 équipements)
        self.assertEqual(Equipment.objects.count(), 500)

        # 6. Un équipement a bien des champs personnalisés
        sample_equipment = Equipment.objects.first()
        self.assertIsNotNone(sample_equipment)
        self.assertGreater(len(sample_equipment.custom_fields), 0)
        print(f"Test vérifié avec succès : {sample_equipment.name} possède des attributs personnalisés : {sample_equipment.custom_fields}")
