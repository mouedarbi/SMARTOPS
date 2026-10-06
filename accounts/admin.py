"""
Fichier : admin.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Administration Django des utilisateurs (rôle métier et suppression logique).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    """Administration des utilisateurs : ajoute le rôle métier et la suppression logique."""
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff', 'is_deleted']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Métier', {'fields': ('role', 'is_deleted', 'deleted_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations Métier', {'fields': ('role',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
