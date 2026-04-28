from django.urls import path
from .views import (
    client_list_view, client_create_view, client_update_view,
    building_list_view, building_create_view, building_update_view
)

urlpatterns = [
    path('clients/', client_list_view, name='client_list'),
    path('clients/new/', client_create_view, name='client_create'),
    path('clients/<int:pk>/edit/', client_update_view, name='client_update'),
    path('buildings/', building_list_view, name='building_list'),
    path('buildings/new/', building_create_view, name='building_create'),
    path('buildings/<int:pk>/edit/', building_update_view, name='building_update'),
]
