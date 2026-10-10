"""
Fichier : services.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Opérations métier partagées entre l'application technicien et l'API.
"""

import datetime
import os
import re

from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from .calendars import assigned_ticket_ids, get_technician_calendar
from .models import NOT_STARTED, MaintenanceTicket, InterventionPhoto
from .templatetags.ticket_links import referenced_ticket_ids


# Début de la description d'un ticket de suite créé par reschedule_ticket().
FOLLOW_UP_PREFIX = "Suite de l'intervention #"
FOLLOW_UP_ORIGIN = re.compile(r"^Suite de l'intervention #(\d+)")
# Retards montrés dans « Interventions à replanifier » ; les plus anciens restent dans la liste complète.
LATE_WINDOW = datetime.timedelta(days=7)


def with_display_start(queryset):
    """
    Annote `display_start` : début effectif si l'intervention a démarré, sinon début prévu.
    Sert à dater une intervention réalisée un autre jour que prévu.
    """
    return queryset.annotate(display_start=Coalesce('effective_start', 'planned_start'))


def technician_tickets(technician):
    """Tickets dont une copie de l'événement est dans le calendrier du technicien."""
    return MaintenanceTicket.objects.filter(pk__in=assigned_ticket_ids(get_technician_calendar(technician)))


def related_ticket_ids(technician):
    """
    Tickets cités dans la description des tickets du technicien : l'intervention d'origine
    d'un ticket de suite qui lui est confié, ou la suite d'une intervention qu'il a clôturée.
    """
    ids = set()
    for description in MaintenanceTicket.objects.filter(technician=technician).values_list('description', flat=True):
        ids |= referenced_ticket_ids(description)
    return ids


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


def tickets_to_plan(queryset, now=None):
    """
    File « À planifier » : interventions qui attendent le gestionnaire, de la plus ancienne date
    prévue à la plus récente, avec leur motif (`plan_reason`) :
    - « follow_up » : suite d'une intervention clôturée « à replanifier » (en attente, sans technicien),
      `origin_id` = numéro de l'intervention d'origine ;
    - « unassigned » : autre intervention en attente, sans technicien ;
    - « late » : intervention planifiée jamais démarrée dont le créneau s'est terminé dans les 7 derniers jours.
    """
    now = now or timezone.now()
    rows = list(queryset.filter(
        Q(status='pending', technician__isnull=True)
        | Q(status='planned', planned_end__lt=now, planned_end__gte=now - LATE_WINDOW),
    ).order_by('planned_start', 'pk'))
    for ticket in rows:
        if ticket.status == 'planned':
            ticket.plan_reason = 'late'
            continue
        match = FOLLOW_UP_ORIGIN.match(ticket.description)
        ticket.plan_reason = 'follow_up' if match else 'unassigned'
        ticket.origin_id = int(match.group(1)) if match else None
    return rows


def older_late_count(queryset, now=None):
    """Interventions planifiées jamais démarrées dont le créneau s'est terminé il y a plus de 7 jours."""
    now = now or timezone.now()
    return queryset.filter(status='planned', planned_end__lt=now - LATE_WINDOW).count()


def occupied_interval(ticket):
    """
    Plage horaire occupée par une intervention pour son technicien, ou None si elle n'occupe plus rien :
    - en attente / planifiée : créneau prévu ;
    - en cours : à partir du démarrage effectif, pour la durée prévue ;
    - terminée, annulée, à replanifier : rien.
    """
    if ticket.status in NOT_STARTED:
        return ticket.planned_start, ticket.planned_end
    if ticket.status == 'in_progress' and ticket.effective_start:
        return ticket.effective_start, ticket.effective_start + (ticket.planned_end - ticket.planned_start)
    return None


def find_schedule_conflict(technician, start, end, exclude_pk=None):
    """
    Première intervention du technicien dont la plage occupée chevauche [start, end[, ou None.
    Les créneaux bord à bord ne sont pas en conflit. La plage occupée est exposée en `busy_start` / `busy_end`.
    """
    if technician is None or start is None or end is None:
        return None
    candidates = MaintenanceTicket.objects.filter(technician=technician).filter(
        Q(status__in=NOT_STARTED, planned_start__lt=end, planned_end__gt=start)
        | Q(status='in_progress', effective_start__lt=end)
    ).exclude(pk=exclude_pk).select_related('equipment', 'equipment__building', 'technician__user').order_by('planned_start')
    for ticket in candidates:
        interval = occupied_interval(ticket)
        if interval and interval[0] < end and interval[1] > start:
            ticket.busy_start, ticket.busy_end = interval
            return ticket
    return None


def schedule_conflict_message(conflict):
    """Message lisible (heure locale) pour un conflit trouvé par find_schedule_conflict()."""
    start, end = timezone.localtime(conflict.busy_start), timezone.localtime(conflict.busy_end)
    when = f"le {start:%d/%m} de {start:%H:%M} à {end:%H:%M}" if start.date() == end.date() \
        else f"du {start:%d/%m %H:%M} au {end:%d/%m %H:%M}"
    place = f"{conflict.equipment.name} – {conflict.equipment.building.name}"
    return f"{conflict.technician} est déjà affecté à l'intervention #{conflict.pk} ({place}) {when}."
