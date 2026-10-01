import re

from django import template
from django.urls import reverse
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()

TICKET_REF = re.compile(r'\b(ticket|intervention) #(\d+)', re.IGNORECASE)


def referenced_ticket_ids(text):
    """Numéros de tickets cités dans un texte (« ticket #12 », « intervention #12 »)."""
    return {int(m.group(2)) for m in TICKET_REF.finditer(text or '')}


@register.simple_tag
def ticket_links(text, url_name, allowed_ids=None):
    """
    Échappe le texte et transforme les références « ticket #N » / « intervention #N »
    en liens vers `url_name`. Si `allowed_ids` est fourni, seuls ces tickets sont liés.
    """
    def link(match):
        pk = int(match.group(2))
        if allowed_ids is not None and pk not in allowed_ids:
            return match.group(0)
        return format_html('<a href="{}" class="underline font-bold not-italic">{}</a>',
                           reverse(url_name, args=[pk]), match.group(0))

    return mark_safe(TICKET_REF.sub(link, str(conditional_escape(text or ''))))
