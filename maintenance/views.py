"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour la gestion de la maintenance dans l'admin custom.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import MaintenanceTicket, Technician
from .forms import MaintenanceTicketForm
from schedule.models import Calendar
from accounts.views import is_management_staff

@login_required
@user_passes_test(is_management_staff)
def ticket_list(request):
    """
    Liste des tickets de maintenance.
    """
    tickets = MaintenanceTicket.objects.all().order_by('-planned_start')
    context = {
        'tickets': tickets,
        'page_title': "Tickets de Maintenance"
    }
    return render(request, 'maintenance/ticket_list.html', context)

@login_required
@user_passes_test(is_management_staff)
def ticket_detail(request, pk):
    """
    Détail et édition d'un ticket de maintenance.
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    if request.method == 'POST':
        form = MaintenanceTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ticket #{ticket.id} mis à jour avec succès.")
            return redirect('ticket_list')
    else:
        form = MaintenanceTicketForm(instance=ticket)
    
    context = {
        'ticket': ticket,
        'form': form,
        'page_title': f"Ticket #{ticket.id}"
    }
    return render(request, 'maintenance/ticket_form.html', context)

@login_required
@user_passes_test(is_management_staff)
def ticket_create(request):
    """
    Création d'un nouveau ticket.
    """
    if request.method == 'POST':
        form = MaintenanceTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save()
            messages.success(request, f"Nouveau ticket #{ticket.id} créé avec succès.")
            return redirect('ticket_list')
    else:
        form = MaintenanceTicketForm()
    
    context = {
        'form': form,
        'page_title': "Nouveau Ticket"
    }
    return render(request, 'maintenance/ticket_form.html', context)

@login_required
@user_passes_test(is_management_staff)
def technician_list(request):
    """
    Liste des techniciens.
    """
    technicians = Technician.objects.all()
    context = {
        'technicians': technicians,
        'active_count': technicians.filter(is_active=True).count(),
        'inactive_count': technicians.filter(is_active=False).count(),
        'page_title': "Équipe Technique"
    }
    return render(request, 'maintenance/technician_list.html', context)

@login_required
@user_passes_test(is_management_staff)
def technician_detail(request, pk):
    """
    Détail d'un technicien.
    """
    technician = get_object_or_404(Technician, pk=pk)
    context = {
        'technician': technician,
        'page_title': f"Profil Technicien : {technician}"
    }
    return render(request, 'maintenance/technician_detail.html', context)

@login_required
@user_passes_test(is_management_staff)
def maintenance_calendar(request):
    """
    Vue calendrier pour la maintenance.
    """
    context = {
        'page_title': "Planning de Maintenance"
    }
    return render(request, 'maintenance/calendar.html', context)

from django.http import JsonResponse

@login_required
@user_passes_test(is_management_staff)
def api_events(request):
    """
    Retourne les événements de maintenance au format JSON pour FullCalendar.
    """
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    tickets = MaintenanceTicket.objects.select_related('equipment', 'technician')
    
    # On pourrait filtrer par date ici si besoin
    
    events = []
    for ticket in tickets:
        events.append({
            'id': ticket.id,
            'title': f"INT-{ticket.id}: {ticket.equipment.nom}",
            'start': ticket.planned_start.isoformat(),
            'end': ticket.planned_end.isoformat(),
            'description': f"Technicien: {ticket.technician}",
            'color': '#3b82f6' if ticket.status != 'emergency' else '#ef4444',
        })
    
    return JsonResponse(events, safe=False)
