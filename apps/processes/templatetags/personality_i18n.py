"""Template filters for localized personality labels."""

from __future__ import annotations

from django import template
from django.utils.translation import get_language

from apps.reports.libraries.personality.content import TRAIT_PROFILE_CONTENT
from apps.reports.libraries.personality.definitions import (
    PERSONALITY_REPORT_DEFINITIONS,
)


register = template.Library()

_SECTION_LABELS_SV = {
    "leading and working with others": "Leda och arbeta med andra",
    "organisation and thinking style": "Organisering och tankemönster",
    "interacting and managing emotions": "Interaktion och känslohantering",
}


def _normalise(value) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .casefold()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def _first_translated_alias(canonical: str, aliases) -> str | None:
    canonical_key = _normalise(canonical)

    for alias in aliases or []:
        alias_text = str(alias or "").strip()

        if alias_text and _normalise(alias_text) != canonical_key:
            return alias_text

    return None


def _build_label_maps():
    swedish = {}
    english = {}

    for canonical, content in TRAIT_PROFILE_CONTENT.items():
        key = _normalise(canonical)
        swedish[key] = content.get("label_sv") or canonical
        english[key] = content.get("label_en") or canonical

    for report in PERSONALITY_REPORT_DEFINITIONS:
        for section in report.get("sections") or []:
            for trait in section.get("traits") or []:
                canonical = str(trait.get("trait_name") or "").strip()

                if not canonical:
                    continue

                key = _normalise(canonical)
                english.setdefault(key, canonical)

                translated_trait = _first_translated_alias(
                    canonical,
                    trait.get("aliases"),
                )

                if translated_trait:
                    swedish.setdefault(key, translated_trait)

                aliases_by_indicator = trait.get("indicator_aliases") or {}

                for indicator in trait.get("indicators") or []:
                    indicator_text = str(indicator or "").strip()

                    if not indicator_text:
                        continue

                    indicator_key = _normalise(indicator_text)
                    english.setdefault(indicator_key, indicator_text)

                    translated_indicator = _first_translated_alias(
                        indicator_text,
                        aliases_by_indicator.get(indicator_text),
                    )

                    if translated_indicator:
                        swedish.setdefault(
                            indicator_key,
                            translated_indicator,
                        )

    return swedish, english


_SWEDISH_LABELS, _ENGLISH_LABELS = _build_label_maps()


@register.filter
def personality_label(value):
    """Display a localized label while preserving the canonical stored name."""
    text = str(value or "").strip()

    if not text:
        return ""

    language = str(get_language() or "sv").lower()
    label_map = (
        _SWEDISH_LABELS
        if language.startswith("sv")
        else _ENGLISH_LABELS
    )

    return label_map.get(_normalise(text), text)


@register.filter
def personality_section_label(value):
    """Localize personality section headings without changing stored report data."""
    text = str(value or "").strip()
    if not text:
        return ""
    language = str(get_language() or "sv").lower()
    if language.startswith("sv"):
        return _SECTION_LABELS_SV.get(_normalise(text), text)
    return text


_PROFILE_GROUPS_SV = {
    "samverkande": "Leda och arbeta med andra",
    "collaborative": "Leda och arbeta med andra",
    "måldriven": "Organisering och tankemönster",
    "goal focused": "Organisering och tankemönster",
    "uppriktighet och regelstyrd": "Interaktion och känslohantering",
    "honesty and rule orientation": "Interaktion och känslohantering",
}

_PROFILE_GROUPS_EN = {
    "samverkande": "Leading and working with others",
    "collaborative": "Leading and working with others",
    "måldriven": "Organisation and thinking style",
    "goal focused": "Organisation and thinking style",
    "uppriktighet och regelstyrd": "Interacting and managing emotions",
    "honesty and rule orientation": "Interacting and managing emotions",
}


@register.filter
def personality_profile_group_label(section):
    """Label a profile group from its actual traits, not unreliable section metadata."""
    traits = getattr(section, "traits", None)
    if traits is None and isinstance(section, dict):
        traits = section.get("traits")
    traits = traits or []
    if not traits:
        return personality_section_label(
            section.get("section_name", "") if isinstance(section, dict)
            else getattr(section, "section_name", "")
        )

    first = traits[0]
    if isinstance(first, dict):
        candidate = first.get("label") or first.get("trait_name") or first.get("name") or ""
    else:
        candidate = getattr(first, "label", "") or getattr(first, "trait_name", "") or getattr(first, "name", "")
    key = _normalise(candidate)
    language = str(get_language() or "sv").lower()
    mapping = _PROFILE_GROUPS_SV if language.startswith("sv") else _PROFILE_GROUPS_EN
    return mapping.get(key, personality_section_label(
        section.get("section_name", "") if isinstance(section, dict)
        else getattr(section, "section_name", "")
    ))
