from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from apps.core.ai.cognitive_interpretation import extract_cognitive_results
from apps.core.ai.language import normalize_ai_language
from apps.core.ai.motivation_interpretation import (
    _owner_motivation_results,
    get_motivation_factor_display_name,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
)
from apps.reports.libraries.cognitive.candidate_result_content import (
    CANDIDATE_SKILL_COPY_VERSION,
    CANDIDATE_SKILL_TITLES,
    resolve_candidate_skill_text,
)
from apps.reports.libraries.motivation.candidate_result_content import (
    CANDIDATE_MOTIVATION_COPY_VERSION,
    CANDIDATE_RESULT_COPY as CANDIDATE_MOTIVATION_COPY,
    CANDIDATE_RESULT_SECTION_COPY,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)
from apps.reports.libraries.personality.builder import get_score_band, normalize_sten

from .models import CandidateResultSnapshot


CANDIDATE_RESULT_CONTENT_VERSION = "candidate-static-v5"
_PERSONALITY_LIBRARY_DIR = (
    Path(__file__).parents[1]
    / "reports"
    / "libraries"
    / "personality"
)
with (_PERSONALITY_LIBRARY_DIR / "candidate_content_sv.json").open(
    encoding="utf-8"
) as _personality_library_file:
    CANDIDATE_PERSONALITY_CONTENT_SV = json.load(
        _personality_library_file
    )
with (_PERSONALITY_LIBRARY_DIR / "candidate_content_en.json").open(
    encoding="utf-8"
) as _personality_translation_file:
    CANDIDATE_PERSONALITY_CONTENT_EN = json.load(
        _personality_translation_file
    )

_CANDIDATE_PERSONALITY_TEXTS_EN = {
    indicator_key: dict(zip(
        CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"],
        sentences,
    ))
    for indicator_key, sentences in (
        CANDIDATE_PERSONALITY_CONTENT_EN["indicators"].items()
    )
}
_EXPECTED_PERSONALITY_INDICATORS = {
    indicator["key"]
    for trait in CANDIDATE_PERSONALITY_CONTENT_SV.get("traits", [])
    for indicator in trait.get("indicators", [])
}
_TRANSLATED_PERSONALITY_INDICATORS = set(
    CANDIDATE_PERSONALITY_CONTENT_EN.get("indicators", {})
)
_MISSING_PERSONALITY_TRANSLATIONS = (
    _EXPECTED_PERSONALITY_INDICATORS - _TRANSLATED_PERSONALITY_INDICATORS
)
_EXTRA_PERSONALITY_TRANSLATIONS = (
    _TRANSLATED_PERSONALITY_INDICATORS - _EXPECTED_PERSONALITY_INDICATORS
)
_INVALID_PERSONALITY_TRANSLATION_LENGTHS = {
    indicator_key: len(sentences)
    for indicator_key, sentences in (
        CANDIDATE_PERSONALITY_CONTENT_EN.get("indicators", {}).items()
    )
    if (
        len(sentences)
        != len(CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"])
        or any(not str(sentence).strip() for sentence in sentences)
    )
}
if (
    _MISSING_PERSONALITY_TRANSLATIONS
    or _EXTRA_PERSONALITY_TRANSLATIONS
    or _INVALID_PERSONALITY_TRANSLATION_LENGTHS
    or CANDIDATE_PERSONALITY_CONTENT_EN.get("score_bands")
    != CANDIDATE_PERSONALITY_CONTENT_SV.get("score_bands")
):
    raise ValueError(
        "English candidate personality copy must provide exactly one "
        "translation for every source indicator and score band."
    )


_FIXED_COPY = {
    "sv": {
        "introduction_title": "Ditt resultat",
        "introduction_body": (
            "Resultatet beskriver möjliga preferenser och tendenser utifrån dina svar. "
            "Det är inte en absolut sanning eller ett betyg, utan ett underlag för en vidare dialog."
        ),
        "personality_title": "Personlighet",
        "skills_title": "Färdigheter",
        "motivation_title": "Motivation",
        "top_motivators_title": CANDIDATE_RESULT_SECTION_COPY["sv"]["title"],
    },
    "en": {
        "introduction_title": "Your result",
        "introduction_body": (
            "The result describes possible preferences and tendencies based on your responses. "
            "It is not an absolute truth or a grade, but a basis for further conversation."
        ),
        "personality_title": "Personality",
        "skills_title": "Skills",
        "motivation_title": "Motivation",
        "top_motivators_title": CANDIDATE_RESULT_SECTION_COPY["en"]["title"],
    },
}




def _normalise_name(value: Any) -> str:
    value = str(value or "").strip().casefold().replace("&", "and")
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()


def _personality_indicator_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for indicator_key, content in INDICATOR_PROFILE_CONTENT.items():
        for alias in (
            indicator_key,
            content.get("label_sv"),
            content.get("label_en"),
        ):
            normalized = _normalise_name(alias)
            if normalized:
                lookup[normalized] = indicator_key
    return lookup


_PERSONALITY_INDICATOR_LOOKUP = _personality_indicator_lookup()


def _personality_results(invitation) -> dict[str, int]:
    """Return available personality indicator STEN values by library key."""
    results: dict[str, int] = {}
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        activity_name = _normalise_name(activity.get("activity"))
        if not any(
            marker in activity_name
            for marker in ("personality", "personality questionnaire", "personlighet", "trait")
        ):
            continue

        for competency in activity.get("competencies") or []:
            if not isinstance(competency, dict):
                continue
            competency_name = competency.get("competency") or competency.get("name")
            key = _PERSONALITY_INDICATOR_LOOKUP.get(_normalise_name(competency_name))
            if not key:
                continue

            sten = normalize_sten(competency.get("sten_rounded"))
            if sten is None:
                sten = normalize_sten(competency.get("sten"))
            if sten is not None:
                results[key] = sten
    return results


def _candidate_personality_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    scores = _personality_results(invitation)
    if not scores:
        return []

    workbook_traits = {
        trait["key"]: trait
        for trait in CANDIDATE_PERSONALITY_CONTENT_SV.get("traits", [])
    }
    section_titles = {
        "sv": {
            "leading_and_working_with_others": "Leda och arbeta med andra",
            "organisation_and_thinking_style": "Organisering och tankemönster",
            "interacting_and_managing_emotions": "Interaktion och känslohantering",
        },
        "en": {
            "leading_and_working_with_others": "Leading and Working with Others",
            "organisation_and_thinking_style": "Organising and Thought Patterns",
            "interacting_and_managing_emotions": "Interaction and Emotional Regulation",
        },
    }
    groups = []
    for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
        sentences = []
        for trait_definition in section["traits"]:
            trait_key = trait_definition["trait_name"]
            workbook_trait = workbook_traits.get(trait_key, {})
            indicator_definitions = {
                item["key"]: item
                for item in workbook_trait.get("indicators", [])
            }

            for indicator_key in trait_definition.get("indicators", []):
                sten = scores.get(indicator_key)
                score_band = get_score_band(sten)
                if score_band is None:
                    continue

                if language_code == "sv":
                    candidate_text = indicator_definitions.get(
                        indicator_key,
                        {},
                    )
                    text = candidate_text.get(
                        "score_texts",
                        {},
                    ).get(score_band, "")
                else:
                    text = _CANDIDATE_PERSONALITY_TEXTS_EN.get(
                        indicator_key,
                        {},
                    ).get(score_band, "")

                if text and text.strip():
                    sentences.append(text.strip())

        if not sentences:
            continue

        title = (
            section_titles[language_code].get(section["section_key"])
            or section["section_name"]
        )
        groups.append({
            "title": title,
            "body": " ".join(sentences),
        })
    return groups


def _candidate_skills_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    cognitive_results = extract_cognitive_results(invitation)
    percentiles = {}
    for result in cognitive_results:
        percentiles.setdefault(result["key"], result["percentile"])

    # Some Sova payloads label the activity generically (for example,
    # "Skills") while naming the actual ability in each competency.
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        activity_name = _normalise_name(activity.get("activity"))
        for competency in activity.get("competencies") or []:
            if not isinstance(competency, dict):
                continue
            competency_name = _normalise_name(
                competency.get("competency") or competency.get("name")
            )
            source_name = f"{activity_name} {competency_name}"
            key = next(
                (
                    result_key
                    for result_key, keywords in (
                        ("logical", ("logical", "logisk")),
                        ("numerical", ("numerical", "numeric", "numerisk")),
                        ("verbal", ("verbal",)),
                    )
                    if any(keyword in source_name for keyword in keywords)
                ),
                None,
            )
            percentile = competency.get("percentile")
            if key and percentile is not None:
                percentiles.setdefault(key, percentile)

    if not percentiles:
        return []

    groups = []
    for key in ("logical", "numerical", "verbal"):
        percentile = percentiles.get(key)
        if percentile is None:
            continue
        interpretation = resolve_candidate_skill_text(
            key,
            percentile,
            language_code=language_code,
        )
        title = CANDIDATE_SKILL_TITLES.get(language_code, {}).get(key)
        if not interpretation or not title:
            continue
        groups.append(
            {
                "title": title,
                "items": [{"label": "", "text": interpretation}],
            }
        )
    return groups


def _candidate_motivation_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    results = sorted(
        _owner_motivation_results(invitation),
        key=lambda item: (-float(item["score"]), item["key"]),
    )[:3]

    items = []
    for result in results:
        key = result["key"]
        text = CANDIDATE_MOTIVATION_COPY.get(language_code, {}).get(key, "")
        if not text:
            continue

        label = get_motivation_factor_display_name(
            result.get("name") or key,
            language_code=language_code,
        )
        items.append({"label": label, "text": text})

    if not items:
        return []
    return [{
        "title": _FIXED_COPY[language_code]["top_motivators_title"],
        "items": items,
    }]


def _area_content(title: str, groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not groups:
        return None
    return {"title": title, "body": "", "points": [], "groups": groups}


def build_static_candidate_result_content(
    invitation,
    *,
    language_code: str = "sv",
) -> dict[str, Any]:
    """Build the candidate report from approved static libraries only."""
    language_code = normalize_ai_language(language_code)
    language_code = language_code if language_code in {"sv", "en"} else "sv"
    copy = _FIXED_COPY[language_code]

    content: dict[str, Any] = {
        "library_version": CANDIDATE_RESULT_CONTENT_VERSION,
        "personality_library_version": (
            f'{CANDIDATE_PERSONALITY_CONTENT_SV.get("library_version", "")}/'
            f'{CANDIDATE_PERSONALITY_CONTENT_EN.get("library_version", "")}'
        ),
        "static_library_versions": {
            "personality": (
                f'{CANDIDATE_PERSONALITY_CONTENT_SV.get("library_version", "")}/'
                f'{CANDIDATE_PERSONALITY_CONTENT_EN.get("library_version", "")}'
            ),
            "skills": CANDIDATE_SKILL_COPY_VERSION,
            "motivation": CANDIDATE_MOTIVATION_COPY_VERSION,
        },
        "introduction": {
            "title": copy["introduction_title"],
            "body": copy["introduction_body"],
        },
        "personality": _area_content(
            copy["personality_title"],
            _candidate_personality_groups(
                invitation,
                language_code=language_code,
            ),
        ),
        "skills": _area_content(
            copy["skills_title"],
            _candidate_skills_groups(
                invitation,
                language_code=language_code,
            ),
        ),
        "motivation": _area_content(
            copy["motivation_title"],
            _candidate_motivation_groups(
                invitation,
                language_code=language_code,
            ),
        ),
    }
    return {key: value for key, value in content.items() if value is not None}


def build_candidate_result_content(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Compatibility entry point that now returns static content, never AI text."""
    content = build_static_candidate_result_content(
        invitation,
        language_code=language_code,
    )
    source_fingerprint = hashlib.sha256(
        json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    library_metadata = {
        "content_version": CANDIDATE_RESULT_CONTENT_VERSION,
        "personality_library_version": content.get(
            "personality_library_version",
            "",
        ),
        "static_library_versions": content.get("static_library_versions", {}),
        "locale": normalize_ai_language(language_code),
    }
    return content, library_metadata, source_fingerprint


def ensure_candidate_result_snapshot_current(
    snapshot: CandidateResultSnapshot | None,
) -> tuple[CandidateResultSnapshot | None, bool]:
    """Refresh changed static copy or replace a legacy AI snapshot."""
    if snapshot is None:
        return None, False
    if snapshot.content_version == CANDIDATE_RESULT_CONTENT_VERSION:
        return snapshot, False

    content, _library_metadata, fingerprint = build_candidate_result_content(
        snapshot.invitation,
        language_code=snapshot.locale,
    )

    old_content = snapshot.content if isinstance(snapshot.content, dict) else {}
    old_prompt_versions = (
        snapshot.prompt_versions
        if isinstance(snapshot.prompt_versions, dict)
        else {}
    )

    updated = CandidateResultSnapshot.objects.filter(
        pk=snapshot.pk,
    ).exclude(
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
    ).update(
        content=content,
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
        legacy_content=snapshot.legacy_content or old_content,
        legacy_prompt_versions=(
            snapshot.legacy_prompt_versions or old_prompt_versions
        ),
        prompt_versions={},
        source_fingerprint=fingerprint,
    )
    snapshot.refresh_from_db()
    return snapshot, bool(updated)


def create_candidate_result_snapshot(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[CandidateResultSnapshot, bool]:
    """Create a static snapshot, or safely upgrade an earlier AI snapshot."""
    if not invitation.process.candidate_results_enabled:
        raise ValueError("Candidate results are not enabled for this process.")
    if invitation.status != "completed":
        raise ValueError("Candidate result snapshots require a completed invitation.")

    existing = CandidateResultSnapshot.objects.filter(invitation=invitation).first()
    if existing:
        current, upgraded = ensure_candidate_result_snapshot_current(existing)
        return current, upgraded

    content, _library_metadata, source_fingerprint = build_candidate_result_content(
        invitation,
        language_code=language_code,
    )
    snapshot = CandidateResultSnapshot.objects.create(
        invitation=invitation,
        candidate=invitation.candidate,
        process=invitation.process,
        locale=normalize_ai_language(language_code),
        content=content,
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
        prompt_versions={},
        source_fingerprint=source_fingerprint,
    )
    return snapshot, True
