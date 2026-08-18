from django import template

from apps.processes.interview_config import (
    get_interview_section_config,
)


register = template.Library()


@register.simple_tag
def interview_section_meta(key: str) -> dict:
    return get_interview_section_config(key)
