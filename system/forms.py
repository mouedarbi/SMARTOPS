"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : system
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaire de gestion de la configuration système.
"""

from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from .models import SystemConfiguration

class SystemConfigurationForm(forms.ModelForm):
    """
    Formulaire pour la mise à jour des informations de l'entreprise.
    L'UUID est exclu pour éviter toute modification accidentelle.
    """
    company_website = forms.CharField(
        required=False,
        label="Site Web",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'www.exemple.be'}),
    )

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
            'company_vat': forms.TextInput(attrs={'class': 'form-control'}),
            'company_logo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_company_website(self):
        website = self.cleaned_data.get('company_website', '').strip()
        if not website:
            return ""
        
        # Si l'utilisateur n'a pas mis de schéma, on ajoute http:// automatiquement
        if not website.startswith(('http://', 'https://')):
            website = f"http://{website}"
            
        # Validation personnalisée pour autoriser les tirets du bas (_) dans le domaine
        import re
        from urllib.parse import urlparse
        
        try:
            result = urlparse(website)
            if not all([result.scheme, result.netloc]):
                raise ValueError()
            
            hostname = result.netloc.split(':')[0] # enlève le port si présent
            # Autorise les caractères alphanumériques, tirets, underscores et points
            if not re.match(r'^[a-zA-Z0-9_\-\.]+$', hostname):
                raise ValueError()
                
            if '.' not in hostname and hostname != 'localhost':
                raise ValueError()
        except ValueError:
            raise ValidationError(
                "Format attendu : 'www.exemple.com' ou 'https://exemple.com' (les tirets du bas '_' sont autorisés)"
            )
        return website
