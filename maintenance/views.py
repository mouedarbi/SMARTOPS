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
    Vue en lecture seule d'un ticket avec onglets.
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    context = {
        'ticket': ticket,
        'page_title': f"Intervention #{ticket.id}"
    }
    return render(request, 'maintenance/ticket_detail.html', context)

@login_required
@user_passes_test(is_management_staff)
def ticket_update(request, pk):
    """
    Vue d'édition (Planification) du ticket.
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    
    # Sécurité : Pas d'édition si déjà commencé/fini
    if ticket.status in ['in_progress', 'done', 'canceled']:
        messages.warning(request, "Cette intervention ne peut plus être modifiée car elle est déjà en cours ou clôturée.")
        return redirect('ticket_detail', pk=ticket.id)

    if request.method == 'POST':
        form = MaintenanceTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Intervention #{ticket.id} reprogrammée.")
            return redirect('ticket_detail', pk=ticket.id)
    else:
        form = MaintenanceTicketForm(instance=ticket)
    
    context = {
        'ticket': ticket,
        'form': form,
        'page_title': f"Planification #{ticket.id}"
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
@user_passes_test(lambda u: u.is_superuser)
def ticket_delete(request, pk):
    """
    Suppression d'un ticket (réservé aux SuperAdmins).
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    ticket_id = ticket.id
    ticket.delete()
    messages.success(request, f"Intervention #{ticket_id} supprimée définitivement.")
    return redirect('ticket_list')

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
from .forms import MaintenanceTicketForm, TechnicianForm

@login_required
@user_passes_test(is_management_staff)
def technician_detail(request, pk):
    """
    Détail et édition d'un technicien avec statistiques de performance.
    """
    technician = get_object_or_404(Technician, pk=pk)
    tickets = technician.tickets.all()
    
    # Calcul des statistiques
    total_tickets = tickets.count()
    done_tickets = tickets.filter(status='done').count()
    completion_rate = (done_tickets / total_tickets * 100) if total_tickets > 0 else 0
    
    # Calcul de la durée moyenne des interventions terminées
    avg_duration_minutes = 0
    completed_with_time = tickets.filter(status='done', effective_start__isnull=False, effective_end__isnull=False)
    if completed_with_time.exists():
        total_duration = sum([(t.effective_end - t.effective_start).total_seconds() for t in completed_with_time], 0)
        avg_duration_minutes = (total_duration / completed_with_time.count()) / 60

    if request.method == 'POST':
        form = TechnicianForm(request.POST, instance=technician)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profil de {technician} mis à jour.")
            return redirect('technician_list')
    else:
        form = TechnicianForm(instance=technician)

    context = {
        'technician': technician,
        'form': form,
        'page_title': f"Profil Technicien : {technician}",
        'stats': {
            'total': total_tickets,
            'done': done_tickets,
            'completion_rate': round(completion_rate, 1),
            'avg_duration': round(avg_duration_minutes, 0),
            'pending': tickets.filter(status__in=['pending', 'planned', 'in_progress']).count()
        }
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
def api_get_buildings(request):
    client_id = request.GET.get('client_id')
    from inventory.models import Building
    buildings = Building.objects.filter(client_id=client_id).values('id', 'name')
    return JsonResponse(list(buildings), safe=False)

@login_required
@user_passes_test(is_management_staff)
def api_get_equipments(request):
    building_id = request.GET.get('building_id')
    search = request.GET.get('search')
    from inventory.models import Equipment
    
    equipments = Equipment.objects.all()
    if building_id:
        equipments = equipments.filter(building_id=building_id)
    if search:
        equipments = equipments.filter(serial_number__icontains=search) | equipments.filter(name__icontains=search)
        
    data = [{'id': e.id, 'text': f"{e.name} ({e.serial_number}) - {e.building.name}"} for e in equipments[:20]]
    return JsonResponse(data, safe=False)

@login_required
@user_passes_test(is_management_staff)
def api_events(request):
    """
    Retourne les événements de maintenance au format JSON pour FullCalendar.
    Priorise les temps réels pour un affichage "Live".
    """
    tickets = MaintenanceTicket.objects.select_related('equipment', 'technician', 'equipment__building')
    
    events = []
    for ticket in tickets:
        # Détermination des heures à afficher (Réel si dispo, sinon Prévu)
        display_start = ticket.effective_start if ticket.effective_start else ticket.planned_start
        display_end = ticket.effective_end if ticket.effective_end else ticket.planned_end

        # Titre dynamique avec statut
        status_label = ticket.get_status_display().upper()
        
        # Détermination de la couleur basée sur le statut
        color = '#64748b' # Default (Slate 500)
        if ticket.status == 'in_progress':
            color = '#3b82f6' # Blue 500
        elif ticket.status == 'done':
            color = '#10b981' # Emerald 500
        elif ticket.status == 'to_reschedule':
            color = '#f59e0b' # Amber 500
        elif ticket.status == 'pending':
            color = '#f59e0b' # Amber 500 (orange)
        elif ticket.type == 'emergency':
            color = '#ef4444' # Red 500

        events.append({
            'id': ticket.id,
            'title': f"[{status_label}] {ticket.equipment.name}",
            'start': display_start.isoformat(),
            'end': display_end.isoformat(),
            'extendedProps': {
                'technician': str(ticket.technician),
                'client': ticket.equipment.building.client.name,
                'building': ticket.equipment.building.name,
                'status': ticket.get_status_display(),
            },
            'backgroundColor': color,
            'borderColor': color,
        })
    
    return JsonResponse(events, safe=False)
