"""
Fichier : models.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.2
Description : Modèle utilisateur personnalisé avec gestion du soft-delete et contraintes d'intégrité.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', _('Administrateur')),
        ('manager', _('Gestionnaire')),
        ('technician', _('Technicien')),
        ('consultant', _('Consultant')),
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='technician',
        verbose_name=_("Rôle")
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

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_technician(self):
        return self.role == 'technician'

    @property
    def is_consultant(self):
        return self.role == 'consultant'

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(is_deleted=True, deleted_at__isnull=True),
                name="customuser_deleted_at_required_if_deleted",
            )
        ]
