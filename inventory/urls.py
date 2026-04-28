from django.urls import path
from .views import (
    client_list_view, client_create_view, client_update_view,
    building_list_view, building_create_view, building_update_view,
    equipment_list_view, equipment_create_view
)

urlpatterns = [
    path('clients/', client_list_view, name='client_list'),
    path('clients/new/', client_create_view, name='client_create'),
    path('clients/<int:pk>/edit/', client_update_view, name='client_update'),
    path('buildings/', building_list_view, name='building_list'),
    path('buildings/new/', building_create_view, name='building_create'),
    path('buildings/<int:pk>/edit/', building_update_view, name='building_update'),
    path('equipments/', equipment_list_view, name='equipment_list'),
    path('equipments/new/', equipment_create_view, name='equipment_create'),
    path('types/', equipment_type_list_view, name='equipment_type_list'),
    path('types/<int:pk>/', equipment_type_detail_view, name='equipment_type_detail'),
]
