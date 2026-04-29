"""
Fichier : urls.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Routage pour le module de maintenance dans l'admin custom.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/add/', views.ticket_create, name='ticket_create'),
    
    # Techniciens
    path('technicians/', views.technician_list, name='technician_list'),
    path('technicians/<int:pk>/', views.technician_detail, name='technician_detail'),
    
    # Calendrier
    path('calendar/', views.maintenance_calendar, name='maintenance_calendar'),
    path('api/events/', views.api_events, name='api_events'),
    path('api/buildings/', views.api_get_buildings, name='api_get_buildings'),
    path('api/equipments/', views.api_get_equipments, name='api_get_equipments'),
]
