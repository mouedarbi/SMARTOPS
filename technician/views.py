from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from maintenance.models import MaintenanceTicket, InterventionPhoto

def is_technician(user):
    return user.is_authenticated and user.role == 'technician'

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
                return redirect('technician_dashboard')
            else:
                messages.error(request, "Accès réservé au personnel technique.")
        else:
            messages.error(request, "Identifiants incorrects.")
    
    return render(request, 'technician/login.html', {
        'page_title': 'Connexion Technicien'
    })

@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    """
    Dashboard principal du technicien (Liste des interventions).
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('login')

    tickets_today = MaintenanceTicket.objects.filter(
        technician=tech_profile,
        planned_start__gte=today_start,
        planned_start__lt=today_end
    ).order_by('planned_start')

    tickets_week = MaintenanceTicket.objects.filter(
        technician=tech_profile,
        planned_start__gte=today_start,
        planned_start__lt=week_end
    ).order_by('planned_start')

    context = {
        'page_title': 'Mon Planning',
        'tickets_today': tickets_today,
        'tickets_week': tickets_week,
        'now': now,
    }
    return render(request, 'technician/dashboard.html', context)

@login_required
@user_passes_test(is_technician)
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
            messages.success(request, "Photo ajoutée.")
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
    }
    return render(request, 'technician/ticket_detail.html', context)

@login_required
@user_passes_test(is_technician)
def start_intervention(request, pk):
    """
    Démarre l'intervention : Change le statut et enregistre l'heure de début.
    """
    try:
        tech_profile = request.user.technician_profile
    except Exception:
        messages.error(request, "Profil technicien introuvable.")
        return redirect('technician_dashboard')

    ticket = get_object_or_404(MaintenanceTicket, pk=pk, technician=tech_profile)
    
    if ticket.status in ['pending', 'planned', 'to_reschedule']:
        ticket.status = 'in_progress'
        ticket.effective_start = timezone.now()
        ticket.save()
        messages.success(request, "Intervention démarrée. Bon travail !")
    else:
        messages.warning(request, "Cette intervention ne peut pas être démarrée.")

    return redirect('technician_ticket_detail', pk=pk)

@login_required
@user_passes_test(is_technician)
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

        ticket.intervention_report = report
        ticket.status = final_status
        ticket.effective_end = timezone.now()
        ticket.save()

        if final_status == 'to_reschedule':
            messages.success(request, "Rapport enregistré. Intervention marquée « à replanifier ».")
        else:
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
    logout(request)
    return redirect('technician_login')
