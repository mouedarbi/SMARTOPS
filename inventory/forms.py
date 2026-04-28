from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un client.
    """
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
