"""
Fichier : serializers.py
Projet : SMARTOPS (Core Application)
Application : api
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Sérialiseurs DRF pour tous les modèles SMARTOPS.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema_field
from accounts.models import CustomUser


class SmartOpsTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Jeton JWT enrichi du rôle de l'utilisateur."""
    @classmethod
    def get_token(cls, user):
        """Ajoute le rôle de l'utilisateur dans le jeton."""
        token = super().get_token(user)
        token['role'] = user.role
        return token
from inventory.models import Client, Building, EquipmentType, EquipmentTypeField, Equipment
from maintenance.models import Technician, MaintenanceTicket, InterventionPhoto
from maintenance.services import NOT_STARTED, find_schedule_conflict, schedule_conflict_message


class UserSerializer(serializers.ModelSerializer):
    """Identité et rôle de l'utilisateur."""
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
        read_only_fields = ['id']


class ClientSerializer(serializers.ModelSerializer):
    """Client B2B."""
    class Meta:
        model = Client
        fields = ['id', 'name', 'address', 'contact_name', 'email', 'phone', 'vat_number', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class BuildingSerializer(serializers.ModelSerializer):
    """Lieu d'un client, avec le nom du client."""
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'client', 'client_name', 'name', 'address']
        read_only_fields = ['id']


class EquipmentTypeFieldSerializer(serializers.ModelSerializer):
    """Champ personnalisé d'un type d'équipement."""
    class Meta:
        model = EquipmentTypeField
        fields = ['id', 'field_name', 'field_type', 'required']


class EquipmentTypeSerializer(serializers.ModelSerializer):
    """Type d'équipement avec ses champs personnalisés."""
    fields = EquipmentTypeFieldSerializer(many=True, read_only=True)

    class Meta:
        model = EquipmentType
        fields = ['id', 'name', 'fields']


class EquipmentSerializer(serializers.ModelSerializer):
    """Équipement, avec les noms de son lieu et de son type."""
    building_name = serializers.CharField(source='building.name', read_only=True)
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    client_name = serializers.CharField(source='building.client.name', read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id', 'building', 'building_name', 'client_name',
            'name', 'equipment_type', 'equipment_type_name',
            'serial_number', 'installed_at', 'custom_fields',
        ]
        read_only_fields = ['id']


class TechnicianSerializer(serializers.ModelSerializer):
    """Technicien avec son compte utilisateur."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = Technician
        fields = ['id', 'user', 'specialties', 'is_active']


class InterventionPhotoSerializer(serializers.ModelSerializer):
    """Photo d'intervention (avant, pendant, après), avec son auteur."""
    phase_display = serializers.CharField(source='get_phase_display', read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InterventionPhoto
        fields = ['id', 'ticket', 'image', 'caption', 'phase', 'phase_display',
                  'uploaded_by', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['id', 'ticket', 'uploaded_by', 'uploaded_at']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_uploaded_by_name(self, obj):
        """Nom complet de l'auteur de la photo, ou son identifiant."""
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    """Ticket de maintenance avec ses libellés et ses photos."""
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    technician_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    photos = InterventionPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceTicket
        fields = [
            'id', 'equipment', 'equipment_name',
            'technician', 'technician_name',
            'type', 'type_display',
            'planned_start', 'planned_end',
            'effective_start', 'effective_end',
            'start_latitude', 'start_longitude',
            'status', 'status_display',
            'description', 'intervention_report',
            'photos',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'effective_start', 'effective_end', 'created_at', 'updated_at']

    def validate(self, attrs):
        """
        Vérifie que la fin prévue suit le début prévu et refuse un conflit de
        planning avec une autre intervention du même technicien.
        """
        attrs = super().validate(attrs)
        instance = self.instance

        def current(field):
            return attrs[field] if field in attrs else getattr(instance, field, None)

        start, end = current('planned_start'), current('planned_end')
        if start and end and end <= start:
            raise serializers.ValidationError({'planned_end': "La date de fin prévue doit être postérieure à la date de début prévue."})

        # Conflit de planning : seulement pour une intervention pas encore démarrée, avec un technicien.
        status = current('status') or 'pending'
        if status in NOT_STARTED:
            conflict = find_schedule_conflict(current('technician'), start, end, exclude_pk=getattr(instance, 'pk', None))
            if conflict:
                raise serializers.ValidationError({'planned_start': f"Conflit de planning : {schedule_conflict_message(conflict)}"})
        return attrs

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_technician_name(self, obj):
        """Nom du technicien affecté, ou None."""
        if obj.technician:
            return str(obj.technician)
        return None


class TicketStartSerializer(serializers.Serializer):
    """Démarrage d'une intervention : position GPS facultative."""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class TicketStopSerializer(serializers.Serializer):
    """Clôture d'une intervention : rapport et statut final (terminée ou à replanifier)."""
    intervention_report = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['done', 'to_reschedule'],
        default='done',
    )
