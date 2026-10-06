"""
Fichier : services.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Description : Opérations métier partagées entre l'application technicien et l'API.
"""

import datetime
import os
import re

from django.core.files import File
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import MaintenanceTicket, InterventionPhoto


# Début de la description d'un ticket de suite créé par reschedule_ticket().
FOLLOW_UP_PREFIX = "Suite de l'intervention #"
FOLLOW_UP_ORIGIN = re.compile(r"^Suite de l'intervention #(\d+)")
NOT_STARTED = ('pending', 'planned')
# Retards montrés dans « Interventions à replanifier » ; les plus anciens restent dans la liste complète.
LATE_WINDOW = datetime.timedelta(days=7)


def with_display_start(queryset):
    """
    Annote `display_start` : début effectif si l'intervention a démarré, sinon début prévu.
    Sert à dater une intervention réalisée un autre jour que prévu.
    """
    return queryset.annotate(display_start=Coalesce('effective_start', 'planned_start'))


def reschedule_ticket(ticket, report=None):
    """
    Clôture une intervention en « à replanifier » et crée le ticket de suite.

    Le ticket d'origine conserve ses données terrain (horaires réels, GPS,
    rapport, photos). Le ticket de suite est créé en attente, sans technicien :
    il doit repasser par le dispatching. Il reprend l'équipement, le type,
    les consignes, le rapport du passage et une copie des photos.

    Retourne le ticket de suite.
    """
    with transaction.atomic():
        ended_at = timezone.now()
        if report is not None:
            ticket.intervention_report = report
        ticket.status = 'to_reschedule'
        ticket.effective_end = ended_at

        description = (
            f"{FOLLOW_UP_PREFIX}{ticket.id} "
            f"(à replanifier le {timezone.localtime(ended_at):%d/%m/%Y à %H:%M})."
        )
        if ticket.description:
            description += f"\n\nConsignes d'origine :\n{ticket.description}"
        if ticket.intervention_report:
            description += f"\n\nRapport du passage précédent :\n{ticket.intervention_report}"

        follow_up = MaintenanceTicket.objects.create(
            equipment=ticket.equipment,
            technician=None,
            type=ticket.type,
            status='pending',
            planned_start=ticket.planned_start,
            planned_end=ticket.planned_end,
            description=description,
        )

        note = f"Suite de l'intervention : ticket #{follow_up.id}"
        ticket.description = f"{ticket.description}\n\n{note}" if ticket.description else note
        ticket.save()

        # Copie physique : supprimer une photo efface son fichier, les deux
        # tickets ne doivent donc pas partager le même fichier.
        for photo in ticket.photos.all():
            copy = InterventionPhoto(
                ticket=follow_up,
                caption=photo.caption,
                phase=photo.phase,
                uploaded_by=photo.uploaded_by,
            )
            with photo.image.open('rb') as source:
                copy.image.save(os.path.basename(photo.image.name), File(source), save=False)
            copy.save()

    return follow_up


def local_day_range(day):
    """
    Début et fin (exclue) d'une journée en heure locale, pour filtrer par intervalle.
    Évite les recherches `__date`, qui ne renvoient rien sur MySQL sans tables de fuseaux horaires.
    """
    start = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
    return start, start + datetime.timedelta(days=1)


def tickets_to_reschedule(queryset, now=None):
    """
    Interventions à réaffecter sans attendre, avec leur motif (`reschedule_reason`) :
    - « follow_up » : suite d'une intervention clôturée « à replanifier » (en attente, sans technicien),
      `origin_id` = numéro de l'intervention d'origine ;
    - « late » : intervention non démarrée dont le créneau prévu s'est terminé dans les 7 derniers jours.
    """
    now = now or timezone.now()
    follow_ups = list(queryset.filter(
        status='pending', technician__isnull=True, description__startswith=FOLLOW_UP_PREFIX,
    ).order_by('planned_start'))
    for ticket in follow_ups:
        ticket.reschedule_reason = 'follow_up'
        match = FOLLOW_UP_ORIGIN.match(ticket.description)
        ticket.origin_id = int(match.group(1)) if match else None

    late = list(queryset.filter(
        status__in=NOT_STARTED, planned_end__lt=now, planned_end__gte=now - LATE_WINDOW,
    ).exclude(
        pk__in=[t.pk for t in follow_ups],
    ).order_by('planned_start'))
    for ticket in late:
        ticket.reschedule_reason = 'late'
    return follow_ups + late


def older_late_count(queryset, now=None):
    """Interventions jamais démarrées dont le créneau s'est terminé il y a plus de 7 jours."""
    now = now or timezone.now()
    return queryset.filter(status__in=NOT_STARTED, planned_end__lt=now - LATE_WINDOW).count()


def tickets_of_the_day(queryset, now=None, exclude_ids=()):
    """
    Journée en cours : interventions en cours (quelle que soit leur date prévue), interventions
    prévues aujourd'hui (heure locale) et pas encore démarrées, par heure de début, puis
    interventions terminées aujourd'hui.
    """
    now = now or timezone.now()
    day_start, day_end = local_day_range(timezone.localdate(now))
    return list(queryset.filter(
        Q(status='in_progress')
        | Q(status__in=NOT_STARTED, planned_start__gte=day_start, planned_start__lt=day_end)
        | Q(status='done', effective_end__gte=day_start, effective_end__lt=day_end),
    ).exclude(pk__in=exclude_ids).annotate(
        day_order=Case(
            When(status='in_progress', then=Value(0)),
            When(status='done', then=Value(2)),
            default=Value(1), output_field=IntegerField(),
        ),
    ).order_by('day_order', 'planned_start'))
