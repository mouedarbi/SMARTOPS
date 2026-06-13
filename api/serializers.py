"""
Fichier : serializers.py
Application : api
Description : Sérialiseurs DRF pour tous les modèles SMARTOPS.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema_field
from accounts.models import CustomUser


class SmartOpsTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token
from inventory.models import Client, Building, EquipmentType, EquipmentTypeField, Equipment
from maintenance.models import Technician, MaintenanceTicket


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
        read_only_fields = ['id']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'address', 'contact_name', 'email', 'phone', 'vat_number', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class BuildingSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'client', 'client_name', 'name', 'address']
        read_only_fields = ['id']


class EquipmentTypeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentTypeField
        fields = ['id', 'field_name', 'field_type', 'required']


class EquipmentTypeSerializer(serializers.ModelSerializer):
    fields = EquipmentTypeFieldSerializer(many=True, read_only=True)

    class Meta:
        model = EquipmentType
        fields = ['id', 'name', 'fields']


class EquipmentSerializer(serializers.ModelSerializer):
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
    user = UserSerializer(read_only=True)

    class Meta:
        model = Technician
        fields = ['id', 'user', 'specialties', 'is_active']


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    technician_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

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
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'effective_start', 'effective_end', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_technician_name(self, obj):
        if obj.technician:
            return str(obj.technician)
        return None


class TicketStartSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class TicketStopSerializer(serializers.Serializer):
    intervention_report = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['done', 'to_reschedule'],
        default='done',
    )
