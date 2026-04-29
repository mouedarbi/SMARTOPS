"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaires pour la gestion des utilisateurs et des permissions.
"""

from django import forms
from .models import CustomUser

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
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
