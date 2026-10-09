"""
Donne à chaque technicien existant son calendrier django-scheduler. Les événements des tickets
restent dans le calendrier global ; chaque ticket assigné reçoit une copie de son événement dans
le calendrier de son technicien. La logique est recopiée ici (et non importée de
maintenance.calendars) pour figer la migration.
"""

from django.conf import settings
from django.db import migrations
from django.template.defaultfilters import slugify

GLOBAL_SLUG = "maintenance-globale"
GLOBAL_NAME = "Calendrier de Maintenance"
OWNER = "owner"
TICKET = "ticket"
ASSIGNMENT = "assignment"


def _technician_label(technician):
    user = technician.user
    return f"{user.first_name} {user.last_name}".strip() or user.username


def _event_bounds(ticket):
    start = ticket.effective_start or ticket.planned_start
    if ticket.effective_end:
        end = ticket.effective_end
    elif ticket.effective_start:
        end = ticket.effective_start + (ticket.planned_end - ticket.planned_start)
    else:
        end = ticket.planned_end
    return start, end


def create_technician_calendars(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Calendar = apps.get_model('schedule', 'Calendar')
    CalendarRelation = apps.get_model('schedule', 'CalendarRelation')
    Event = apps.get_model('schedule', 'Event')
    EventRelation = apps.get_model('schedule', 'EventRelation')
    Technician = apps.get_model('maintenance', 'Technician')
    MaintenanceTicket = apps.get_model('maintenance', 'MaintenanceTicket')

    technician_ct, _ = ContentType.objects.get_or_create(app_label='maintenance', model='technician')
    ticket_ct, _ = ContentType.objects.get_or_create(app_label='maintenance', model='maintenanceticket')
    global_calendar, _ = Calendar.objects.get_or_create(slug=GLOBAL_SLUG, defaults={'name': GLOBAL_NAME})

    calendars = {}
    for technician in Technician.objects.select_related('user'):
        relation = CalendarRelation.objects.filter(
            content_type=technician_ct, object_id=technician.pk, distinction=OWNER
        ).select_related('calendar').first()
        if relation:
            calendar = relation.calendar
        else:
            name = f"Planning technicien #{technician.pk} - {_technician_label(technician)}"
            calendar = Calendar.objects.create(name=name, slug=slugify(name))
            CalendarRelation.objects.create(
                calendar=calendar, content_type=technician_ct, object_id=technician.pk,
                distinction=OWNER, inheritable=True,
            )
        calendars[technician.pk] = calendar

    for ticket in MaintenanceTicket.objects.select_related('event', 'equipment', 'technician__user'):
        status_label = ticket.get_status_display().upper()
        technician = _technician_label(ticket.technician) if ticket.technician_id else None
        fields = {
            'title': f"[{status_label}] INT-{ticket.pk}: {ticket.equipment.name}",
            'description': f"Type: {ticket.get_type_display()}\nTechnicien: {technician}\nStatut: {status_label}",
        }

        # Événement global : créneau prévu, toujours dans le calendrier global.
        event = ticket.event
        if event is None:
            event = Event.objects.create(
                start=ticket.planned_start, end=ticket.planned_end, calendar=global_calendar, **fields
            )
            MaintenanceTicket.objects.filter(pk=ticket.pk).update(event=event)
        else:
            event.start, event.end, event.calendar = ticket.planned_start, ticket.planned_end, global_calendar
            event.save(update_fields=['start', 'end', 'calendar'])
        EventRelation.objects.get_or_create(
            event=event, content_type=ticket_ct, object_id=ticket.pk, distinction=TICKET,
        )

        # Copie dans le calendrier du technicien assigné : heures réelles dès qu'elles existent.
        if ticket.technician_id:
            calendar = calendars[ticket.technician_id]
            has_copy = EventRelation.objects.filter(
                content_type=ticket_ct, object_id=ticket.pk, distinction=ASSIGNMENT, event__calendar=calendar,
            ).exists()
            if not has_copy:
                start, end = _event_bounds(ticket)
                copy = Event.objects.create(start=start, end=end, calendar=calendar, **fields)
                EventRelation.objects.create(
                    event=copy, content_type=ticket_ct, object_id=ticket.pk, distinction=ASSIGNMENT,
                )


def remove_technician_calendars(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Calendar = apps.get_model('schedule', 'Calendar')
    CalendarRelation = apps.get_model('schedule', 'CalendarRelation')
    Event = apps.get_model('schedule', 'Event')
    EventRelation = apps.get_model('schedule', 'EventRelation')

    technician_ct = ContentType.objects.filter(app_label='maintenance', model='technician').first()
    ticket_ct = ContentType.objects.filter(app_label='maintenance', model='maintenanceticket').first()
    if technician_ct is None:
        return
    calendar_ids = list(CalendarRelation.objects.filter(
        content_type=technician_ct, distinction=OWNER
    ).values_list('calendar_id', flat=True))
    # Les copies sont dans les calendriers des techniciens : supprimés avec eux.
    Event.objects.filter(calendar_id__in=calendar_ids).delete()
    Calendar.objects.filter(pk__in=calendar_ids).delete()
    if ticket_ct is not None:
        EventRelation.objects.filter(content_type=ticket_ct, distinction__in=[TICKET, ASSIGNMENT]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0003_interventionphoto'),
        ('schedule', '0015_rename_calendarrelation_content_type_object_id_schedule_ca_content_cddadb_idx_and_more'),
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_technician_calendars, remove_technician_calendars),
    ]
