"""
Met en cohérence le statut des interventions pas encore démarrées avec leur assignation :
« Planifié » avec un technicien, « En attente » sans. Seuls le statut et le titre des
événements de calendrier changent ; rien n'est fait à l'inverse.
"""

from django.db import migrations

LABELS = {'pending': "EN ATTENTE", 'planned': "PLANIFIÉ"}


def align_not_started_status(apps, schema_editor):
    MaintenanceTicket = apps.get_model('maintenance', 'MaintenanceTicket')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    EventRelation = apps.get_model('schedule', 'EventRelation')
    ticket_ct = ContentType.objects.filter(app_label='maintenance', model='maintenanceticket').first()

    mismatched = [
        (ticket, 'planned')
        for ticket in MaintenanceTicket.objects.filter(status='pending', technician__isnull=False)
    ] + [
        (ticket, 'pending')
        for ticket in MaintenanceTicket.objects.filter(status='planned', technician__isnull=True)
    ]
    for ticket, status in mismatched:
        old_tag, new_tag = f"[{LABELS[ticket.status]}]", f"[{LABELS[status]}]"
        MaintenanceTicket.objects.filter(pk=ticket.pk).update(status=status)
        # Événement global et copie éventuelle chez le technicien.
        events = []
        if ticket.event_id:
            events.append(ticket.event)
        if ticket_ct is not None:
            events += [
                relation.event for relation in EventRelation.objects.filter(
                    content_type=ticket_ct, object_id=ticket.pk, distinction='assignment',
                ).select_related('event')
            ]
        for event in events:
            event.title = event.title.replace(old_tag, new_tag, 1)
            event.description = event.description.replace(f"Statut: {LABELS[ticket.status]}", f"Statut: {LABELS[status]}", 1)
            event.save(update_fields=['title', 'description'])


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0004_technician_calendars'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('schedule', '0015_rename_calendarrelation_content_type_object_id_schedule_ca_content_cddadb_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(align_not_started_status, migrations.RunPython.noop),
    ]
