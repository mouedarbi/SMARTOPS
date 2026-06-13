"""
Fichier : urls.py
Application : api
Description : Routeur DRF pour l'API REST SMARTOPS v0.2.0.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views import (
    MeView,
    ClientViewSet,
    BuildingViewSet,
    EquipmentTypeViewSet,
    EquipmentViewSet,
    TechnicianViewSet,
    MaintenanceTicketViewSet,
    MyInterventionsView,
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'buildings', BuildingViewSet, basename='building')
router.register(r'equipment-types', EquipmentTypeViewSet, basename='equipment-type')
router.register(r'equipments', EquipmentViewSet, basename='equipment')
router.register(r'technicians', TechnicianViewSet, basename='technician')
router.register(r'tickets', MaintenanceTicketViewSet, basename='ticket')

urlpatterns = [
    # Auth JWT
    path('auth/token/', TokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/me/', MeView.as_view(), name='api_me'),

    # Technicien mobile
    path('my/interventions/', MyInterventionsView.as_view(), name='api_my_interventions'),

    # Resources REST
    path('', include(router.urls)),

    # Documentation OpenAPI / Swagger
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_swagger'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api_schema'), name='api_redoc'),
]
