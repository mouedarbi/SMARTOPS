"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaires pour la gestion de la maintenance.
"""

from django import forms
from django.utils import timezone
from datetime import timedelta, time
from .models import MaintenanceTicket, Technician

from inventory.models import Client, Building, Equipment

class MaintenanceTicketForm(forms.ModelForm):
    # Choix pour les créneaux horaires
    TIME_SLOTS = [(time(h, m).strftime('%H:%M'), f"{h:02d}:{m:02d}") for h in range(7, 20) for m in (0, 30)]
    
    # Champs de filtrage (non-persistés directement mais utilisés pour le UI)
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        required=False,
        label="Filtrer par Client",
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 bg-white text-slate-900 shadow-sm'})
    )
    building = forms.ModelChoiceField(
        queryset=Building.objects.none(),
        required=False,
        label="Filtrer par Bâtiment",
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 bg-white text-slate-900 shadow-sm'})
    )

    # Choix pour les durées
    DURATION_CHOICES = [
        (3600, '1 heure'),
        (5400, '1h30'),
        (7200, '2 heures'),
        (10800, '3 heures'),
        (14400, '4 heures'),
    ]

    planned_date = forms.DateField(
        label="Date de l'intervention",
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={'type': 'date', 'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 transition shadow-sm'}
        ),
    )
    start_time_slot = forms.ChoiceField(
        label="Heure de début",
        choices=TIME_SLOTS,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 transition shadow-sm'}),
    )
    duration_seconds = forms.TypedChoiceField(
        label="Durée estimée",
        choices=DURATION_CHOICES,
        coerce=int,
        initial=5400,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 transition shadow-sm'}),
    )

    class Meta:
        model = MaintenanceTicket
        fields = ['equipment', 'technician', 'type', 'status', 'description']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 shadow-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. État par défaut (vide)
        self.fields['equipment'].queryset = Equipment.objects.none()
        self.fields['equipment'].choices = [('', '--- Choisir un équipement ---')]
        
        # 2. Si mode édition : pré-peupler les menus déroulants
        if self.instance and self.instance.pk and self.instance.equipment:
            building = self.instance.equipment.building
            client = building.client
            
            # Client (Lecture seule dans template, mais on garde la logique)
            self.fields['client'].initial = client
            
            # Peupler Bâtiments
            self.fields['building'].queryset = Building.objects.filter(client=client)
            self.fields['building'].initial = building
            
            # Peupler Équipements
            self.fields['equipment'].queryset = Equipment.objects.filter(building=building)
            self.fields['equipment'].choices = [(e.id, str(e)) for e in self.fields['equipment'].queryset]
            self.fields['equipment'].initial = self.instance.equipment

            if self.instance.planned_start:
                self.fields['planned_date'].initial = self.instance.planned_start.strftime('%Y-%m-%d')
                self.fields['start_time_slot'].initial = self.instance.planned_start.strftime('%H:%M')
                if self.instance.planned_end:
                    diff = (self.instance.planned_end - self.instance.planned_start).total_seconds()
                    # On cherche la durée la plus proche
                    closest = min([c[0] for c in self.DURATION_CHOICES], key=lambda x: abs(x - diff))
                    self.fields['duration_seconds'].initial = int(closest)
        
        # 3. Validation dynamique pour le formulaire POST (Ajax)
        if self.data.get('building'):
            try:
                building_id = int(self.data.get('building'))
                self.fields['equipment'].queryset = Equipment.objects.filter(building_id=building_id)
                self.fields['equipment'].choices = [(e.id, str(e)) for e in self.fields['equipment'].queryset]
            except (ValueError, TypeError):
                pass
        
        if self.data.get('client'):
            try:
                client_id = int(self.data.get('client'))
                self.fields['building'].queryset = Building.objects.filter(client_id=client_id)
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        planned_date = self.cleaned_data['planned_date']
        start_time_str = self.cleaned_data['start_time_slot']
        duration_sec = self.cleaned_data['duration_seconds']

        start_time = time.fromisoformat(start_time_str)
        instance.planned_start = timezone.make_aware(timezone.datetime.combine(planned_date, start_time))
        instance.planned_end = instance.planned_start + timedelta(seconds=duration_sec)
        
        if commit:
            instance.save()
        return instance

class TechnicianForm(forms.ModelForm):
    """
    Formulaire pour éditer le profil d'un technicien.
    """
    specialties_str = forms.CharField(
        label="Spécialités (séparées par des virgules)",
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 shadow-sm', 'placeholder': 'Ex: Electrique, Hydraulique, Froid'})
    )

    class Meta:
        model = Technician
        fields = ['is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 rounded border-slate-300 focus:ring-blue-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['specialties_str'].initial = ", ".join(self.instance.specialties)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Conversion de la chaîne en liste
        spec_str = self.cleaned_data.get('specialties_str', '')
        instance.specialties = [s.strip() for s in spec_str.split(',') if s.strip()]
        if commit:
            instance.save()
        return instance
