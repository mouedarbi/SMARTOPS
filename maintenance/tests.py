"""
Fichier : tests.py
Application : maintenance
Auteur : Mohamed Ouedarbi
Description : Tests unitaires du modèle MaintenanceTicket et des contraintes d'intégrité temporelle.
"""

from django.test import TestCase, override_settings
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
