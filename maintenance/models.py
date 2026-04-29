"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Gestion des interventions techniques, des techniciens et 
              synchronisation avec django-scheduler.
"""

from django.db import models
from django.conf import settings
from schedule.models import Event, Calendar
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from inventory.models import Equipment
from datetime import timedelta
from django.utils import timezone

class Technician(models.Model):
    """
    Profil étendu pour les techniciens, lié au CustomUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='technician_profile',
        limit_choices_to={'role': 'technician'}
    )
    specialties = models.JSONField(default=list, blank=True, help_text="Liste des compétences (ex: Electrique, Hydraulique)")
    is_active = models.BooleanField(default=True, verbose_name="Actif")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "Technicien"
        verbose_name_plural = "Techniciens"


class MaintenanceTicket(models.Model):
    """
    Ticket d'intervention lié à un équipement et un technicien.
    Synchronisé avec django-scheduler.
    """
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("planned", "Planifié"),
        ("in_progress", "En cours"),
        ("done", "Terminé"),
        ("canceled", "Annulé"),
    ]

    TYPE_CHOICES = [
        ("maintenance", "Maintenance Préventive"),
        ("repair", "Dépannage / Réparation"),
        ("emergency", "Urgence"),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="maintenance_tickets")
    technician = models.ForeignKey(Technician, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="maintenance")

    # Planification
    planned_start = models.DateTimeField(verbose_name="Début prévu")
    planned_end = models.DateTimeField(verbose_name="Fin prévue")

    # Réalisation (Terrain)
    effective_start = models.DateTimeField(null=True, blank=True, verbose_name="Début réel")
    effective_end = models.DateTimeField(null=True, blank=True, verbose_name="Fin réelle")

    # Géolocalisation
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.TextField(blank=True, verbose_name="Description du problème / travail")
    intervention_report = models.TextField(blank=True, verbose_name="Rapport d'intervention")
    
    # Lien avec django-scheduler
    event = models.OneToOneField(Event, null=True, blank=True, on_delete=models.SET_NULL, related_name="maintenance_ticket")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.equipment.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Ticket de Maintenance"
        verbose_name_plural = "Tickets de Maintenance"


# --- SIGNALS POUR SYNCHRONISATION CALENDRIER ---

@receiver(post_save, sender=MaintenanceTicket)
def sync_maintenance_event(sender, instance, created, **kwargs):
    """
    Crée ou met à jour l'événement dans le calendrier lors de la sauvegarde d'un ticket.
    """
    # Récupération ou création du calendrier principal de maintenance
    calendar, _ = Calendar.objects.get_or_create(
        slug="maintenance-globale",
        defaults={'name': "Calendrier de Maintenance"}
    )

    if created or not instance.event:
        # Création de l'événement
        event = Event.objects.create(
            title=f"INT-{instance.id}: {instance.equipment.name}",
            description=f"Type: {instance.get_type_display()}\nTechnicien: {instance.technician}",
            start=instance.planned_start,
            end=instance.planned_end,
            calendar=calendar
        )
        # On met à jour l'instance sans redéclencher le signal
        MaintenanceTicket.objects.filter(pk=instance.pk).update(event=event)
    else:
        # Mise à jour de l'événement existant
        event = instance.event
        event.title = f"INT-{instance.id}: {instance.equipment.name}"
        event.start = instance.planned_start
        event.end = instance.planned_end
        event.description = f"Type: {instance.get_type_display()}\nTechnicien: {instance.technician}"
        event.save()

@receiver(post_delete, sender=MaintenanceTicket)
def delete_maintenance_event(sender, instance, **kwargs):
    """
    Supprime l'événement lié lors de la suppression d'un ticket.
    """
    if instance.event:
        instance.event.delete()

# --- SIGNALS POUR PROFILS TECHNICIENS ---

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_technician_profile(sender, instance, created, **kwargs):
    """
    Crée automatiquement un profil Technicien si le rôle est 'technician'.
    """
    if instance.role == 'technician' and not instance.is_deleted:
        Technician.objects.get_or_create(user=instance)
    elif instance.role != 'technician':
        # Optionnel : On pourrait désactiver ou supprimer le profil si le rôle change
        Technician.objects.filter(user=instance).delete()
