"""
Fichier : forms.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Formulaires pour la gestion de la maintenance.
"""

from itertools import groupby

from django import forms
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from datetime import timedelta, time
from .models import MaintenanceTicket, Technician, InterventionPhoto
from .services import NOT_STARTED, find_schedule_conflict, schedule_conflict_message

from inventory.models import Client, Building, Equipment


def _equipment_choices_by_type(queryset):
    """Regroupe les équipements par type (optgroups), tri croissant sur le type puis le nom."""
    queryset = queryset.select_related('equipment_type').order_by('equipment_type__name', 'name')
    return [
        (type_name, [(e.id, str(e)) for e in items])
        for type_name, items in groupby(queryset, key=lambda e: e.equipment_type.name)
    ]


class MaintenanceTicketForm(forms.ModelForm):
    """
    Création et planification d'un ticket : client, lieu et équipement en cascade,
    technicien, date, créneau de début et durée (en heure locale).
    """
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
        label="Filtrer par lieu",
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
        # Le statut est fixé par le système (voir MaintenanceTicket.save()).
        fields = ['equipment', 'technician', 'type', 'description']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 shadow-sm'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white text-slate-900 shadow-sm', 'rows': 4}),
        }

    # Champs modifiables selon l'écran, pour un ticket « Planifié » :
    # « Modifier » ne touche qu'à la description, « Réassigner » au technicien et au créneau.
    EDITABLE_FIELDS = {
        'description': {'description'},
        'reassign': {'technician', 'planned_date', 'start_time_slot', 'duration_seconds'},
    }

    def __init__(self, *args, mode=None, **kwargs):
        super().__init__(*args, **kwargs)
        if mode:
            for name, field in self.fields.items():
                if name not in self.EDITABLE_FIELDS[mode]:
                    field.disabled = True
                    field.required = False

        # À la création, pas de technicien : le ticket naît « En attente » et s'assigne en modification.
        if not self.instance.pk:
            del self.fields['technician']

        # 1. État par défaut (vide)
        self.fields['equipment'].queryset = Equipment.objects.none()
        self.fields['equipment'].choices = [('', '--- Choisir un équipement ---')]

        # 1.bis Sécurité : Si l'intervention est en cours ou terminée, on verrouille la planification et le statut
        if self.instance and self.instance.pk:
            if self.instance.status in ['in_progress', 'done', 'canceled', 'to_reschedule']:
                # On verrouille TOUT pour éviter les incohérences avec le terrain
                for field_name in self.fields:
                    self.fields[field_name].disabled = True
                    self.fields[field_name].required = False
        if self.instance and self.instance.pk and self.instance.equipment:
            building = self.instance.equipment.building
            client = building.client
            
            # Client (Lecture seule dans template, mais on garde la logique)
            self.fields['client'].initial = client
            
            # Peupler les lieux
            self.fields['building'].queryset = Building.objects.filter(client=client)
            self.fields['building'].initial = building
            
            # Peupler Équipements (groupés par type, tri croissant)
            self.fields['equipment'].queryset = Equipment.objects.filter(building=building)
            self.fields['equipment'].choices = _equipment_choices_by_type(self.fields['equipment'].queryset)
            self.fields['equipment'].initial = self.instance.equipment

            if self.instance.planned_start:
                # Heure locale : les champs sont réenregistrés en heure locale (voir clean()).
                local_start = timezone.localtime(self.instance.planned_start)
                self.fields['planned_date'].initial = local_start.strftime('%Y-%m-%d')
                self.fields['start_time_slot'].initial = local_start.strftime('%H:%M')
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
                self.fields['equipment'].choices = _equipment_choices_by_type(self.fields['equipment'].queryset)
            except (ValueError, TypeError):
                pass
        
        if self.data.get('client'):
            try:
                client_id = int(self.data.get('client'))
                self.fields['building'].queryset = Building.objects.filter(client_id=client_id)
            except (ValueError, TypeError):
                pass

    def clean(self):
        """
        Calcule le début et la fin prévus (heure locale) et refuse un conflit de
        planning avec une autre intervention du même technicien.
        """
        cleaned_data = super().clean()
        planned_date = cleaned_data.get('planned_date')
        start_time_str = cleaned_data.get('start_time_slot')
        duration_sec = cleaned_data.get('duration_seconds')
        if not (planned_date and start_time_str and duration_sec):
            return cleaned_data

        start = timezone.make_aware(timezone.datetime.combine(planned_date, time.fromisoformat(start_time_str)))
        end = start + timedelta(seconds=duration_sec)
        cleaned_data['planned_start'], cleaned_data['planned_end'] = start, end

        # Conflit de planning : seulement pour une intervention pas encore démarrée, avec un technicien.
        if self.instance.status in NOT_STARTED:
            conflict = find_schedule_conflict(cleaned_data.get('technician'), start, end, exclude_pk=self.instance.pk)
            if conflict:
                message = schedule_conflict_message(conflict)
                ticket_ref = f"#{conflict.pk}"
                before, after = message.split(ticket_ref, 1)
                self.add_error(None, format_html(
                    '<strong>Conflit de planning</strong> : {}<a href="{}" target="_blank" class="underline font-bold">{}</a>{}',
                    before, reverse('ticket_detail', args=[conflict.pk]), ticket_ref, after,
                ))
        return cleaned_data

    def save(self, commit=True):
        """Enregistre le ticket avec le début et la fin prévus calculés par clean()."""
        instance = super().save(commit=False)
        instance.planned_start = self.cleaned_data['planned_start']
        instance.planned_end = self.cleaned_data['planned_end']

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
        """Enregistre le profil avec la liste des spécialités saisies."""
        instance = super().save(commit=False)
        # Conversion de la chaîne en liste
        spec_str = self.cleaned_data.get('specialties_str', '')
        instance.specialties = [s.strip() for s in spec_str.split(',') if s.strip()]
        if commit:
            instance.save()
        return instance


class InterventionPhotoForm(forms.ModelForm):
    """
    Ajout d'une photo d'intervention : le fichier doit être une image valide
    (extension et contenu vérifiés par l'ImageField).
    """
    class Meta:
        model = InterventionPhoto
        fields = ['image', 'caption']
