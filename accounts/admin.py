from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'is_staff', 'is_deleted']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Métier', {'fields': ('role', 'is_deleted', 'deleted_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations Métier', {'fields': ('role',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
