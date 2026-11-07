"""Expose the approved MQ practical guidance in the candidate report template."""

from django import template

from apps.core.ai.motivation_practical_advice import get_motivation_practical_advice


register = template.Library()


@register.simple_tag
def talena_motivation_practical_advice() -> dict:
    # json_script applies Django's HTML-safe JSON escaping in the template.
    return get_motivation_practical_advice()
