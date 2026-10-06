"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : api
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : ViewSets DRF pour l'API REST SMARTOPS v0.2.0.
"""

import hmac
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import CustomUser
from accounts.security import get_client_ip
from licensing.models import Plugin
from inventory.models import Client, Building, EquipmentType, Equipment
from maintenance.models import Technician, MaintenanceTicket, InterventionPhoto
from maintenance.services import reschedule_ticket, with_display_start

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
    InterventionPhotoSerializer,
)
from .permissions import IsAdminOrManager, IsAdminOnly, IsTechnicianOwner
from .throttles import MobileLicenseRateThrottle, TokenObtainRateThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Obtention du jeton JWT, limitée par adresse IP."""
    throttle_classes = [TokenObtainRateThrottle]


@extend_schema(tags=['Auth'])
class MeView(APIView):
    """Retourne les informations de l'utilisateur authentifié."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        """Renvoie l'utilisateur authentifié."""
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
    """CRUD complet sur les lieux."""
    serializer_class = BuildingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        """Lieux par nom, filtrables par client (?client=)."""
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
    """CRUD complet sur les équipements (administrateurs et gestionnaires)."""
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        """Équipements par nom, filtrables par lieu (?building=)."""
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
        """
        Tickets du plus récent au plus ancien ; un technicien ne voit que les siens.
        Filtres : ?status= et, pour la gestion, ?technician=.
        """
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
        """
        Création, modification et suppression : administrateur ou gestionnaire ;
        actions terrain : technicien du ticket.
        """
        # Création et modification : gestionnaire (CDC F5) ; actions terrain : technicien du ticket.
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdminOrManager()]
        if self.action in ('start', 'stop', 'photos'):
            return [IsAuthenticated(), IsTechnicianOwner()]
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

        if ticket.status not in ('pending', 'planned'):
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
        """
        Passe le ticket en `done` ou `to_reschedule` et enregistre l'heure de fin.
        En `to_reschedule`, un ticket de suite est créé en attente, sans technicien.
        """
        ticket = self.get_object()

        if ticket.status != 'in_progress':
            return Response(
                {'detail': "Seul un ticket 'En cours' peut être terminé."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TicketStopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = serializer.validated_data.get('intervention_report') or None
        if serializer.validated_data.get('status') == 'to_reschedule':
            reschedule_ticket(ticket, report)
        else:
            ticket.status = 'done'
            ticket.effective_end = timezone.now()
            if report:
                ticket.intervention_report = report
            ticket.save()

        return Response(MaintenanceTicketSerializer(ticket).data)

    @extend_schema(
        request=InterventionPhotoSerializer,
        responses=InterventionPhotoSerializer(many=True),
        summary="Lister ou ajouter des photos d'intervention",
    )
    @action(detail=True, methods=['get', 'post'], url_path='photos',
            parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        """GET : photos du ticket. POST (multipart) : ajoute une photo."""
        ticket = self.get_object()

        if request.method == 'GET':
            qs = ticket.photos.select_related('uploaded_by').all()
            return Response(InterventionPhotoSerializer(qs, many=True).data)

        serializer = InterventionPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(ticket=ticket, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        """
        Interventions du technicien connecté, datées par leur début effectif
        s'il existe : aujourd'hui (par défaut) ou la semaine (?range=week).
        """
        if request.user.role != 'technician':
            return Response({'detail': 'Réservé aux techniciens.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            tech = request.user.technician_profile
        except Exception:
            return Response({'detail': 'Profil technicien introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        # Bornes du jour dans le fuseau local (TIME_ZONE), pas en UTC
        today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)

        # Datation : début effectif si démarrée, sinon début prévu
        range_end = week_end if request.query_params.get('range', 'today') == 'week' else today_end
        tickets = with_display_start(MaintenanceTicket.objects.filter(technician=tech)).filter(
            display_start__gte=today_start,
            display_start__lt=range_end,
        ).order_by('display_start')

        serializer = MaintenanceTicketSerializer(tickets, many=True)
        return Response(serializer.data)


MOBILE_MODULE_SLUG = 'smartops-mobile'
mobile_logger = logging.getLogger('api.mobile')


@extend_schema(
    tags=['Technicien mobile'], auth=[],
    request=inline_serializer('MobileLicenseVerifyRequest', {'license_key': serializers.CharField()}),
    responses={
        200: inline_serializer('MobileLicenseValid', {
            'valid': serializers.BooleanField(), 'module': serializers.CharField(), 'version': serializers.CharField(),
        }),
        403: inline_serializer('MobileLicenseInvalid', {'valid': serializers.BooleanField(), 'detail': serializers.CharField()}),
    },
)
class MobileLicenseVerifyView(APIView):
    """
    Vérifie la clé de licence saisie dans l'application mobile à sa configuration.
    Contrôle local (module SmartOps Mobile installé et actif sur ce Core), sans appel au Portail.
    Même réponse 403 pour une clé fausse et un module absent ; la clé n'est jamais journalisée.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [MobileLicenseRateThrottle]

    def post(self, request):
        """
        Vérifie la clé saisie dans l'application : 200 si elle est celle du module
        SmartOps Mobile actif, sinon 403.
        """
        key = request.data.get('license_key') if hasattr(request.data, 'get') else None
        key = key.strip() if isinstance(key, str) else ''
        plugin = Plugin.objects.filter(slug=MOBILE_MODULE_SLUG, is_active=True).first()
        ip = get_client_ip(request)

        if key and plugin and plugin.license_key and hmac.compare_digest(
            key.encode(), plugin.license_key.strip().encode()
        ):
            mobile_logger.info("Licence mobile valide (IP %s).", ip)
            return Response({'valid': True, 'module': MOBILE_MODULE_SLUG, 'version': plugin.version})

        mobile_logger.warning("Licence mobile refusée (IP %s).", ip)
        return Response(
            {'valid': False, 'detail': 'Licence mobile invalide ou inactive.'},
            status=status.HTTP_403_FORBIDDEN,
        )
