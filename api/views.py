"""
Fichier : views.py
Application : api
Description : ViewSets DRF pour l'API REST SMARTOPS v0.2.0.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter

from accounts.models import CustomUser
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician, MaintenanceTicket

from .serializers import (
    UserSerializer,
    ClientSerializer,
    BuildingSerializer,
    EquipmentTypeSerializer,
    EquipmentSerializer,
    TechnicianSerializer,
    MaintenanceTicketSerializer,
    TicketStartSerializer,
    TicketStopSerializer,
)
from .permissions import IsAdminOrManager, IsAdminOnly, IsTechnicianOwner


@extend_schema(tags=['Auth'])
class MeView(APIView):
    """Retourne les informations de l'utilisateur authentifié."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@extend_schema(tags=['Inventaire'])
class ClientViewSet(viewsets.ModelViewSet):
    """CRUD complet sur les clients B2B."""
    queryset = Client.objects.all().order_by('name')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


@extend_schema(tags=['Inventaire'])
class BuildingViewSet(viewsets.ModelViewSet):
    """CRUD complet sur les bâtiments."""
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        qs = Building.objects.select_related('client').order_by('name')
        client_id = self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs


@extend_schema(tags=['Inventaire'])
class EquipmentTypeViewSet(viewsets.ModelViewSet):
    """CRUD sur les types d'équipements."""
    queryset = EquipmentType.objects.prefetch_related('fields').order_by('name')
    serializer_class = EquipmentTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


@extend_schema(tags=['Inventaire'])
class EquipmentViewSet(viewsets.ModelViewSet):
    """CRUD complet sur les équipements."""
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Equipment.objects.select_related(
            'building', 'building__client', 'equipment_type'
        ).order_by('name')
        building_id = self.request.query_params.get('building')
        if building_id:
            qs = qs.filter(building_id=building_id)
        return qs


@extend_schema(tags=['Maintenance'])
class TechnicianViewSet(viewsets.ReadOnlyModelViewSet):
    """Liste des techniciens (lecture seule via API)."""
    queryset = Technician.objects.select_related('user').filter(is_active=True)
    serializer_class = TechnicianSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


@extend_schema(tags=['Maintenance'])
class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les tickets de maintenance.
    Les techniciens ne voient que leurs propres tickets.
    """
    serializer_class = MaintenanceTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaintenanceTicket.objects.select_related(
            'equipment', 'technician', 'technician__user'
        ).order_by('-created_at')

        if self.request.user.role == 'technician':
            try:
                tech = self.request.user.technician_profile
                qs = qs.filter(technician=tech)
            except Exception:
                return MaintenanceTicket.objects.none()

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        technician_id = self.request.query_params.get('technician')
        if technician_id and self.request.user.role in ('admin', 'manager'):
            qs = qs.filter(technician_id=technician_id)

        return qs

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAuthenticated(), IsAdminOrManager()]
        return [IsAuthenticated()]

    @extend_schema(
        request=TicketStartSerializer,
        responses=MaintenanceTicketSerializer,
        summary="Démarrer une intervention",
    )
    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """Passe le ticket en `in_progress` et enregistre l'heure de début."""
        ticket = self.get_object()

        if request.user.role == 'technician':
            try:
                if ticket.technician != request.user.technician_profile:
                    return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                return Response({'detail': 'Profil technicien introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.status not in ('pending', 'planned', 'to_reschedule'):
            return Response(
                {'detail': f"Impossible de démarrer un ticket au statut '{ticket.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.status = 'in_progress'
        ticket.effective_start = timezone.now()
        if serializer.validated_data.get('latitude'):
            ticket.start_latitude = serializer.validated_data['latitude']
            ticket.start_longitude = serializer.validated_data['longitude']
        ticket.save()

        return Response(MaintenanceTicketSerializer(ticket).data)

    @extend_schema(
        request=TicketStopSerializer,
        responses=MaintenanceTicketSerializer,
        summary="Terminer une intervention",
    )
    @action(detail=True, methods=['post'], url_path='stop')
    def stop(self, request, pk=None):
        """Passe le ticket en `done` ou `to_reschedule` et enregistre l'heure de fin."""
        ticket = self.get_object()

        if request.user.role == 'technician':
            try:
                if ticket.technician != request.user.technician_profile:
                    return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
            except Exception:
                return Response({'detail': 'Profil technicien introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.status != 'in_progress':
            return Response(
                {'detail': "Seul un ticket 'En cours' peut être terminé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketStopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.status = serializer.validated_data.get('status', 'done')
        ticket.effective_end = timezone.now()
        if serializer.validated_data.get('intervention_report'):
            ticket.intervention_report = serializer.validated_data['intervention_report']
        ticket.save()

        return Response(MaintenanceTicketSerializer(ticket).data)


@extend_schema(tags=['Technicien Mobile'])
class MyInterventionsView(APIView):
    """
    Endpoint dédié à l'app mobile technicien.
    Retourne les interventions du jour ou de la semaine.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=MaintenanceTicketSerializer(many=True),
        parameters=[
            OpenApiParameter('range', description="'today' ou 'week'", default='today'),
        ],
    )
    def get(self, request):
        if request.user.role != 'technician':
            return Response({'detail': 'Réservé aux techniciens.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            tech = request.user.technician_profile
        except Exception:
            return Response({'detail': 'Profil technicien introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)

        range_param = request.query_params.get('range', 'today')
        if range_param == 'week':
            tickets = MaintenanceTicket.objects.filter(
                technician=tech,
                planned_start__gte=today_start,
                planned_start__lt=week_end,
            ).order_by('planned_start')
        else:
            tickets = MaintenanceTicket.objects.filter(
                technician=tech,
                planned_start__gte=today_start,
                planned_start__lt=today_end,
            ).order_by('planned_start')

        serializer = MaintenanceTicketSerializer(tickets, many=True)
        return Response(serializer.data)
