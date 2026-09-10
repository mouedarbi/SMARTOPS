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
    Représente un lieu (site / bâtiment) associé à un client.
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='buildings', verbose_name=_("Client"))
    name = models.CharField(max_length=255, verbose_name=_("Nom du lieu"))
    address = models.TextField(verbose_name=_("Adresse du lieu"))

    class Meta:
        verbose_name = _("Lieu")
        verbose_name_plural = _("Lieux")

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

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
import datetime

class Equipment(models.Model):
    """
    Entité principale d'équipement avec des attributs communs et dynamiques.
    """
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='equipments', verbose_name=_("Lieu"))
    name = models.CharField(max_length=255, verbose_name=_("Nom de l'équipement"))
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.PROTECT, verbose_name=_("Type"))
    serial_number = models.CharField(max_length=100, unique=True, verbose_name=_("Numéro de série"))
    installed_at = models.DateField(verbose_name=_("Date d'installation"))
    
    # Stockage des valeurs des champs personnalisés
    custom_fields = models.JSONField(default=dict, blank=True, verbose_name=_("Champs personnalisés"))

    def clean(self):
        """
        Valide la structure et les types des données dans custom_fields
        selon la définition des EquipmentTypeField associés.
        """
        super().clean()
        if not hasattr(self, 'equipment_type') or not self.equipment_type:
            return

        if self.custom_fields is None:
            self.custom_fields = {}
        elif not isinstance(self.custom_fields, dict):
            raise ValidationError({
                'custom_fields': _("Les champs personnalisés doivent être un objet JSON valide.")
            })

        expected_fields = self.equipment_type.fields.all()
        errors = {}

        for f in expected_fields:
            value = self.custom_fields.get(f.field_name)
            
            # 1. Vérification de l'obligation
            if f.required and (value is None or value == ""):
                errors[f.field_name] = _("Le champ personnalisé '%(name)s' est requis pour ce type d'équipement.") % {'name': f.field_name}
            elif value is not None and value != "":
                # 2. Validation des types
                if f.field_type == "number":
                    if not isinstance(value, (int, float)):
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            errors[f.field_name] = _("Le champ '%(name)s' doit être numérique.") % {'name': f.field_name}
                elif f.field_type == "date":
                    if isinstance(value, (datetime.date, datetime.datetime)):
                        pass
                    elif isinstance(value, str):
                        parsed = parse_date(value)
                        if not parsed:
                            errors[f.field_name] = _("Le champ '%(name)s' doit être une date valide au format AAAA-MM-JJ.") % {'name': f.field_name}
                    else:
                        errors[f.field_name] = _("Le champ '%(name)s' doit être une date valide au format AAAA-MM-JJ.") % {'name': f.field_name}

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = _("Équipement")
        verbose_name_plural = _("Équipements")

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

