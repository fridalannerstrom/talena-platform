from __future__ import annotations

from django import template
from django.utils.translation import get_language

from apps.reports.libraries.personality.competency_framework import (
    COMPETENCIES,
    COMPETENCY_TOKEN_PREFIX,
    competency_groups,
    competency_label,
    competency_token,
    parse_competency_token,
)
from .personality_i18n import personality_label


register = template.Library()


@register.simple_tag
def personality_question_competency_groups():
    return competency_groups(get_language() or "en")


@register.simple_tag
def personality_question_competency_label_map():
    language = get_language() or "en"
    return {
        competency_token(item["name"]): competency_label(
            item["name"],
            language,
        )
        for item in COMPETENCIES
    }


@register.simple_tag
def personality_question_selection_basis(selection):
    for item in selection or []:
        if parse_competency_token(item):
            return "competencies"
    return "traits"


@register.filter
def personality_question_focus_label(value):
    text = str(value or "").strip()
    if not text:
        return ""

    if text.casefold().startswith(COMPETENCY_TOKEN_PREFIX):
        return competency_label(text, get_language() or "en")

    return personality_label(text)
