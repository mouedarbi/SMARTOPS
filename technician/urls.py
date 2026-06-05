from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.technician_login, name='technician_login'),
    path('dashboard/', views.technician_dashboard, name='technician_dashboard'),
]
