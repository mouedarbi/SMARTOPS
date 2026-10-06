"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : api
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routeur DRF pour l'API REST SMARTOPS v0.2.0.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views import (
    ThrottledTokenObtainPairView,
    MeView,
    ClientViewSet,
    BuildingViewSet,
    EquipmentTypeViewSet,
    EquipmentViewSet,
    TechnicianViewSet,
    MaintenanceTicketViewSet,
    MyInterventionsView,
    MobileLicenseVerifyView,
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
    path('auth/token/', ThrottledTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/me/', MeView.as_view(), name='api_me'),

    # Technicien mobile
    path('my/interventions/', MyInterventionsView.as_view(), name='api_my_interventions'),
    path('mobile/license/verify/', MobileLicenseVerifyView.as_view(), name='api_mobile_license_verify'),

    # Resources REST
    path('', include(router.urls)),

    # Documentation OpenAPI / Swagger
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_swagger'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api_schema'), name='api_redoc'),
]
