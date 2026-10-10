"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour la gestion de la maintenance dans l'admin custom.
"""

import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from .models import MaintenanceTicket, Technician, InterventionPhoto
from .forms import MaintenanceTicketForm, InterventionPhotoForm
from .calendars import assigned_ticket_ids, get_technician_calendar, ticket_event_bounds
from .services import FOLLOW_UP_PREFIX, local_day_range, older_late_count, tickets_to_plan
from accounts.views import is_management_staff

# Colonnes triables de la liste des interventions.
TICKET_LIST_SORTS = ('id', 'created_at', 'planned_start')


@login_required
@user_passes_test(is_management_staff)
def ticket_list(request):
    """
    Liste des interventions en trois onglets :
    - « À planifier » (par défaut) : file des tickets qui attendent le gestionnaire ;
    - « En cours » (?tab=en-cours) : interventions démarrées et pas encore clôturées, quelle que soit
      leur date, du démarrage le plus ancien au plus récent (les clôtures oubliées remontent) ;
    - « Toutes les interventions » (?tab=toutes) : filtres par technicien, date, statut, lieu
      et client, tri par colonne et pagination.
    """
    from inventory.models import Client, Building

    tickets = MaintenanceTicket.objects.select_related(
        'equipment', 'equipment__building', 'equipment__building__client', 'technician__user'
    ).order_by('-planned_start')
    all_tickets = tickets

    # Tri de la liste complète par en-tête de colonne ; par défaut, date prévue la plus récente d'abord.
    sort = request.GET.get('sort')
    sort = sort if sort in TICKET_LIST_SORTS else 'planned_start'
    order = 'asc' if request.GET.get('order') == 'asc' else 'desc'

    technician_id = request.GET.get('technician') or ''
    date_filter = request.GET.get('date') or ''
    status_filter = request.GET.get('status') or ''
    building_id = request.GET.get('building') or ''
    client_id = request.GET.get('client') or ''

    if technician_id == 'none':
        tickets = tickets.filter(technician__isnull=True)
    elif technician_id:
        tickets = tickets.filter(technician_id=technician_id)
    if date_filter:
        try:
            day_start, day_end = local_day_range(datetime.date.fromisoformat(date_filter))
        except ValueError:
            date_filter = ''
        else:
            tickets = tickets.filter(planned_start__gte=day_start, planned_start__lt=day_end)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if building_id:
        tickets = tickets.filter(equipment__building_id=building_id)
    if client_id:
        tickets = tickets.filter(equipment__building__client_id=client_id)

    filtering = any([technician_id, date_filter, status_filter, building_id, client_id])
    tab = request.GET.get('tab')
    if tab not in ('a-planifier', 'en-cours', 'toutes'):
        # Un lien filtré, trié ou paginé sans onglet vise la liste complète.
        tab = 'toutes' if filtering or request.GET.get('sort') or request.GET.get('page') else 'a-planifier'
    in_progress = list(all_tickets.filter(status='in_progress').order_by('effective_start', 'pk'))
    # File « À planifier » : toujours calculée sans filtre, pour le compteur de l'onglet.
    to_plan = tickets_to_plan(all_tickets)
    tickets = tickets.order_by(f"{'-' if order == 'desc' else ''}{sort}", '-pk')

    paginator = Paginator(tickets, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Pour préserver les filtres actifs dans les liens de pagination.
    querystring = request.GET.copy()
    querystring.pop('page', None)
    # Pour les liens de tri : filtres actifs, sans le tri ni la page.
    sort_querystring = querystring.copy()
    sort_querystring.pop('sort', None)
    sort_querystring.pop('order', None)

    context = {
        'tickets': page_obj,
        'page_obj': page_obj,
        'querystring': querystring.urlencode(),
        'sort_querystring': sort_querystring.urlencode(),
        'sort': sort,
        'order': order,
        'filtering': filtering,
        'tab': tab,
        'to_plan': to_plan,
        'in_progress': in_progress,
        'older_late': older_late_count(all_tickets),
        'page_title': "Tickets de Maintenance",
        'technicians': Technician.objects.select_related('user').order_by('user__username'),
        'clients': Client.objects.order_by('name'),
        'buildings': Building.objects.select_related('client').order_by('name'),
        'status_choices': MaintenanceTicket.STATUS_CHOICES,
        'filters': {
            'technician': technician_id,
            'date': date_filter,
            'status': status_filter,
            'building': building_id,
            'client': client_id,
        },
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

        if action == 'add_photo':
            form = InterventionPhotoForm(request.POST, request.FILES)
            if form.is_valid():
                phase = request.POST.get('phase', 'during')
                if phase not in dict(InterventionPhoto.PHASE_CHOICES):
                    phase = 'during'
                photo = form.save(commit=False)
                photo.ticket = ticket
                photo.caption = photo.caption.strip()
                photo.phase = phase
                photo.uploaded_by = request.user
                photo.save()
                messages.success(request, "Photo ajoutée à l'intervention.")
            else:
                messages.error(request, "Le fichier envoyé n'est pas une image valide.")

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
        # Clôturée « à replanifier » : le ticket de suite transmis au dispatching.
        'follow_up': MaintenanceTicket.objects.filter(
            description__startswith=f"{FOLLOW_UP_PREFIX}{ticket.id} ",
        ).first() if ticket.status == 'to_reschedule' else None,
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
    Modification du ticket. En attente : planification complète (technicien, créneau...).
    Planifié : description seulement ; le technicien se change par « Réassigner ».
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)

    # Sécurité : Pas d'édition si déjà commencé/fini
    if ticket.status in ['in_progress', 'done', 'canceled', 'to_reschedule']:
        messages.warning(request, "Cette intervention ne peut plus être modifiée car elle est déjà en cours ou clôturée.")
        return redirect('ticket_detail', pk=ticket.id)

    mode = 'description' if ticket.status == 'planned' else None
    return _ticket_edit(request, ticket, mode, f"Planification #{ticket.id}", f"Intervention #{ticket.id} reprogrammée.")


@login_required
@user_passes_test(is_management_staff)
def ticket_cancel(request, pk):
    """
    Annulation par la gestion d'un ticket pas encore démarré (ex. le client rappelle : la panne est
    résolue). Le motif, obligatoire, est enregistré comme rapport. Le ticket quitte le planning du
    technicien ; il reste dans le planning global, en « Annulé ».
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    if ticket.status not in ('pending', 'planned'):
        messages.warning(request, "Seule une intervention pas encore démarrée peut être annulée.")
        return redirect('ticket_detail', pk=ticket.id)

    report = ''
    if request.method == 'POST':
        report = (request.POST.get('report') or '').strip()
        if report:
            ticket.status = 'canceled'
            ticket.intervention_report = report
            ticket.save()
            messages.success(request, f"Intervention #{ticket.id} annulée.")
            return redirect('ticket_detail', pk=ticket.id)
        messages.error(request, "Le motif de l'annulation est obligatoire.")

    return render(request, 'maintenance/ticket_cancel.html', {
        'ticket': ticket,
        'report': report,
        'page_title': f"Annulation #{ticket.id}",
    })


@login_required
@user_passes_test(is_management_staff)
def ticket_reassign(request, pk):
    """
    Réassignation d'un ticket « Planifié » : choix d'un autre technicien (et du créneau),
    avec son planning. Vider le technicien remet le ticket « En attente ».
    """
    ticket = get_object_or_404(MaintenanceTicket, pk=pk)
    if ticket.status != 'planned':
        messages.warning(request, "Seule une intervention planifiée peut être réassignée.")
        return redirect('ticket_detail', pk=ticket.id)
    return _ticket_edit(request, ticket, 'reassign', f"Réassignation #{ticket.id}", f"Intervention #{ticket.id} réassignée.")


def _ticket_edit(request, ticket, mode, page_title, success_message):
    """Formulaire de ticket limité aux champs de l'écran (mode), enregistré puis renvoyé à la fiche."""
    if request.method == 'POST':
        form = MaintenanceTicketForm(request.POST, instance=ticket, mode=mode)
        if form.is_valid():
            form.save()
            messages.success(request, success_message)
            if form.overlap_warning:
                messages.warning(request, form.overlap_warning)
            return redirect('ticket_detail', pk=ticket.id)
    else:
        form = MaintenanceTicketForm(instance=ticket, mode=mode)

    context = {
        'ticket': ticket,
        'form': form,
        'mode': mode,
        'technician_editable': 'technician' in form.fields and not form.fields['technician'].disabled,
        'page_title': page_title,
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

# Onglets de la fiche technicien.
TECHNICIAN_TABS = ('planning', 'interventions', 'statistiques', 'profil')


@login_required
@user_passes_test(is_management_staff)
def technician_detail(request, pk):
    """
    Fiche d'un technicien en onglets (?tab=) : planning (par défaut), interventions,
    statistiques et profil (compétences, disponibilité).
    """
    technician = get_object_or_404(Technician, pk=pk)
    tab = request.GET.get('tab')
    tab = tab if tab in TECHNICIAN_TABS else 'planning'
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
            return redirect(f"{reverse('technician_detail', args=[technician.pk])}?tab=profil")
        tab = 'profil'
    else:
        form = TechnicianForm(instance=technician)

    # Onglet Interventions : toutes celles du technicien, la date prévue la plus récente d'abord.
    interventions = Paginator(
        tickets.select_related('equipment', 'equipment__building', 'equipment__building__client', 'technician__user')
        .order_by('-planned_start', '-pk'),
        25,
    ).get_page(request.GET.get('page'))

    context = {
        'technician': technician,
        'form': form,
        'tab': tab,
        'interventions': interventions,
        'events_url': f"{reverse('api_events')}?technician={technician.pk}",
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
    Planning d'un technicien à la fois (?technician=, le premier par défaut) : tous les techniciens
    ensemble seraient illisibles. La vue d'ensemble se fait dans la liste des interventions.
    """
    technicians = Technician.objects.select_related('user').order_by('user__first_name', 'user__last_name', 'user__username')
    technician_id = request.GET.get('technician') or ''
    selected_technician = (technicians.filter(pk=technician_id).first() if technician_id.isdigit() else None) or technicians.first()
    events_url = f"{reverse('api_events')}?technician={selected_technician.pk}" if selected_technician else None
    context = {
        'page_title': "Planning de Maintenance",
        'technicians': technicians,
        'selected_technician': selected_technician,
        'events_url': events_url,
    }
    return render(request, 'maintenance/calendar.html', context)

from django.http import JsonResponse

@login_required
@user_passes_test(is_management_staff)
def api_get_buildings(request):
    """Lieux d'un client au format JSON (formulaire de ticket)."""
    client_id = request.GET.get('client_id')
    from inventory.models import Building
    buildings = Building.objects.filter(client_id=client_id).values('id', 'name')
    return JsonResponse(list(buildings), safe=False)

@login_required
@user_passes_test(is_management_staff)
def api_get_equipments(request):
    """Équipements d'un lieu au format JSON, avec recherche par nom ou numéro de série."""
    building_id = request.GET.get('building_id')
    search = request.GET.get('search')
    from inventory.models import Equipment

    equipments = Equipment.objects.select_related('equipment_type', 'building').all()
    if building_id:
        equipments = equipments.filter(building_id=building_id)
    if search:
        equipments = equipments.filter(serial_number__icontains=search) | equipments.filter(name__icontains=search)

    # Tri croissant par type d'équipement puis par nom, pour un regroupement par type côté client.
    equipments = equipments.order_by('equipment_type__name', 'name')
    if search:
        equipments = equipments[:20]

    if search:
        data = [{
            'id': e.id,
            'text': f"{e.name} ({e.serial_number}) - {e.building.name}",
            'type': e.equipment_type.name,
        } for e in equipments]
    else:
        data = [{
            'id': e.id,
            'text': f"{e.name} ({e.serial_number})",
            'type': e.equipment_type.name,
        } for e in equipments]
    return JsonResponse(data, safe=False)

def _parse_calendar_bound(value):
    """Borne envoyée par FullCalendar (date ou date-heure ISO 8601), rendue « aware », ou None."""
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        day = parse_date(value)
        if day is None:
            return None
        parsed = datetime.datetime.combine(day, datetime.time.min)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed

@login_required
@user_passes_test(is_management_staff)
def api_events(request):
    """
    Retourne les tickets au format JSON pour FullCalendar.
    - Vue globale : tous les tickets, à leur créneau prévu.
    - ?technician=<pk> : les tickets copiés dans le calendrier de ce technicien, aux heures de
      ces copies (le réel dès qu'il existe).
    ?start= / ?end= (envoyés par FullCalendar) : uniquement la période affichée.
    ?exclude=<pk> : sans ce ticket (le ticket en cours de dispatching).
    """
    range_start = _parse_calendar_bound(request.GET.get('start'))
    range_end = _parse_calendar_bound(request.GET.get('end'))
    in_range = range_start and range_end

    technician_id = request.GET.get('technician')
    if technician_id:
        if not technician_id.isdigit():
            return JsonResponse([], safe=False)
        calendar = get_technician_calendar(get_object_or_404(Technician, pk=technician_id))
        ticket_ids = assigned_ticket_ids(calendar)
        if in_range:
            ticket_ids = ticket_ids.filter(event__start__lt=range_end, event__end__gt=range_start)
        tickets = MaintenanceTicket.objects.filter(pk__in=ticket_ids)
        bounds = ticket_event_bounds
    else:
        tickets = MaintenanceTicket.objects.all()
        if in_range:
            tickets = tickets.filter(planned_start__lt=range_end, planned_end__gt=range_start)
        bounds = lambda ticket: (ticket.planned_start, ticket.planned_end)
    exclude_id = request.GET.get('exclude')
    if exclude_id and exclude_id.isdigit():
        tickets = tickets.exclude(pk=exclude_id)
    tickets = tickets.select_related('equipment', 'technician', 'equipment__building', 'equipment__building__client')

    events = []
    for ticket in tickets:
        display_start, display_end = bounds(ticket)

        # Titre dynamique avec statut
        status_label = ticket.get_status_display().upper()
        
        # Détermination de la couleur basée sur le statut
        # Mêmes repères que la liste des interventions : chaque statut a sa couleur.
        color = '#f59e0b' # Planifié : Amber 500
        if ticket.status == 'in_progress':
            color = '#3b82f6' # Blue 500
        elif ticket.status == 'done':
            color = '#10b981' # Emerald 500
        elif ticket.status == 'to_reschedule':
            color = '#ea580c' # Orange 600 : clôturée, travail non effectué
        elif ticket.status == 'pending':
            color = '#94a3b8' # Slate 400 : en attente, sans technicien
        elif ticket.status == 'canceled':
            color = '#f43f5e' # Rose 500
        elif ticket.type == 'emergency':
            color = '#ef4444' # Red 500 : urgence planifiée

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
