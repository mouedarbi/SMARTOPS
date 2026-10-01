"""
Fichier : services.py
Projet : SMARTOPS (Core Application)
Application : maintenance
Description : Opérations métier partagées entre l'application technicien et l'API.
"""

import os

from django.core.files import File
from django.db import transaction
from django.utils import timezone

from .models import MaintenanceTicket, InterventionPhoto


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
            f"Suite de l'intervention #{ticket.id} "
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
