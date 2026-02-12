from django import template
import re

register = template.Library()

@register.filter
def get_item(d, key):
    if not d:
        return None
    return d.get(key)


register = template.Library()

@register.filter
def get_item(d, key):
    return d.get(key) if d else None

@register.filter
def split_tests(value):
    """
    Splittar t.ex. "PQ, MQ" eller "PQ · MQ" eller "['PQ', 'MQ']" till en lista.
    """
    if not value:
        return []

    s = str(value).strip()

    # Om någon råkar spara som "['PQ', 'MQ']" eller '["PQ","MQ"]'
    if (s.startswith("[") and s.endswith("]")):
        # plocka ut ord mellan citationstecken
        items = re.findall(r'["\']([^"\']+)["\']', s)
        if items:
            return [x.strip() for x in items if x.strip()]

        # fallback: ta bort hakparenteser och splitta på comma
        s = s[1:-1]

    # normal split på , eller ·
    parts = re.split(r"\s*(?:,|·)\s*", s)
    return [p.strip() for p in parts if p.strip()]
