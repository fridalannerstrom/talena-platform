from django import template
from django.utils import timezone


register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key, [])
    except Exception:
        return []


@register.filter
def last_active_compact(dt):
    if not dt:
        return "Aldrig"

    now = timezone.now()

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    seconds = max(int((now - dt).total_seconds()), 0)

    hour = 3600
    day = 86400

    if seconds < hour:
        return "mindre än 1 timme"

    if seconds < day:
        hours = seconds // hour
        return f"{hours} timme" if hours == 1 else f"{hours} timmar sedan"

    days = seconds // day
    return f"{days} dag" if days == 1 else f"{days} dagar sedan"
