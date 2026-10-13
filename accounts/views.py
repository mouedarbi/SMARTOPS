"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : accounts
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues pour la gestion des utilisateurs dans l'admin custom.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_POST
from .models import CustomUser
from django.contrib.auth import update_session_auth_hash
from .forms import CustomUserForm, CustomUserCreateForm, ProfileForm, ProfilePasswordForm

def is_admin(user):
    """Vrai si l'utilisateur connecté est administrateur ou superutilisateur."""
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

def is_management_staff(user):
    """Autorise uniquement les Admins et les Managers (et superusers)."""
    return user.is_authenticated and (user.role in ['admin', 'manager'] or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """
    Liste des utilisateurs du système.
    """
    users = CustomUser.objects.filter(is_deleted=False).order_by('username')
    context = {
        'users': users,
        'page_title': "Utilisateurs du système"
    }
    return render(request, 'accounts/user_list.html', context)

@login_required
@user_passes_test(is_admin)
def user_create(request):
    """
    Création d'un nouvel utilisateur.
    """
    if request.method == 'POST':
        form = CustomUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _("Utilisateur %(username)s créé avec succès.") % {'username': user.username})
            return redirect('user_list')
    else:
        form = CustomUserCreateForm()
    
    context = {
        'form': form,
        'page_title': _("Nouvel Utilisateur")
    }
    return render(request, 'accounts/user_form.html', context)

@login_required
@user_passes_test(is_admin)
def user_edit(request, pk):
    """
    Édition d'un utilisateur existant.
    """
    user_to_edit = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            form.save()
            messages.success(request, _("Utilisateur %(username)s mis à jour.") % {'username': user_to_edit.username})
            return redirect('user_list')
    else:
        form = CustomUserForm(instance=user_to_edit)
    
    context = {
        'form': form,
        'user_to_edit': user_to_edit,
        'page_title': _("Modifier %(username)s") % {'username': user_to_edit.username}
    }
    return render(request, 'accounts/user_form.html', context)

@login_required
@user_passes_test(is_admin)
@require_POST
def user_delete(request, pk):
    """
    Suppression logique d'un utilisateur (compte désactivé, historique conservé). Refusée pour
    un technicien qui a encore des interventions planifiées ou en cours.
    """
    user_to_delete = get_object_or_404(CustomUser, pk=pk)
    open_count = user_to_delete.open_ticket_count()
    if user_to_delete == request.user:
        messages.error(request, _("Vous ne pouvez pas vous supprimer vous-même."))
    elif open_count:
        messages.error(request, ngettext(
            "Ce technicien a encore %(count)s intervention planifiée ou en cours : réassignez-la avant de supprimer son compte.",
            "Ce technicien a encore %(count)s interventions planifiées ou en cours : réassignez-les avant de supprimer son compte.",
            open_count,
        ) % {'count': open_count})
    else:
        user_to_delete.soft_delete()
        messages.success(request, _("Utilisateur %(username)s supprimé.") % {'username': user_to_delete.username})
    return redirect('user_list')


@login_required
def my_profile(request):
    """
    « Mon profil » de l'utilisateur connecté (administrateur ou gestionnaire) : ses données de compte,
    modification de ses nom, prénom et e-mail, changement de son mot de passe.
    Un technicien est renvoyé vers le profil de son interface terrain.
    """
    if not is_management_staff(request.user):
        return redirect('technician_profile')

    profile_form = ProfileForm(instance=request.user)
    password_form = ProfilePasswordForm(request.user)

    if request.method == 'POST':
        if request.POST.get('action') == 'password':
            password_form = ProfilePasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Garde la session ouverte après le changement de mot de passe.
                update_session_auth_hash(request, user)
                messages.success(request, _("Mot de passe modifié."))
                return redirect('my_profile')
        else:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, _("Profil mis à jour."))
                return redirect('my_profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'page_title': "Mon profil",
    })
