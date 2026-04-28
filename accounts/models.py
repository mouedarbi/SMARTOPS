from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('manager', 'Gestionnaire'),
        ('technician', 'Technicien'),
        ('consultant', 'Consultant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

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
