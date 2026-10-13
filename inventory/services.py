"""
Fichier : services.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Archivage des clients, lieux et appareils, partagé entre l'interface web et l'API.
              Les interventions servent de preuve (responsabilité de la société) : un élément qui a
              un historique est archivé, jamais supprimé.
"""

from django.db import transaction
from django.utils.translation import gettext as _, ngettext

from maintenance.models import MaintenanceTicket

from .models import Building, Client, Equipment

# Interventions qui attendent encore d'être faites : elles empêchent l'archivage.
OPEN_STATUSES = ('pending', 'planned', 'in_progress')


class ArchiveError(Exception):
    """Archivage ou réactivation refusé ; le message est destiné à l'utilisateur."""


def _equipments(obj):
    """Appareils concernés par l'archivage d'un client, d'un lieu ou d'un appareil."""
    if isinstance(obj, Client):
        return Equipment.objects.filter(building__client=obj)
    if isinstance(obj, Building):
        return Equipment.objects.filter(building=obj)
    return Equipment.objects.filter(pk=obj.pk)


def open_tickets(obj):
    """Interventions en attente, planifiées ou en cours sur le client, le lieu ou l'appareil."""
    return MaintenanceTicket.objects.filter(equipment__in=_equipments(obj), status__in=OPEN_STATUSES)


def archive(obj):
    """
    Archive un client, un lieu ou un appareil, avec ce qu'il contient (lieux et appareils d'un
    client, appareils d'un lieu). Refusé tant qu'une intervention y est en attente, planifiée ou en
    cours : il faut d'abord la terminer, l'annuler ou la déplacer.
    """
    count = open_tickets(obj).count()
    if count:
        raise ArchiveError(ngettext(
            "Archivage impossible : %(count)s intervention est encore en attente, planifiée ou en cours. "
            "Terminez-la ou annulez-la d'abord.",
            "Archivage impossible : %(count)s interventions sont encore en attente, planifiées ou en cours. "
            "Terminez-les ou annulez-les d'abord.",
            count,
        ) % {'count': count})
    with transaction.atomic():
        _equipments(obj).update(is_active=False)
        if isinstance(obj, Client):
            obj.buildings.update(is_active=False)
        obj.is_active = False
        obj.save(update_fields=['is_active'])


def restore(obj):
    """
    Réactive un client, un lieu ou un appareil, seul : ses lieux ou appareils archivés restent
    archivés et se réactivent un par un. Refusé si son client ou son lieu est encore archivé.
    """
    if isinstance(obj, Building) and not obj.client.is_active:
        raise ArchiveError(_("Réactivez d'abord le client de ce lieu."))
    if isinstance(obj, Equipment) and not obj.building.is_active:
        raise ArchiveError(_("Réactivez d'abord le lieu de cet appareil."))
    obj.is_active = True
    obj.save(update_fields=['is_active'])
