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
from schedule.models import Event, Calendar, EventRelation
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from inventory.models import Equipment
from datetime import timedelta
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .calendars import ASSIGNMENT, OWNER, TICKET, assignment_events, get_global_calendar, get_technician_calendar, ticket_event_bounds


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


# Statuts d'une intervention pas encore démarrée, fixés par le système selon le technicien.
NOT_STARTED = ('pending', 'planned')


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
        """Vérifie que les fins prévue et réelle suivent les débuts correspondants."""
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

    def save(self, *args, **kwargs):
        """
        Tant que l'intervention n'a pas démarré, son statut découle de l'assignation :
        « Planifié » avec un technicien, « En attente » sans. Les statuts terrain
        (en cours, terminé, à replanifier) et l'annulation ne sont jamais recalculés.
        """
        if self.status in NOT_STARTED:
            self.status = 'planned' if self.technician_id else 'pending'
            update_fields = kwargs.get('update_fields')
            if update_fields is not None and 'technician' in update_fields:
                kwargs['update_fields'] = {*update_fields, 'status'}
        super().save(*args, **kwargs)

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
    Tient à jour les événements du ticket :
    - l'événement global (créneau prévu), toujours dans le calendrier global ;
    - sa copie dans le calendrier du technicien assigné (heures réelles dès qu'elles existent).
    Retirer ou changer le technicien supprime la copie chez l'ancien.
    """
    # Titre dynamique avec statut
    status_label = instance.get_status_display().upper()
    fields = {
        'title': f"[{status_label}] INT-{instance.id}: {instance.equipment.name}",
        'description': f"Type: {instance.get_type_display()}\nTechnicien: {instance.technician}\nStatut: {status_label}",
    }

    global_calendar = get_global_calendar()
    if created or not instance.event:
        event = Event.objects.create(
            start=instance.planned_start, end=instance.planned_end, calendar=global_calendar, **fields
        )
        EventRelation.objects.create_relation(event, instance, TICKET)
        # On met à jour l'instance sans redéclencher le signal
        MaintenanceTicket.objects.filter(pk=instance.pk).update(event=event)
        instance.event = event
    else:
        _update_event(instance.event, instance.planned_start, instance.planned_end, global_calendar, fields)

    copies = assignment_events(instance)
    # Sans technicien, ou annulé : plus rien dans le calendrier d'un technicien.
    if instance.technician_id is None or instance.status == 'canceled':
        copies.delete()
        return
    calendar = get_technician_calendar(instance.technician)
    copies.exclude(calendar=calendar).delete()
    start, end = ticket_event_bounds(instance)
    copy = copies.filter(calendar=calendar).first()
    if copy:
        _update_event(copy, start, end, calendar, fields)
    else:
        copy = Event.objects.create(start=start, end=end, calendar=calendar, **fields)
        EventRelation.objects.create_relation(copy, instance, ASSIGNMENT)


def _update_event(event, start, end, calendar, fields):
    """Applique créneau, calendrier, titre et description à un événement existant."""
    event.start, event.end, event.calendar = start, end, calendar
    for name, value in fields.items():
        setattr(event, name, value)
    event.save()

@receiver(post_delete, sender=MaintenanceTicket)
def delete_maintenance_event(sender, instance, **kwargs):
    """
    Supprime l'événement global et la copie du technicien lors de la suppression d'un ticket.
    """
    assignment_events(instance).delete()
    if instance.event:
        instance.event.delete()

# --- SIGNALS POUR CALENDRIERS TECHNICIENS ---

@receiver(post_save, sender=Technician)
def create_technician_calendar(sender, instance, created, **kwargs):
    """
    Donne à chaque nouveau technicien son propre calendrier.
    """
    if created:
        get_technician_calendar(instance)

@receiver(pre_delete, sender=Technician)
def delete_technician_calendar(sender, instance, **kwargs):
    """
    Supprime le calendrier d'un technicien et ses copies d'événements. Les événements du
    calendrier global restent : les tickets pourront être réassignés.
    """
    Calendar.objects.get_calendars_for_object(instance, distinction=OWNER).delete()

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
