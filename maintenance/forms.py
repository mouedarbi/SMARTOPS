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

class MaintenanceTicketForm(forms.ModelForm):
    # Choix pour les créneaux horaires
    TIME_SLOTS = [(time(h, m).strftime('%H:%M'), f"{h:02d}:{m:02d}") for h in range(7, 20) for m in (0, 30)]
    
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
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
    )
    start_time_slot = forms.ChoiceField(
        label="Heure de début",
        choices=TIME_SLOTS,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
    )
    duration_seconds = forms.TypedChoiceField(
        label="Durée estimée",
        choices=DURATION_CHOICES,
        coerce=int,
        initial=5400,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
    )

    class Meta:
        model = MaintenanceTicket
        fields = ['equipment', 'technician', 'type', 'status', 'description']
        widgets = {
            'equipment': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
            'technician': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
            'type': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
            'status': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition shadow-sm', 'placeholder': 'Détaillez le problème ou les tâches à effectuer...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.planned_start:
            self.fields['planned_date'].initial = self.instance.planned_start.date()
            self.fields['start_time_slot'].initial = self.instance.planned_start.strftime('%H:%M')
            if self.instance.planned_end:
                diff = (self.instance.planned_end - self.instance.planned_start).total_seconds()
                # On cherche la durée la plus proche
                closest = min([c[0] for c in self.DURATION_CHOICES], key=lambda x: abs(x - diff))
                self.fields['duration_seconds'].initial = int(closest)

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
