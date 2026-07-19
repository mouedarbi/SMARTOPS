"""
Fichier : views.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.2
Description : Vues CRUD pour la gestion des clients, bâtiments, équipements et types.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import is_management_staff
from .models import Client, Building, Equipment, EquipmentType, EquipmentTypeField
from .forms import ClientForm, BuildingForm, EquipmentForm, EquipmentTypeForm, EquipmentTypeFieldForm

# --- VUES CLIENT ---

@login_required
@user_passes_test(is_management_staff)
def client_list_view(request):
    """Liste les clients enregistrés avec recherche, tri et pagination."""
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    clients = Client.objects.all()
    
    # Recherche
    q = request.GET.get('q', '').strip()
    if q:
        clients = clients.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(vat_number__icontains=q)
        )
    
    # Tri
    sort_by = request.GET.get('sort', 'created_at')
    order = request.GET.get('order', 'desc')
    
    if sort_by in ['name', 'created_at']:
        prefix = '-' if order == 'desc' else ''
        clients = clients.order_by(f"{prefix}{sort_by}")
    else:
        clients = clients.order_by('-created_at')
        
    # Pagination
    paginator = Paginator(clients, 10)  # 10 clients par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/client_list.html', {
        'page_obj': page_obj,
        'q': q,
        'sort': sort_by,
        'order': order
    })

@login_required
@user_passes_test(is_management_staff)
def client_create_view(request):
    """Crée un nouveau client."""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Client créé avec succès.")
            return redirect('client_list')
    else:
        form = ClientForm()
    return render(request, 'inventory/client_form.html', {'form': form, 'title': 'Nouveau Client'})

@login_required
@user_passes_test(is_management_staff)
def client_update_view(request, pk):
    """Met à jour un client existant."""
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Informations mises à jour.")
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'inventory/client_form.html', {'form': form, 'title': 'Modifier Client'})

@login_required
@user_passes_test(is_management_staff)
def client_detail_view(request, pk):
    """Affiche les détails d'un client et ses sites associés."""
    client = get_object_or_404(Client, pk=pk)
    buildings = client.buildings.all().order_by('name')
    return render(request, 'inventory/client_detail.html', {
        'client': client,
        'buildings': buildings,
        'page_title': f"Détails Client - {client.name}"
    })

# --- VUES BÂTIMENT ---

@login_required
@user_passes_test(is_management_staff)
def building_list_view(request):
    """Liste les bâtiments enregistrés avec recherche, tri et pagination."""
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    buildings = Building.objects.all()
    
    # Recherche
    q = request.GET.get('q', '').strip()
    if q:
        buildings = buildings.filter(
            Q(name__icontains=q) |
            Q(address__icontains=q) |
            Q(client__name__icontains=q)
        )
        
    # Tri
    sort_by = request.GET.get('sort', 'name')
    order = request.GET.get('order', 'asc')
    
    if sort_by in ['name', 'client__name']:
        prefix = '-' if order == 'desc' else ''
        # select_related pour optimiser les performances de requete
        buildings = buildings.select_related('client').order_by(f"{prefix}{sort_by}")
    else:
        buildings = buildings.select_related('client').order_by('name')
        
    # Pagination
    paginator = Paginator(buildings, 10)  # 10 sites par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/building_list.html', {
        'page_obj': page_obj,
        'q': q,
        'sort': sort_by,
        'order': order
    })

@login_required
@user_passes_test(is_management_staff)
def building_create_view(request):
    """Crée un nouveau bâtiment."""
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
@user_passes_test(is_management_staff)
def building_update_view(request, pk):
    """Met à jour un bâtiment existant."""
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

# --- VUES ÉQUIPEMENT ---

@login_required
@user_passes_test(is_management_staff)
def equipment_list_view(request):
    """Liste les équipements enregistrés."""
    equipments = Equipment.objects.all().order_by('name')
    return render(request, 'inventory/equipment_list.html', {'equipments': equipments})

@login_required
@user_passes_test(is_management_staff)
def equipment_create_view(request):
    """Crée un nouvel équipement."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Équipement créé avec succès.")
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'inventory/equipment_form.html', {'form': form, 'title': 'Nouvel Équipement'})

# --- VUES TYPE ÉQUIPEMENT ---

@login_required
@user_passes_test(is_management_staff)
def equipment_type_list_view(request):
    """Liste les types d'équipement."""
    types = EquipmentType.objects.all().order_by('name')
    if request.method == 'POST':
        form = EquipmentTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('equipment_type_list')
    else:
        form = EquipmentTypeForm()
    return render(request, 'inventory/equipment_type_list.html', {'types': types, 'form': form})

@login_required
@user_passes_test(is_management_staff)
def equipment_type_detail_view(request, pk):
    """Détail d'un type et gestion de ses champs."""
    etype = get_object_or_404(EquipmentType, pk=pk)
    if request.method == 'POST':
        form = EquipmentTypeFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.equipment_type = etype
            field.save()
            messages.success(request, "Champ ajouté.")
            return redirect('equipment_type_detail', pk=pk)
    else:
        form = EquipmentTypeFieldForm()
    return render(request, 'inventory/equipment_type_detail.html', {'type': etype, 'form': form})

@login_required
@user_passes_test(is_management_staff)
def building_detail_view(request, pk):
    """Affiche les détails d'un site et la liste de ses équipements."""
    building = get_object_or_404(Building, pk=pk)
    equipments = building.equipments.all().order_by('name')
    return render(request, 'inventory/building_detail.html', {
        'building': building,
        'equipments': equipments,
        'page_title': f"Détails Site - {building.name}"
    })

@login_required
@user_passes_test(is_management_staff)
def equipment_detail_view(request, pk):
    """Affiche les détails d'un équipement, ses attributs et ses tickets d'intervention."""
    equipment = get_object_or_404(Equipment, pk=pk)
    tickets = equipment.maintenance_tickets.all().order_by('-planned_start')[:10]
    return render(request, 'inventory/equipment_detail.html', {
        'equipment': equipment,
        'tickets': tickets,
        'page_title': f"Détails Équipement - {equipment.name}"
    })
