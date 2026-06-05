from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.technician_login, name='technician_login'),
    path('logout/', views.technician_logout, name='technician_logout'),
    path('dashboard/', views.technician_dashboard, name='technician_dashboard'),
    path('ticket/<int:pk>/', views.technician_ticket_detail, name='technician_ticket_detail'),
    path('ticket/<int:pk>/start/', views.start_intervention, name='start_intervention'),
    path('ticket/<int:pk>/stop/', views.stop_intervention, name='stop_intervention'),
]
