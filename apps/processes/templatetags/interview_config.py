from django import template
from django.utils import translation

from apps.processes.interview_config import (
    get_interview_section_config,
)


register = template.Library()


@register.simple_tag(takes_context=True)
def interview_section_meta(context, key: str) -> dict:
    language_code = (
        context.get("LANGUAGE_CODE")
        or translation.get_language()
        or "en"
    )

    return get_interview_section_config(
        key,
        language_code=language_code,
    )
