from django import forms
from .models import EquipmentType, EquipmentTypeField

class EquipmentTypeForm(forms.ModelForm):
    """
    Formulaire pour la création d'un type d'équipement.
    """
    class Meta:
        model = EquipmentType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
        }

class EquipmentTypeFieldForm(forms.ModelForm):
    """
    Formulaire pour la gestion des champs personnalisés d'un type.
    """
    class Meta:
        model = EquipmentTypeField
        fields = ['field_name', 'field_type', 'required']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'field_type': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'required': forms.CheckboxInput(attrs={'class': 'mr-2'}),
        }
