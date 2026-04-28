"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Vues CRUD pour la gestion des clients.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Client, Building
from .forms import ClientForm, BuildingForm

# --- VUES CLIENT ---

# ... (Vues Client existantes) ...

@login_required
def building_list_view(request):
    """
    Liste les bâtiments enregistrés.
    """
    buildings = Building.objects.all().order_by('name')
    return render(request, 'inventory/building_list.html', {'buildings': buildings})

@login_required
def building_create_view(request):
    """
    Crée un nouveau bâtiment.
    """
    if request.method == 'POST':
        form = BuildingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bâtiment créé avec succès.")
            return redirect('building_list')
    else:
        form = BuildingForm()
    return render(request, 'inventory/building_form.html', {'form': form, 'title': 'Nouveau Bâtiment'})

@login_required
def building_update_view(request, pk):
    """
    Met à jour un bâtiment existant.
    """
    building = get_object_or_404(Building, pk=pk)
    if request.method == 'POST':
        form = BuildingForm(request.POST, instance=building)
        if form.is_valid():
            form.save()
            messages.success(request, "Informations bâtiment mises à jour.")
            return redirect('building_list')
    else:
        form = BuildingForm(instance=building)
    return render(request, 'inventory/building_form.html', {'form': form, 'title': 'Modifier Bâtiment'})
