from django import template
from django.utils import translation

from apps.processes.interview_config import (
    INTERVIEW_SECTION_DEFAULTS,
    get_available_interview_areas,
    get_completed_cognitive_test_keys,
    get_interview_section_config,
)

register = template.Library()


def _language(context):
    return context.get("LANGUAGE_CODE") or translation.get_language() or "en"


def _owner(context):
    return context.get("invitation") or context.get("inv")


@register.simple_tag(takes_context=True)
def interview_section_meta(context, key: str) -> dict:
    owner = _owner(context)
    completed_cognitive = (
        len(get_completed_cognitive_test_keys(owner))
        if key == "cognitive" and owner is not None
        else 0
    )
    return get_interview_section_config(
        key,
        language_code=_language(context),
        completed_cognitive_tests=completed_cognitive,
    )


@register.simple_tag(takes_context=True)
def interview_combined_sections(context) -> list[dict]:
    """
    Show every completed assessment's static questions even without saved AI
    questions. Keep the AI-question totals and stored payload untouched.
    The same tag works for the normal page and the refreshed partial.
    """
    existing = {
        section["key"]: dict(section)
        for section in (context.get("combined_question_sections") or [])
        if isinstance(section, dict) and section.get("key") in INTERVIEW_SECTION_DEFAULTS
    }
    owner = _owner(context)
    available = get_available_interview_areas(owner) if owner is not None else set()
    sections = []
    for key, defaults in sorted(
        INTERVIEW_SECTION_DEFAULTS.items(),
        key=lambda pair: pair[1]["order"],
    ):
        if key not in existing and key not in available:
            continue
        meta = get_interview_section_config(key, _language(context))
        section = existing.get(key, {
            "key": key,
            "questions": [],
            "question_count": 0,
            "estimated_minutes": meta["estimated_minutes"],
            "description": "",
        })
        section["title"] = meta["area_label"]
        section["description"] = meta["area_description"]
        sections.append(section)
    return sections
