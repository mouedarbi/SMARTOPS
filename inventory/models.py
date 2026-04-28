"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.1
Description : Modèles d'équipement avec gestion dynamique des champs personnalisés.
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
    phone = models.CharField(max_length=50, verbose_name=_("Téléphone"), blank=True)
    vat_number = models.CharField(max_length=50, verbose_name=_("Numéro de TVA"), blank=True)
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

class EquipmentType(models.Model):
    """
    Définit une catégorie d'équipement (ex: HVAC, Ascenseur).
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nom du type"))
    
    class Meta:
        verbose_name = _("Type d'équipement")
        verbose_name_plural = _("Types d'équipement")

    def __str__(self):
        return self.name

class EquipmentTypeField(models.Model):
    """
    Définit les champs additionnels requis pour un type d'équipement.
    """
    FIELD_TYPES = (
        ('text', _('Texte')),
        ('number', _('Nombre')),
        ('date', _('Date')),
    )
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE, related_name='fields', verbose_name=_("Type"))
    field_name = models.CharField(max_length=100, verbose_name=_("Nom du champ"))
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, verbose_name=_("Type de champ"))
    required = models.BooleanField(default=False, verbose_name=_("Requis"))

    class Meta:
        verbose_name = _("Champ personnalisé")
        verbose_name_plural = _("Champs personnalisés")

    def __str__(self):
        return f"{self.field_name} ({self.equipment_type.name})"

class Equipment(models.Model):
    """
    Entité principale d'équipement avec des attributs communs et dynamiques.
    """
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='equipments', verbose_name=_("Bâtiment"))
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'équipement"))
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.PROTECT, verbose_name=_("Type"))
    serial_number = models.CharField(max_length=100, unique=True, verbose_name=_("Numéro de série"))
    installed_at = models.DateField(verbose_name=_("Date d'installation"))
    
    # Stockage des valeurs des champs personnalisés
    custom_fields = models.JSONField(default=dict, blank=True, verbose_name=_("Champs personnalisés"))

    class Meta:
        verbose_name = _("Équipement")
        verbose_name_plural = _("Équipements")

    def __str__(self):
        return f"{self.name} ({self.serial_number})"
