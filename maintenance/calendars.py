"""
Fichier : calendars.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Calendriers django-scheduler. Chaque ticket a son événement dans le calendrier
              global ; quand un technicien est assigné, une copie de cet événement est placée
              dans le calendrier propre à ce technicien.
"""

from django.contrib.contenttypes.models import ContentType
from schedule.models import Calendar, EventRelation

GLOBAL_CALENDAR_SLUG = "maintenance-globale"
GLOBAL_CALENDAR_NAME = "Calendrier de Maintenance"
# Nature du lien CalendarRelation entre un technicien et son calendrier.
OWNER = "owner"
# Nature du lien EventRelation entre l'événement global et son ticket.
TICKET = "ticket"
# Nature du lien EventRelation entre la copie dans le calendrier du technicien et son ticket.
ASSIGNMENT = "assignment"


def technician_calendar_name(technician):
    """Nom du calendrier d'un technicien ; le numéro rend le slug unique entre homonymes."""
    return f"Planning technicien #{technician.pk} - {technician}"


def get_global_calendar():
    """Calendrier des interventions sans technicien."""
    calendar, _ = Calendar.objects.get_or_create(
        slug=GLOBAL_CALENDAR_SLUG, defaults={'name': GLOBAL_CALENDAR_NAME}
    )
    return calendar


def get_technician_calendar(technician):
    """Calendrier du technicien, créé au besoin et relié à lui par une CalendarRelation « owner »."""
    return Calendar.objects.get_or_create_calendar_for_object(
        technician, distinction=OWNER, name=technician_calendar_name(technician)
    )


def assignment_events(ticket):
    """Copies de l'événement du ticket dans les calendriers des techniciens (au plus une en pratique)."""
    return EventRelation.objects.get_events_for_object(ticket, ASSIGNMENT, inherit=False)


def assigned_ticket_ids(calendar):
    """Identifiants des tickets dont une copie est dans ce calendrier de technicien."""
    from .models import MaintenanceTicket
    return EventRelation.objects.filter(
        content_type=ContentType.objects.get_for_model(MaintenanceTicket),
        distinction=ASSIGNMENT,
        event__calendar=calendar,
    ).values('object_id')


def ticket_event_bounds(ticket):
    """
    Début et fin affichés : le réel prime sur le prévu. Une intervention en cours sans fin réelle
    occupe sa durée prévue à partir du démarrage, comme dans occupied_interval().
    """
    start = ticket.effective_start or ticket.planned_start
    if ticket.effective_end:
        end = ticket.effective_end
    elif ticket.effective_start:
        end = ticket.effective_start + (ticket.planned_end - ticket.planned_start)
    else:
        end = ticket.planned_end
    return start, end
