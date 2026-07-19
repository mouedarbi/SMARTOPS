import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from inventory.models import Client, Building, EquipmentType, EquipmentTypeField, Equipment
from maintenance.models import Technician

User = get_user_model()

BELGIAN_CITIES = [
    ("Bruxelles", "1000", "Rue de la Loi"),
    ("Anvers", "2000", "Meir"),
    ("Gand", "9000", "Veldstraat"),
    ("Charleroi", "6000", "Boulevard Tirou"),
    ("Liège", "4000", "Rue de la Cathédrale"),
    ("Bruges", "8000", "Steenstraat"),
    ("Namur", "5000", "Rue de Fer"),
    ("Mons", "7000", "Grand Rue"),
    ("Louvain", "3000", "Bondgenotenlaan"),
    ("Alost", "9300", "Albert Lienaertstraat"),
    ("Malines", "2800", "Bruul"),
    ("La Louvière", "7100", "Rue Albert 1er"),
    ("Hasselt", "3500", "Demerstraat"),
    ("Courtrai", "8500", "Lange Steenstraat"),
    ("Ostende", "8400", "Kapellestraat"),
    ("Tournai", "7500", "Rue de l'Yser"),
    ("Genk", "3600", "Shoppingstraat"),
    ("Seraing", "4100", "Rue de la Fonderie"),
    ("Roulers", "8800", "Ooststraat"),
    ("Verviers", "4800", "Rue Brou-Crayloo"),
    ("Mouscron", "7700", "Petite Rue"),
    ("Beveren", "9120", "Warandestraat"),
    ("Dendermonde", "9200", "Oude Vest"),
    ("Beringen", "3580", "Koolmijnlaan"),
    ("Turnhout", "2300", "Gasthuisstraat"),
    ("Dilbeek", "1700", "Gemeenteplein"),
    ("Heist-op-den-Berg", "2220", "Bergstraat"),
    ("Sint-Niklaas", "9100", "Stationsstraat"),
    ("Waterloo", "1410", "Chaussée de Bruxelles"),
    ("Wavre", "1300", "Rue du Chemin de Fer"),
    ("Ixelles", "1050", "Chaussée d'Ixelles"),
    ("Uccle", "1180", "Avenue Brugmann"),
    ("Anderlecht", "1070", "Rue Wayez"),
    ("Schaerbeek", "1030", "Avenue Rogier"),
    ("Forest", "1190", "Chaussée de Neerstalle"),
    ("Saint-Gilles", "1060", "Chaussée de Waterloo"),
    ("Molenbeek", "1080", "Chaussée de Gand"),
    ("Jette", "1090", "Avenue de Secrétin"),
    ("Woluwe-Saint-Lambert", "1200", "Avenue Georges Henri"),
    ("Woluwe-Saint-Pierre", "1150", "Avenue de Tervueren"),
    ("Auderghem", "1160", "Chaussée de Wavre"),
    ("Etterbeek", "1040", "Rue de la Loi"),
    ("Halle", "1500", "Basiliekstraat"),
    ("Vilvorde", "1800", "Leuvensestraat"),
    ("Lokeren", "9160", "Kerkstraat"),
    ("Geel", "2440", "Nieuwstraat"),
    ("Brasschaat", "2930", "Bredabaan"),
    ("Herstal", "4040", "Rue Saint-Lambert"),
    ("Châtelet", "6200", "Rue de la Station"),
    ("Ottignies-Louvain-la-Neuve", "1340", "Grand Rue")
]

FIRST_NAMES = [
    "Jean", "Pierre", "Michel", "Philippe", "David", "Thomas", "Nicolas", "Marc", "Eric", "Marc",
    "Sophie", "Marie", "Isabelle", "Nathalie", "Sarah", "Julie", "Charlotte", "Emma", "Chantal", "Monique"
]

LAST_NAMES = [
    "Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Claes", "Wauters", "Lambrechts", "De Smet", "Hendrickx",
    "Dubois", "Lambert", "Martin", "Dupont", "Simon", "Leclercq", "Laurent", "Dumont", "Gérard", "Beckers"
]

CATEGORIES = {
    "Ascenseur": [
        ("Capacité (kg)", "number", True),
        ("Date dernier contrôle", "date", True),
        ("Marque", "text", False)
    ],
    "CVC": [
        ("Puissance (kW)", "number", True),
        ("Fluide Réfrigérant", "text", False),
        ("Type de filtre", "text", False)
    ],
    "Détecteur de fumée": [
        ("Autonomie pile (ans)", "number", True),
        ("Date de fabrication", "date", True)
    ],
    "Extincteur": [
        ("Type d'agent (CO2/Poudre/Eau)", "text", True),
        ("Poids (kg)", "number", True),
        ("Date de péremption", "date", True)
    ],
    "Alarme incendie": [
        ("Nombre de zones", "number", True),
        ("Type de centrale", "text", False)
    ]
}

def run_population():
    print("Début de l'importation des données belges...")

    # 1. Création des Utilisateurs
    # 1 Admin
    admin_user, created = User.objects.get_or_create(
        username="admin_belgique",
        defaults={
            "email": "admin_be@opensmartops.org",
            "role": "admin",
            "first_name": "Marc",
            "last_name": "Dubois"
        }
    )
    if created or not admin_user.check_password("AdminBE123!"):
        admin_user.set_password("AdminBE123!")
        admin_user.save()
        print("Admin créé/mis à jour.")

    # 2 Managers
    managers = []
    for i in range(1, 3):
        mgr, created = User.objects.get_or_create(
            username=f"manager_{i}",
            defaults={
                "email": f"manager_{i}@opensmartops.org",
                "role": "manager",
                "first_name": random.choice(FIRST_NAMES),
                "last_name": random.choice(LAST_NAMES)
            }
        )
        if created or not mgr.check_password("ManagerBE123!"):
            mgr.set_password("ManagerBE123!")
            mgr.save()
        managers.append(mgr)
    print("2 Managers créés/mis à jour.")

    # 20 Technicians
    technicians = []
    for i in range(1, 21):
        tech_user, created = User.objects.get_or_create(
            username=f"technicien_{i}",
            defaults={
                "email": f"technicien_{i}@opensmartops.org",
                "role": "technician",
                "first_name": random.choice(FIRST_NAMES),
                "last_name": random.choice(LAST_NAMES)
            }
        )
        if created or not tech_user.check_password("TechnicienBE123!"):
            tech_user.set_password("TechnicienBE123!")
            tech_user.save()
        
        # Récupération/mise à jour du profil Technicien
        # Le signal Django l'aura créé, mais on s'assure d'avoir des spécialités
        profile, _ = Technician.objects.get_or_create(user=tech_user)
        profile.specialties = random.sample(["Électricité", "CVC", "Ascenseurs", "Hydraulique", "Sécurité Incendie"], 2)
        profile.save()
        technicians.append(profile)
    print("20 Techniciens créés/mis à jour avec leurs profils.")

    # 2. Création des Catégories d'Équipements (Types et Champs personnalisés)
    types_map = {}
    for cat_name, fields in CATEGORIES.items():
        eq_type, created = EquipmentType.objects.get_or_create(name=cat_name)
        types_map[cat_name] = eq_type
        
        # Ajout des champs personnalisés
        for field_name, field_type, required in fields:
            EquipmentTypeField.objects.get_or_create(
                equipment_type=eq_type,
                field_name=field_name,
                defaults={"field_type": field_type, "required": required}
            )
    print("Catégories d'équipements et champs personnalisés configurés.")

    # 3. Création de 50 Clients Belges
    print("Création de 50 clients belges...")
    clients = []
    for idx, (city, zip_code, street) in enumerate(BELGIAN_CITIES, 1):
        client_name = f"Société {random.choice(LAST_NAMES)} Belux"
        if idx <= 10:
            client_name = f"Immo {city} SA"
        elif idx <= 20:
            client_name = f"Industrie du {city} SPRL"
            
        address = f"{street} {random.randint(1, 150)}, {zip_code} {city}, Belgique"
        contact = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"contact@{client_name.lower().replace(' ', '').replace('é', 'e').replace('è', 'e')}.be"
        phone = f"+32 {random.randint(2, 9)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
        vat = f"BE 0{random.randint(10000000, 99999999)} {random.randint(10, 99)}"

        client, created = Client.objects.get_or_create(
            vat_number=vat,
            defaults={
                "name": client_name,
                "address": address,
                "contact_name": contact,
                "email": email,
                "phone": phone
            }
        )
        clients.append(client)
    
    # 4. Création d'au moins 10 appareils par client (soit 500 appareils au total)
    print("Création de 10 appareils par client (500 au total)...")
    total_equipments = 0
    for client in clients:
        # Pour chaque client, on crée un bâtiment par défaut (ou plus)
        building, _ = Building.objects.get_or_create(
            client=client,
            name=f"Site principal - {client.name}",
            defaults={"address": client.address}
        )
        
        # Création de 10 équipements de catégories aléatoires pour ce bâtiment
        for eq_idx in range(1, 11):
            cat_name = random.choice(list(CATEGORIES.keys()))
            eq_type = types_map[cat_name]
            
            # Génération des champs personnalisés selon la catégorie
            custom_data = {}
            if cat_name == "Ascenseur":
                custom_data = {
                    "Capacité (kg)": random.choice([450, 630, 1000, 1500]),
                    "Date dernier contrôle": str(timezone.now().date() - timedelta(days=random.randint(10, 150))),
                    "Marque": random.choice(["Otis", "Kone", "Schindler", "ThyssenKrupp"])
                }
            elif cat_name == "CVC":
                custom_data = {
                    "Puissance (kW)": random.randint(10, 250),
                    "Fluide Réfrigérant": random.choice(["R410A", "R32", "R134a"]),
                    "Type de filtre": random.choice(["HEPA", "Poussière standard", "Filtre à charbon"])
                }
            elif cat_name == "Détecteur de fumée":
                custom_data = {
                    "Autonomie pile (ans)": random.choice([5, 10]),
                    "Date de fabrication": str(timezone.now().date() - timedelta(days=random.randint(100, 1000)))
                }
            elif cat_name == "Extincteur":
                custom_data = {
                    "Type d'agent (CO2/Poudre/Eau)": random.choice(["CO2", "Poudre ABC", "Eau + Additif"]),
                    "Poids (kg)": random.choice([2, 6, 9]),
                    "Date de péremption": str(timezone.now().date() + timedelta(days=random.randint(100, 1000)))
                }
            elif cat_name == "Alarme incendie":
                custom_data = {
                    "Nombre de zones": random.choice([4, 8, 16, 32]),
                    "Type de centrale": random.choice(["Adressable", "Conventionnelle"])
                }

            serial_number = f"SN-{cat_name[:3].upper()}-{client.id:03d}-{eq_idx:02d}-{random.randint(1000, 9999)}"
            
            Equipment.objects.get_or_create(
                serial_number=serial_number,
                defaults={
                    "building": building,
                    "name": f"{cat_name} {eq_idx}",
                    "equipment_type": eq_type,
                    "installed_at": timezone.now().date() - timedelta(days=random.randint(30, 2000)),
                    "custom_fields": custom_data
                }
            )
            total_equipments += 1

    print(f"Population terminée : {len(clients)} clients et {total_equipments} équipements créés avec succès !")
