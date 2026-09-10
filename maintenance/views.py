"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour la gestion de la maintenance dans l'admin custom.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import MaintenanceTicket, Technician, InterventionPhoto
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

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_photo' and request.FILES.get('image'):
            phase = request.POST.get('phase', 'during')
            if phase not in dict(InterventionPhoto.PHASE_CHOICES):
                phase = 'during'
            InterventionPhoto.objects.create(
                ticket=ticket,
                image=request.FILES['image'],
                caption=(request.POST.get('caption') or '').strip(),
                phase=phase,
                uploaded_by=request.user,
            )
            messages.success(request, "Photo ajoutée à l'intervention.")

        elif action == 'delete_photo':
            photo = ticket.photos.filter(pk=request.POST.get('photo_id')).first()
            if photo:
                photo.delete()
                messages.success(request, "Photo supprimée.")

        return redirect(reverse('ticket_detail', kwargs={'pk': ticket.id}) + '#photos')

    context = {
        'ticket': ticket,
        'page_title': f"Intervention #{ticket.id}",
        'closure': _build_closure_summary(ticket),
        'photos': ticket.photos.select_related('uploaded_by').all(),
        'timeline': _build_ticket_timeline(ticket),
    }
    return render(request, 'maintenance/ticket_detail.html', context)


def _build_ticket_timeline(ticket):
    """
    Reconstitue l'historique de l'intervention à partir de ses horodatages.
    Aucune table d'audit dédiée : la chronologie est dérivée des champs du ticket
    et des photos rattachées.
    """
    events = []

    if ticket.created_at:
        events.append({'at': ticket.created_at, 'icon': 'la-plus-circle', 'color': 'slate',
                       'label': "Ticket créé", 'detail': ticket.get_type_display()})

    if ticket.planned_start:
        events.append({'at': ticket.planned_start, 'icon': 'la-calendar-check', 'color': 'blue',
                       'label': "Intervention planifiée",
                       'detail': str(ticket.technician) if ticket.technician else "Sans technicien assigné"})

    if ticket.effective_start:
        events.append({'at': ticket.effective_start, 'icon': 'la-play-circle', 'color': 'blue',
                       'label': "Démarrage terrain", 'detail': "Pointage du technicien sur site"})

    for photo in ticket.photos.all():
        events.append({'at': photo.uploaded_at, 'icon': 'la-camera', 'color': 'slate',
                       'label': "Photo ajoutée",
                       'detail': f"{photo.get_phase_display()}"
                                 + (f" — {photo.caption}" if photo.caption else "")})

    if ticket.effective_end:
        events.append({'at': ticket.effective_end, 'icon': 'la-check-circle', 'color': 'emerald',
                       'label': "Clôture terrain", 'detail': ticket.get_status_display()})

    if ticket.updated_at and ticket.created_at and (ticket.updated_at - ticket.created_at).total_seconds() > 1:
        events.append({'at': ticket.updated_at, 'icon': 'la-edit', 'color': 'slate',
                       'label': "Dernière modification de la fiche", 'detail': ""})

    return sorted(events, key=lambda e: e['at'])


def _fmt_duration(minutes):
    """Formate une durée en minutes vers un libellé lisible (ex: '2 h 15')."""
    if minutes is None:
        return None
    minutes = int(round(minutes))
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{sign}{hours} h {mins:02d}"
    if hours:
        return f"{sign}{hours} h"
    return f"{sign}{mins} min"


def _build_closure_summary(ticket):
    """
    Synthèse de clôture pour l'onglet Rapport : durée réelle, durée planifiée
    et écart. Retourne None tant que l'intervention n'a pas démarré sur le terrain.
    """
    if not ticket.effective_start:
        return None

    planned_minutes = None
    if ticket.planned_start and ticket.planned_end:
        planned_minutes = (ticket.planned_end - ticket.planned_start).total_seconds() / 60

    real_minutes = None
    if ticket.effective_end:
        real_minutes = (ticket.effective_end - ticket.effective_start).total_seconds() / 60

    delta_minutes = None
    if planned_minutes is not None and real_minutes is not None:
        delta_minutes = real_minutes - planned_minutes

    return {
        'in_progress': ticket.effective_end is None,
        'planned_label': _fmt_duration(planned_minutes),
        'real_label': _fmt_duration(real_minutes),
        'delta_label': _fmt_duration(delta_minutes),
        'delta_minutes': None if delta_minutes is None else int(round(delta_minutes)),
    }


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
