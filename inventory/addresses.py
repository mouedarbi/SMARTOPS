"""
Fichier : addresses.py
Projet : SMARTOPS (Core Application)
Application : inventory
Auteur : Mohamed Ouedarbi
Version : 1.0
Description : Adresse structurée d'un lieu (format des balises addr:* d'OpenStreetMap) :
              découpage d'une adresse libre, recomposition et lien d'itinéraire.
"""

import re
from urllib.parse import quote_plus

# Pays proposés (code ISO 3166-1 alpha-2, comme addr:country dans OpenStreetMap).
COUNTRY_CHOICES = [
    ('BE', 'Belgique'),
    ('FR', 'France'),
    ('NL', 'Pays-Bas'),
    ('LU', 'Luxembourg'),
    ('DE', 'Allemagne'),
]
COUNTRY_NAMES = dict(COUNTRY_CHOICES)

# « Rue de la Loi 12 bte 3, 1000 Bruxelles, Belgique » (pays facultatif).
ADDRESS_PATTERN = re.compile(
    r'^(?P<street>.+?)\s+(?P<house_number>\d+[A-Za-z]?)'
    r'(?:\s*(?:bte|bus|boîte)\s*(?P<box>\S+))?'
    r',\s*(?P<postal_code>\d{4,5})\s+(?P<city>[^,]+?)'
    r'(?:,\s*(?P<country>[^,]+))?$'
)


def parse_address(text):
    """
    Découpe une adresse libre au format « Rue N[ bte B], CP Ville[, Pays] ».
    Retourne un dict (street, house_number, box, postal_code, city, country) ou None si
    l'adresse ne suit pas ce format.
    """
    match = ADDRESS_PATTERN.match(' '.join((text or '').split()))
    if not match:
        return None
    parts = {key: (value or '').strip() for key, value in match.groupdict().items()}
    names_to_codes = {name.lower(): code for code, name in COUNTRY_CHOICES}
    parts['country'] = names_to_codes.get(parts['country'].lower(), 'BE')
    return parts


def format_address(street, house_number='', box='', postal_code='', city='', country=''):
    """Adresse complète sur une ligne : « Rue de la Loi 12 bte 3, 1000 Bruxelles, Belgique »."""
    line = ' '.join(part for part in (street, house_number) if part)
    if box:
        line += f' bte {box}'
    locality = ' '.join(part for part in (postal_code, city) if part)
    return ', '.join(part for part in (line, locality, COUNTRY_NAMES.get(country, country)) if part)


def navigation_url(address):
    """
    Lien d'itinéraire universel Google Maps : ouvre l'application de navigation sur
    Android et iOS (Google Maps), ou le site sur ordinateur, avec l'adresse en destination.
    """
    return 'https://www.google.com/maps/dir/?api=1&destination=' + quote_plus(address)
