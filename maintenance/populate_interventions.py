import os
import sys
import django
import random
from datetime import timedelta

# Configuration Django et ajout du chemin racine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartops_project.settings')
django.setup()

from django.utils import timezone
from inventory.models import Equipment
from maintenance.models import Technician, MaintenanceTicket

def run():
    print("Début de la génération de 100 interventions...")
    
    # Récupération de tous les techniciens et équipements
    technicians = list(Technician.objects.filter(is_active=True))
    equipments = list(Equipment.objects.all())
    
    if not technicians:
        print("Erreur : Aucun technicien trouvé dans la base de données. Exécutez d'abord populate_data.py.")
        return
    if not equipments:
        print("Erreur : Aucun équipement trouvé dans la base de données. Exécutez d'abord populate_data.py.")
        return

    # Nettoyage préalable des tickets pour repartir sur une base propre
    print("Nettoyage des anciens tickets de maintenance...")
    MaintenanceTicket.objects.all().delete()

    # Descriptions réalistes
    past_descriptions = [
        ("Entretien périodique standard et nettoyage", "Visite de maintenance préventive effectuée. Dépoussiérage complet, resserrage des connexions électriques et vérification générale. RAS."),
        ("Remplacement préventif des filtres et vérification de pression", "Filtres encrassés remplacés par des neufs. Test d'étanchéité réalisé. Pression nominale correcte. Système parfaitement fonctionnel."),
        ("Dépannage d'urgence suite à une panne de signalisation", "Intervention curative. Remplacement du fusible de commande grillé. Reprogrammation du contrôleur. Tests fonctionnels OK."),
        ("Contrôle annuel de conformité et de sécurité", "Audit de sécurité périodique. L'équipement répond aux normes belges de sécurité. Rapport d'inspection visuel OK."),
        ("Remplacement de pièces d'usure (courroies et joints)", "Courroies d'entraînement détendues remplacées. Remplacement du joint d'étanchéité principal. Nettoyage de la zone de travail."),
    ]
    
    future_descriptions = [
        "Maintenance préventive semestrielle réglementaire",
        "Contrôle technique annuel obligatoire",
        "Remplacement programmé des pièces d'usure",
        "Vérification des organes de sécurité et tests d'alarme",
        "Dépoussiérage et calibration des sondes de contrôle",
    ]

    total_tickets = 100
    past_count = 30
    future_count = 70
    
    now = timezone.now()
    # Limite supérieure : 31 octobre 2026
    october_limit = timezone.make_aware(timezone.datetime(2026, 10, 31, 23, 59, 59))
    
    created_past = 0
    created_future = 0
    
    # 1. Génération des 30 interventions passées
    for i in range(past_count):
        tech = random.choice(technicians)
        eq = random.choice(equipments)
        desc_pair = random.choice(past_descriptions)
        
        # Date dans le passé (entre 1 an et 1 jour)
        days_ago = random.randint(1, 365)
        start_hour = random.randint(8, 16)
        start_minute = random.choice([0, 15, 30, 45])
        
        planned_start = now - timedelta(days=days_ago)
        planned_start = planned_start.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        duration_hours = random.randint(1, 3)
        planned_end = planned_start + timedelta(hours=duration_hours)
        
        # Heures réelles légèrement décalées
        effective_start = planned_start + timedelta(minutes=random.randint(-15, 15))
        effective_end = effective_start + timedelta(hours=duration_hours, minutes=random.randint(-10, 30))
        
        # Latitude et Longitude belges (environ 50.85, 4.35)
        lat = 50.85 + random.uniform(-0.5, 0.5)
        lon = 4.35 + random.uniform(-0.5, 0.5)
        
        MaintenanceTicket.objects.create(
            equipment=eq,
            technician=tech,
            type=random.choice(["maintenance", "repair"]),
            planned_start=planned_start,
            planned_end=planned_end,
            effective_start=effective_start,
            effective_end=effective_end,
            start_latitude=lat,
            start_longitude=lon,
            status="done",
            description=desc_pair[0],
            intervention_report=desc_pair[1]
        )
        created_past += 1

    # 2. Génération des 70 interventions futures
    # Pour s'assurer que les dates ne dépassent pas le 31 octobre 2026
    delta_total_seconds = int((october_limit - now).total_seconds())
    
    for i in range(future_count):
        eq = random.choice(equipments)
        desc = random.choice(future_descriptions)
        
        # Date dans le futur (entre 1 jour et la limite d'octobre 2026)
        random_seconds = random.randint(24*3600, delta_total_seconds)
        planned_start = now + timedelta(seconds=random_seconds)
        
        # Ramener les heures pendant la journée de travail (8h - 17h)
        start_hour = random.randint(8, 16)
        start_minute = random.choice([0, 15, 30, 45])
        planned_start = planned_start.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        duration_hours = random.randint(1, 3)
        planned_end = planned_start + timedelta(hours=duration_hours)
        
        # Statut (planned ou pending)
        status = random.choice(["planned", "planned", "pending"])  # 66% planned, 33% pending
        tech = random.choice(technicians) if status == "planned" else None
        ticket_type = "maintenance" if status == "planned" else random.choice(["maintenance", "repair", "emergency"])
        
        MaintenanceTicket.objects.create(
            equipment=eq,
            technician=tech,
            type=ticket_type,
            planned_start=planned_start,
            planned_end=planned_end,
            status=status,
            description=desc,
            intervention_report=""
        )
        created_future += 1

    print(f"Population réussie ! {created_past} interventions passées (clôturées) et {created_future} interventions futures (jusqu'en octobre 2026) créées.")

if __name__ == '__main__':
    run()
