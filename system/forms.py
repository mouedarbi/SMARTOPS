"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaire de gestion de la configuration système.
"""

from django import forms
from .models import SystemConfiguration

class SystemConfigurationForm(forms.ModelForm):
    """
    Formulaire pour la mise à jour des informations de l'entreprise.
    L'UUID est exclu pour éviter toute modification accidentelle.
    """
    class Meta:
        model = SystemConfiguration
        fields = [
            'company_name', 'company_address', 'company_phone', 
            'company_email', 'company_website', 'company_vat', 'company_logo'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company_website': forms.URLInput(attrs={'class': 'form-control'}),
            'company_vat': forms.TextInput(attrs={'class': 'form-control'}),
            'company_logo': forms.FileInput(attrs={'class': 'form-control'}),
        }
