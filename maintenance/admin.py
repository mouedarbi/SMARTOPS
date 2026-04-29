"""
Fichier : admin.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Configuration de l'interface d'administration pour la maintenance.
"""

from django.contrib import admin
from .models import Technician, MaintenanceTicket

@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    """
    Gestion des techniciens.
    """
    list_display = ('get_full_name', 'get_email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = "Nom Complet"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"


@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    """
    Gestion des tickets de maintenance.
    """
    list_display = ('id', 'equipment', 'technician', 'type', 'status', 'planned_start')
    list_filter = ('status', 'type', 'technician')
    search_fields = ('equipment__nom', 'description', 'id')
    readonly_fields = ('event', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Informations Générales', {
            'fields': ('equipment', 'technician', 'type', 'status')
        }),
        ('Planification', {
            'fields': ('planned_start', 'planned_end', 'event')
        }),
        ('Détails & Travail effectué', {
            'fields': ('description', 'intervention_report')
        }),
        ('Données Terrain (Réel)', {
            'fields': ('effective_start', 'effective_end', 'start_latitude', 'start_longitude'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
