"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : technician
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues de l'application web mobile des techniciens : connexion, tableau de bord,
              démarrage et clôture des interventions, photos, historique et profil.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from maintenance.models import MaintenanceTicket, InterventionPhoto
from maintenance.forms import InterventionPhotoForm
from maintenance.services import reschedule_ticket, technician_tickets, with_display_start
from maintenance.templatetags.ticket_links import referenced_ticket_ids

def is_technician(user):
    """Vrai si l'utilisateur connecté est technicien."""
    return user.is_authenticated and user.role == 'technician'

def technician_root(request):
    """
    Point d'entrée /technician/ : redirige vers le dashboard si connecté en technicien,
    ou vers la page de login technicien sinon.
    """
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'technician':
        return redirect('technician_dashboard')
    return redirect('technician_login')

def technician_login(request):
    """
    Vue de connexion dédiée aux techniciens.
    """
    if request.user.is_authenticated:
        if request.user.is_technician:
            return redirect('technician_dashboard')
        return redirect('dashboard') 

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.role == 'technician':
                login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url and next_url.startswith('/technician/'):
                    return redirect(next_url)
                return redirect('technician_dashboard')
            else:
                messages.error(request, "Accès réservé au personnel technique.")
        else:
            messages.error(request, "Identifiants incorrects.")
    
    return render(request, 'technician/login.html', {
        'page_title': 'Connexion Technicien'
    })

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
def technician_dashboard(request):
    """
    Dashboard principal du technicien (Liste des interventions).
    """
    now = timezone.now()
    # Bornes du jour dans le fuseau local (TIME_ZONE), pas en UTC
    today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('login')

    # Interventions du calendrier du technicien, datées par leur début effectif si démarrées, sinon prévu
    tickets = with_display_start(technician_tickets(tech_profile))

    tickets_today = tickets.filter(
        display_start__gte=today_start,
        display_start__lt=today_end
    ).order_by('display_start')

    tickets_week = tickets.filter(
        display_start__gte=today_start,
        display_start__lt=week_end
    ).order_by('display_start')

    # Interventions des jours précédents qui n'ont pas été clôturées
    tickets_overdue = tickets.filter(
        planned_start__lt=today_start,
        status__in=['pending', 'planned', 'in_progress'],
    ).order_by('planned_start')

    context = {
        'page_title': 'Mon Planning',
        'tickets_today': tickets_today,
        'tickets_week': tickets_week,
        'tickets_overdue': tickets_overdue,
        'now': now,
    }
    return render(request, 'technician/dashboard.html', context)

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
def technician_history(request):
    """
    Historique des interventions du technicien (terminées, à replanifier ou annulées).
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    tickets = (
        with_display_start(MaintenanceTicket.objects)
        .filter(technician=tech_profile, status__in=['done', 'to_reschedule', 'canceled'])
        .select_related('equipment', 'equipment__building')
        .order_by('-display_start', '-id')
    )
    page = Paginator(tickets, 20).get_page(request.GET.get('page'))

    return render(request, 'technician/history.html', {
        'page_title': 'Historique',
        'page': page,
        'now': timezone.now(),
    })

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
def technician_profile(request):
    """
    Profil du technicien : identité, spécialités et récapitulatif de son activité.
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    stats = MaintenanceTicket.objects.filter(technician=tech_profile).aggregate(
        done=Count('id', filter=Q(status='done')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        upcoming=Count('id', filter=Q(status__in=['pending', 'planned'])),
    )

    return render(request, 'technician/profile.html', {
        'page_title': 'Mon Profil',
        'tech_profile': tech_profile,
        'stats': stats,
        'now': timezone.now(),
    })

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
def technician_ticket_detail(request, pk):
    """
    Vue détaillée d'une intervention pour le technicien.
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician=tech_profile)

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
                messages.success(request, "Photo ajoutée.")
            else:
                messages.error(request, "Le fichier envoyé n'est pas une image valide.")
        elif action == 'delete_photo':
            photo = ticket.photos.filter(pk=request.POST.get('photo_id'), uploaded_by=request.user).first()
            if photo:
                photo.delete()
                messages.success(request, "Photo supprimée.")
        return redirect('technician_ticket_detail', pk=ticket.id)

    context = {
        'page_title': f"Intervention #{ticket.id}",
        'ticket': ticket,
        'now': timezone.now(),
        'photos': ticket.photos.all(),
        # Liens vers les tickets cités dans la description, limités à ceux du technicien
        'linkable_ids': set(MaintenanceTicket.objects.filter(
            technician=tech_profile, pk__in=referenced_ticket_ids(ticket.description),
        ).values_list('pk', flat=True)),
    }
    return render(request, 'technician/ticket_detail.html', context)

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
@require_POST
def start_intervention(request, pk):
    """
    Démarre l'intervention : Change le statut, enregistre l'heure de début
    et, si le navigateur l'a fournie, la position GPS de départ.
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician=tech_profile)

    if ticket.status in ['pending', 'planned']:
        ticket.status = 'in_progress'
        ticket.effective_start = timezone.now()

        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        if latitude and longitude:
            try:
                ticket.start_latitude = Decimal(latitude)
                ticket.start_longitude = Decimal(longitude)
            except InvalidOperation:
                pass

        ticket.save()
        messages.success(request, "Intervention démarrée. Bon travail !")
    else:
        messages.warning(request, "Cette intervention ne peut pas être démarrée.")

    return redirect('technician_ticket_detail', pk=pk)

@login_required(login_url='technician_login')
@user_passes_test(is_technician, login_url='technician_login')
def stop_intervention(request, pk):
    """
    Clôture de l'intervention (Phase 5) : saisie du rapport terrain,
    choix du statut final (terminé / à replanifier) puis horodatage de fin.

    GET  : affiche le formulaire de rapport.
    POST : enregistre le rapport et clôture l'intervention.
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician=tech_profile)

    if ticket.status != 'in_progress':
        messages.warning(request, "Cette intervention n'est pas en cours.")
        return redirect('technician_ticket_detail', pk=pk)

    if request.method == 'POST':
        report = (request.POST.get('intervention_report') or '').strip()
        final_status = request.POST.get('final_status', 'done')
        if final_status not in ('done', 'to_reschedule'):
            final_status = 'done'

        if not report:
            messages.error(request, "Le rapport d'intervention est obligatoire pour clôturer.")
            return render(request, 'technician/intervention_report.html', {
                'page_title': f"Rapport #{ticket.id}",
                'ticket': ticket,
                'now': timezone.now(),
                'report_value': report,
                'final_status': final_status,
            })

        if final_status == 'to_reschedule':
            follow_up = reschedule_ticket(ticket, report)
            messages.success(
                request,
                f"Rapport enregistré. Intervention clôturée, ticket de suite #{follow_up.id} transmis au dispatching.",
            )
        else:
            ticket.intervention_report = report
            ticket.status = final_status
            ticket.effective_end = timezone.now()
            ticket.save()
            messages.success(request, "Intervention clôturée. Merci et bon travail !")
        return redirect('technician_ticket_detail', pk=pk)

    return render(request, 'technician/intervention_report.html', {
        'page_title': f"Rapport #{ticket.id}",
        'ticket': ticket,
        'now': timezone.now(),
        'report_value': ticket.intervention_report,
        'final_status': 'done',
    })

def technician_logout(request):
    """Déconnecte le technicien et revient à l'écran de connexion."""
    logout(request)
    return redirect('technician_login')
