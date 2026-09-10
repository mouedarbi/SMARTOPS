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

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class Technician(models.Model):
    """
    Profil étendu pour les techniciens, lié au CustomUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='technician_profile',
        limit_choices_to={'role': 'technician'},
        verbose_name=_("Utilisateur")
    )
    specialties = models.JSONField(default=list, blank=True, help_text=_("Liste des compétences (ex: Electrique, Hydraulique)"), verbose_name=_("Spécialités"))
    is_active = models.BooleanField(default=True, verbose_name=_("Actif"))

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = _("Technicien")
        verbose_name_plural = _("Techniciens")


class MaintenanceTicket(models.Model):
    """
    Ticket d'intervention lié à un équipement et un technicien.
    Synchronisé avec django-scheduler.
    """
    STATUS_CHOICES = [
        ("pending", _("En attente")),
        ("planned", _("Planifié")),
        ("in_progress", _("En cours")),
        ("to_reschedule", _("À replanifier")),
        ("done", _("Terminé")),
        ("canceled", _("Annulé")),
    ]

    TYPE_CHOICES = [
        ("maintenance", _("Maintenance Préventive")),
        ("repair", _("Dépannage / Réparation")),
        ("emergency", _("Urgence")),
    ]

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="maintenance_tickets", verbose_name=_("Équipement"))
    technician = models.ForeignKey(Technician, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets", verbose_name=_("Technicien"))
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="maintenance", verbose_name=_("Type d'intervention"))

    # Planification
    planned_start = models.DateTimeField(verbose_name=_("Début prévu"))
    planned_end = models.DateTimeField(verbose_name=_("Fin prévue"))

    # Réalisation (Terrain)
    effective_start = models.DateTimeField(null=True, blank=True, verbose_name=_("Début réel"))
    effective_end = models.DateTimeField(null=True, blank=True, verbose_name=_("Fin réelle"))

    # Géolocalisation
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Latitude de début"))
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_("Longitude de début"))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name=_("Statut"))
    description = models.TextField(blank=True, verbose_name=_("Description du problème / travail"))
    intervention_report = models.TextField(blank=True, verbose_name=_("Rapport d'intervention"))
    
    # Lien avec django-scheduler
    event = models.OneToOneField(Event, null=True, blank=True, on_delete=models.SET_NULL, related_name="maintenance_ticket", verbose_name=_("Événement calendrier"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de mise à jour"))

    def clean(self):
        super().clean()
        errors = {}
        if self.planned_start and self.planned_end:
            if self.planned_end <= self.planned_start:
                errors['planned_end'] = _("La date de fin prévue doit être postérieure à la date de début prévue.")

        if self.effective_start and self.effective_end:
            if self.effective_end <= self.effective_start:
                errors['effective_end'] = _("La date de fin réelle doit être postérieure à la date de début réelle.")

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Ticket #{self.id} - {self.equipment.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = _("Ticket de Maintenance")
        verbose_name_plural = _("Tickets de Maintenance")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(planned_end__gt=models.F("planned_start")),
                name="ticket_planned_end_after_planned_start",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(effective_start__isnull=True)
                    | models.Q(effective_end__isnull=True)
                    | models.Q(effective_end__gt=models.F("effective_start"))
                ),
                name="ticket_effective_end_after_effective_start",
            ),
        ]


class InterventionPhoto(models.Model):
    """
    Photo rattachée à une intervention (preuve terrain : avant / pendant / après).
    Alimentée par le technicien depuis le terrain ou par un gestionnaire.
    """
    PHASE_CHOICES = [
        ("before", _("Avant intervention")),
        ("during", _("Pendant intervention")),
        ("after", _("Après intervention")),
    ]

    ticket = models.ForeignKey(
        MaintenanceTicket,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Intervention"),
    )
    image = models.ImageField(upload_to="interventions/%Y/%m/", verbose_name=_("Photo"))
    caption = models.CharField(max_length=255, blank=True, verbose_name=_("Légende"))
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default="during", verbose_name=_("Moment"))
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="intervention_photos",
        verbose_name=_("Ajoutée par"),
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'ajout"))

    def __str__(self):
        return f"Photo #{self.id} - Intervention #{self.ticket_id}"

    class Meta:
        verbose_name = _("Photo d'intervention")
        verbose_name_plural = _("Photos d'intervention")
        ordering = ["uploaded_at"]


@receiver(post_delete, sender=InterventionPhoto)
def delete_intervention_photo_file(sender, instance, **kwargs):
    """Supprime le fichier physique lorsque la photo est retirée."""
    if instance.image:
        instance.image.delete(save=False)


# --- SIGNALS POUR SYNCHRONISATION CALENDRIER ---

@receiver(post_save, sender=MaintenanceTicket)
def sync_maintenance_event(sender, instance, created, **kwargs):
    """
    Crée ou met à jour l'événement dans le calendrier lors de la sauvegarde d'un ticket.
    Priorise les temps réels (terrain) sur les temps prévus pour un affichage "Live".
    """
    # Récupération ou création du calendrier principal de maintenance
    calendar, _ = Calendar.objects.get_or_create(
        slug="maintenance-globale",
        defaults={'name': "Calendrier de Maintenance"}
    )

    # Détermination des heures à afficher (Réel si dispo, sinon Prévu)
    display_start = instance.effective_start if instance.effective_start else instance.planned_start
    display_end = instance.effective_end if instance.effective_end else instance.planned_end

    # Titre dynamique avec statut
    status_label = instance.get_status_display().upper()
    event_title = f"[{status_label}] INT-{instance.id}: {instance.equipment.name}"

    if created or not instance.event:
        # Création de l'événement
        event = Event.objects.create(
            title=event_title,
            description=f"Type: {instance.get_type_display()}\nTechnicien: {instance.technician}\nStatut: {status_label}",
            start=display_start,
            end=display_end,
            calendar=calendar
        )
        # On met à jour l'instance sans redéclencher le signal
        MaintenanceTicket.objects.filter(pk=instance.pk).update(event=event)
    else:
        # Mise à jour de l'événement existant
        event = instance.event
        event.title = event_title
        event.start = display_start
        event.end = display_end
        event.description = f"Type: {instance.get_type_display()}\nTechnicien: {instance.technician}\nStatut: {status_label}"
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
