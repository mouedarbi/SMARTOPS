"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Modèles de gestion de l'inventaire des actifs (Clients, Bâtiments, Équipements).
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

class Client(models.Model):
    """
    Représente un client de la plateforme.
    """
    name = models.CharField(max_length=255, verbose_name=_("Nom du Client"))
    address = models.TextField(verbose_name=_("Adresse"))
    contact_name = models.CharField(max_length=255, verbose_name=_("Contact"))
    email = models.EmailField(verbose_name=_("Email"))
    is_active = models.BooleanField(default=True, verbose_name=_("Est Actif"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")

    def __str__(self):
        return self.name

class Building(models.Model):
    """
    Représente un bâtiment associé à un client.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='buildings', verbose_name=_("Client"))
    name = models.CharField(max_length=255, verbose_name=_("Nom du Bâtiment"))
    address = models.TextField(verbose_name=_("Adresse du Bâtiment"))

    class Meta:
        verbose_name = _("Bâtiment")
        verbose_name_plural = _("Bâtiments")

    def __str__(self):
        return f"{self.name} ({self.client.name})"

class Equipment(models.Model):
    """
    Représente un équipement technique (ascenseur, HVAC, etc.) dans un bâtiment.
    """
    TYPE_CHOICES = (
        ('hvac', _('Chauffage, Ventilation, Climatisation')),
        ('security', _('Sécurité')),
        ('medical', _('Médical')),
        ('industrial', _('Industriel')),
        ('elevator', _('Ascenseur')),
        ('it', _('Informatique')),
    )
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='equipments', verbose_name=_("Bâtiment"))
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'équipement"))
    equipment_type = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name=_("Type d'équipement"))
    serial_number = models.CharField(max_length=100, unique=True, verbose_name=_("Numéro de série"))
    installed_at = models.DateField(verbose_name=_("Date d'installation"))

    class Meta:
        verbose_name = _("Équipement")
        verbose_name_plural = _("Équipements")

    def __str__(self):
        return f"{self.name} ({self.serial_number})"
