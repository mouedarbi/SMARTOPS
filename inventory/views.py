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
from .models import Client
from .forms import ClientForm

@login_required
def client_list_view(request):
    """
    Liste les clients enregistrés.
    """
    clients = Client.objects.all().order_by('-created_at')
    return render(request, 'inventory/client_list.html', {'clients': clients})

@login_required
def client_create_view(request):
    """
    Crée un nouveau client.
    """
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
def client_update_view(request, pk):
    """
    Met à jour un client existant.
    """
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
