"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaires des clients, lieux, équipements et types d'équipements.
"""

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from .models import Client, Building, Equipment, EquipmentType, EquipmentTypeField

class ClientForm(forms.ModelForm):
    """Formulaire pour la création et l'édition d'un client."""
    class Meta:
        model = Client
        fields = ['name', 'address', 'contact_name', 'email', 'phone', 'vat_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl', 'rows': 2}),
            'contact_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'vat_number': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'mr-2'}),
        }

class BuildingForm(forms.ModelForm):
    """Formulaire pour la création et l'édition d'un lieu. Le client est fixé par la vue :
    un lieu se crée depuis la fiche de son client et n'en change jamais."""
    class Meta:
        model = Building
        fields = ['name', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl', 'rows': 2}),
        }

class EquipmentForm(forms.ModelForm):
    """Formulaire pour la création d'équipement. Le lieu est fixé par la vue : un équipement se
    crée depuis la fiche de son lieu."""
    class Meta:
        model = Equipment
        fields = ['name', 'equipment_type', 'serial_number', 'installed_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'equipment_type': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'serial_number': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'installed_at': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
        }

    INPUT_CLASS = 'w-full p-3 border border-slate-200 rounded-xl'

    def __init__(self, *args, **kwargs):
        """Ajoute un champ de saisie par champ personnalisé de chaque type d'équipement ; le gabarit
        n'affiche que ceux du type choisi, et seuls ceux-là sont validés et enregistrés."""
        super().__init__(*args, **kwargs)
        self.custom_field_defs = list(EquipmentTypeField.objects.order_by('equipment_type__name', 'pk'))
        for definition in self.custom_field_defs:
            self.fields[self.custom_key(definition)] = self._custom_form_field(definition)

    @staticmethod
    def custom_key(definition):
        return f'cf_{definition.pk}'

    def _custom_form_field(self, definition):
        """Champ de formulaire selon le type déclaré (nombre, date ou texte), jamais obligatoire ici :
        l'obligation ne vaut que pour le type d'équipement choisi (voir clean)."""
        label = f"{definition.field_name}{' *' if definition.required else ''}"
        if definition.field_type == 'number':
            return forms.FloatField(label=label, required=False, widget=forms.NumberInput(
                attrs={'class': self.INPUT_CLASS, 'step': 'any'}))
        if definition.field_type == 'date':
            return forms.DateField(label=label, required=False, widget=forms.DateInput(
                attrs={'type': 'date', 'class': self.INPUT_CLASS}))
        return forms.CharField(label=label, required=False, max_length=255, widget=forms.TextInput(
            attrs={'class': self.INPUT_CLASS}))

    def standard_fields(self):
        """Champs communs à tous les équipements, dans l'ordre du formulaire."""
        return [self[name] for name in self.Meta.fields]

    def custom_groups(self):
        """Champs personnalisés regroupés par type d'équipement : [(id du type, [champs]), ...]."""
        groups = {}
        for definition in self.custom_field_defs:
            groups.setdefault(definition.equipment_type_id, []).append(self[self.custom_key(definition)])
        return list(groups.items())

    def clean(self):
        """Valide les champs personnalisés du type choisi et les recopie dans custom_fields
        (nombres en nombre, dates au format AAAA-MM-JJ, comme l'API et les données de démo)."""
        cleaned = super().clean()
        equipment_type = cleaned.get('equipment_type')
        values = {}
        for definition in self.custom_field_defs:
            key = self.custom_key(definition)
            if equipment_type is None or definition.equipment_type_id != equipment_type.pk:
                # Champ d'un autre type : ni validé ni enregistré.
                self.errors.pop(key, None)
                continue
            value = cleaned.get(key)
            if value in (None, ''):
                if definition.required and key not in self.errors:
                    self.add_error(key, "Ce champ est requis pour ce type d'équipement.")
                continue
            if isinstance(value, float):
                value = int(value) if value.is_integer() else value
            elif hasattr(value, 'isoformat'):
                value = value.isoformat()
            values[definition.field_name] = value
        self.instance.custom_fields = values
        return cleaned

    def _update_errors(self, errors):
        """Une erreur du modèle sur un champ personnalisé est rattachée à son champ de saisie ;
        une erreur sur un champ inconnu du formulaire devient une erreur générale (jamais une 500)."""
        if hasattr(errors, 'error_dict'):
            keys = {d.field_name: self.custom_key(d) for d in self.custom_field_defs
                    if self.cleaned_data.get('equipment_type') and d.equipment_type_id == self.cleaned_data['equipment_type'].pk}
            remapped = {}
            for name, messages in errors.error_dict.items():
                target = keys.get(name, name)
                if target not in self.fields:
                    target = NON_FIELD_ERRORS
                remapped.setdefault(target, []).extend(messages)
            errors = ValidationError(remapped)
        super()._update_errors(errors)

class EquipmentTypeForm(forms.ModelForm):
    """Formulaire pour la création d'un type d'équipement."""
    class Meta:
        model = EquipmentType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
        }

class EquipmentTypeFieldForm(forms.ModelForm):
    """Formulaire pour la gestion des champs personnalisés d'un type."""
    class Meta:
        model = EquipmentTypeField
        fields = ['field_name', 'field_type', 'required']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'field_type': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'required': forms.CheckboxInput(attrs={'class': 'mr-2'}),
        }
