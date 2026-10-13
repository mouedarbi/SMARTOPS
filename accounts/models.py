"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.2
Description : Modèle utilisateur personnalisé avec gestion du soft-delete et contraintes d'intégrité.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, ngettext

class CustomUser(AbstractUser):
    """
    Utilisateur SMARTOPS avec un rôle métier (administrateur, gestionnaire, technicien)
    et une suppression logique qui conserve l'historique.
    """
    ROLE_CHOICES = (
        ('admin', _('Administrateur')),
        ('manager', _('Gestionnaire')),
        ('technician', _('Technicien')),
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='technician',
        verbose_name=_("Rôle")
    )
    # Langue de l'interface choisie par l'utilisateur (français par défaut).
    language = models.CharField(
        max_length=5,
        choices=settings.LANGUAGES,
        default='fr',
        verbose_name=_("Langue"),
    )
    is_deleted = models.BooleanField(
        default=False, 
        verbose_name=_("Est supprimé")
    )
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("Date de suppression")
    )

    def clean(self):
        """
        Un technicien qui a encore des interventions planifiées ou en cours garde son rôle :
        il faut d'abord les réassigner (sinon elles perdraient leur technicien).
        """
        super().clean()
        if not self.pk or self.role == 'technician':
            return
        previous_role = CustomUser.objects.filter(pk=self.pk).values_list('role', flat=True).first()
        if previous_role != 'technician':
            return
        from maintenance.models import OPEN_ASSIGNED_STATUSES, MaintenanceTicket
        count = MaintenanceTicket.objects.filter(technician__user_id=self.pk, status__in=OPEN_ASSIGNED_STATUSES).count()
        if count:
            raise ValidationError({'role': ngettext(
                "Ce technicien a encore %(count)s intervention planifiée ou en cours : réassignez-la avant de changer son rôle.",
                "Ce technicien a encore %(count)s interventions planifiées ou en cours : réassignez-les avant de changer son rôle.",
                count,
            ) % {'count': count}})

    def soft_delete(self):
        """Suppression logique : marque le compte supprimé et date la suppression."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        """Vrai si l'utilisateur est administrateur."""
        return self.role == 'admin'

    @property
    def is_manager(self):
        """Vrai si l'utilisateur est gestionnaire."""
        return self.role == 'manager'

    @property
    def is_technician(self):
        """Vrai si l'utilisateur est technicien."""
        return self.role == 'technician'

    @property
    def initials(self):
        """Initiales pour l'avatar : prénom + nom, sinon les deux premières lettres de l'identifiant."""
        letters = (self.first_name[:1] + self.last_name[:1]) or self.username[:2]
        return letters.upper()

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(is_deleted=True, deleted_at__isnull=True),
                name="customuser_deleted_at_required_if_deleted",
            )
        ]
