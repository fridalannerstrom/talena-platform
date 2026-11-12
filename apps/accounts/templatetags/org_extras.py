from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """
    Safely get item from dict-like objects in Django templates.
    Usage: {{ mydict|get_item:somekey }}
    """
    if d is None:
        return None
    try:
        return d.get(key)
    except Exception:
        try:
            return d[key]
        except Exception:
            return None