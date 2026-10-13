"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routes des écrans d'inventaire (clients, lieux, équipements, étiquettes QR).
"""

from django.urls import path
from .views import (
    client_list_view, client_create_view, client_update_view, client_detail_view,
    building_list_view, building_create_view, building_update_view, building_detail_view,
    equipment_list_view, equipment_create_view, equipment_detail_view,
    equipment_type_list_view, equipment_type_detail_view,
    equipment_public_report_view, equipment_qrcode_svg_view,
    equipment_label_view, building_labels_view,
    client_archive_view, building_archive_view, equipment_archive_view,
)

urlpatterns = [
    path('clients/', client_list_view, name='client_list'),
    path('clients/new/', client_create_view, name='client_create'),
    path('clients/<int:pk>/', client_detail_view, name='client_detail'),
    path('clients/<int:pk>/edit/', client_update_view, name='client_update'),
    path('clients/<int:pk>/archive/', client_archive_view, {'action': 'archive'}, name='client_archive'),
    path('clients/<int:pk>/restore/', client_archive_view, {'action': 'restore'}, name='client_restore'),
    path('buildings/', building_list_view, name='building_list'),
    path('buildings/new/', building_create_view, name='building_create'),
    path('buildings/<int:pk>/', building_detail_view, name='building_detail'),
    path('buildings/<int:pk>/edit/', building_update_view, name='building_update'),
    path('buildings/<int:pk>/labels/', building_labels_view, name='building_labels'),
    path('buildings/<int:pk>/archive/', building_archive_view, {'action': 'archive'}, name='building_archive'),
    path('buildings/<int:pk>/restore/', building_archive_view, {'action': 'restore'}, name='building_restore'),
    path('equipments/', equipment_list_view, name='equipment_list'),
    path('equipments/new/', equipment_create_view, name='equipment_create'),
    path('equipments/<int:pk>/', equipment_detail_view, name='equipment_detail'),
    path('equipments/<int:pk>/label/', equipment_label_view, name='equipment_label'),
    path('equipments/<int:pk>/archive/', equipment_archive_view, {'action': 'archive'}, name='equipment_archive'),
    path('equipments/<int:pk>/restore/', equipment_archive_view, {'action': 'restore'}, name='equipment_restore'),
    path('equipment/<str:serial_number>/report/', equipment_public_report_view, name='equipment_public_report'),
    path('equipment/<str:serial_number>/qrcode.svg', equipment_qrcode_svg_view, name='equipment_qrcode_svg'),
    path('public/equipment/<str:serial_number>/', equipment_public_report_view, name='equipment_public_report_alt'),
    path('types/', equipment_type_list_view, name='equipment_type_list'),
    path('types/<int:pk>/', equipment_type_detail_view, name='equipment_type_detail'),
]
