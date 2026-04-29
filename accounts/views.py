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
from .models import CustomUser
from .forms import CustomUserForm, CustomUserCreateForm

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """
    Liste des utilisateurs du système.
    """
    users = CustomUser.objects.filter(is_deleted=False).order_by('username')
    context = {
        'users': users,
        'page_title': "Gestion des Utilisateurs"
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
            messages.success(request, f"Utilisateur {user.username} créé avec succès.")
            return redirect('user_list')
    else:
        form = CustomUserCreateForm()
    
    context = {
        'form': form,
        'page_title': "Nouvel Utilisateur"
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
            messages.success(request, f"Utilisateur {user_to_edit.username} mis à jour.")
            return redirect('user_list')
    else:
        form = CustomUserForm(instance=user_to_edit)
    
    context = {
        'form': form,
        'user_to_edit': user_to_edit,
        'page_title': f"Modifier {user_to_edit.username}"
    }
    return render(request, 'accounts/user_form.html', context)

@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    """
    Suppression logique d'un utilisateur.
    """
    user_to_delete = get_object_or_404(CustomUser, pk=pk)
    if user_to_delete == request.user:
        messages.error(request, "Vous ne pouvez pas vous supprimer vous-même.")
    else:
        user_to_delete.soft_delete()
        messages.success(request, f"Utilisateur {user_to_delete.username} supprimé.")
    return redirect('user_list')
