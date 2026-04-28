from django import forms
from .models import Client, Building, Equipment, EquipmentType

class ClientForm(forms.ModelForm):
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
    class Meta:
        model = Building
        fields = ['client', 'name', 'address']
        widgets = {
            'client': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl', 'rows': 2}),
        }

class EquipmentForm(forms.ModelForm):
    """
    Formulaire pour la création d'équipement.
    """
    class Meta:
        model = Equipment
        fields = ['building', 'name', 'equipment_type', 'serial_number', 'installed_at']
        widgets = {
            'building': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'equipment_type': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'serial_number': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'installed_at': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
        }
