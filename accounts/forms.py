"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaires pour la gestion des utilisateurs et des permissions.
"""

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import CustomUser

INPUT_CLASS = 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'

class CustomUserForm(forms.ModelForm):
    """
    Formulaire pour l'édition d'un utilisateur existant.
    """
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
            'role': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 rounded border-slate-300 focus:ring-blue-500'}),
        }

class CustomUserCreateForm(CustomUserForm):
    """
    Formulaire pour la création d'un utilisateur (avec mot de passe).
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm'}),
        label="Mot de passe"
    )

    class Meta(CustomUserForm.Meta):
        fields = CustomUserForm.Meta.fields + ['password']

    def save(self, commit=True):
        """Enregistre l'utilisateur avec son mot de passe haché."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """
    « Mon profil » : l'utilisateur connecté modifie ses propres nom, prénom et e-mail.
    L'identifiant, le rôle et l'état du compte restent gérés par un administrateur.
    """
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
        }


class ProfilePasswordForm(PasswordChangeForm):
    """Changement de son propre mot de passe (ancien mot de passe exigé, règles de AUTH_PASSWORD_VALIDATORS)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = INPUT_CLASS
