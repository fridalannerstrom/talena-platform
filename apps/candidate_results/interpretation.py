from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from apps.core.ai.cognitive_interpretation import extract_cognitive_results
from apps.core.ai.language import normalize_ai_language
from apps.core.ai.motivation_interpretation import (
    MOTIVATION_DEFINITIONS,
    _owner_motivation_results,
    get_motivation_factor_display_name,
)
from apps.processes.services.cognitive_insights import (
    build_cognitive_insight_results,
)
from apps.processes.templatetags.motivation_i18n import FACTOR_CONTENT
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)
from apps.reports.libraries.personality.builder import get_score_band, normalize_sten

from .models import CandidateResultSnapshot


CANDIDATE_RESULT_CONTENT_VERSION = "candidate-static-v1"
_PERSONALITY_LIBRARY_PATH = Path(__file__).parents[1] / "reports" / "libraries" / "personality" / "candidate_content_sv.json"
with _PERSONALITY_LIBRARY_PATH.open(encoding="utf-8") as _personality_library_file:
    CANDIDATE_PERSONALITY_CONTENT_SV = json.load(_personality_library_file)


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
        "top_motivators_title": "Dina tre främsta drivkrafter",
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
        "top_motivators_title": "Your Top 3 Motivators",
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
    groups = []
    for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
        for trait_definition in section["traits"]:
            trait_key = trait_definition["trait_name"]
            workbook_trait = workbook_traits.get(trait_key, {})
            indicator_definitions = {
                item["key"]: item
                for item in workbook_trait.get("indicators", [])
            }
            trait_content = TRAIT_PROFILE_CONTENT.get(trait_key, {})
            items = []

            for indicator_key in trait_definition.get("indicators", []):
                sten = scores.get(indicator_key)
                score_band = get_score_band(sten)
                if score_band is None:
                    continue

                indicator_content = INDICATOR_PROFILE_CONTENT.get(indicator_key, {})
                if language_code == "sv":
                    candidate_text = indicator_definitions.get(indicator_key, {})
                    label = candidate_text.get("label_sv") or indicator_content.get("label_sv") or indicator_key
                    text = candidate_text.get("score_texts", {}).get(score_band, "")
                else:
                    label = indicator_content.get("label_en") or indicator_key
                    text = (
                        indicator_content.get("score_texts", {})
                        .get(score_band, {})
                        .get("en", "")
                    )

                if text:
                    items.append({"label": label, "text": text})

            if not items:
                continue

            if language_code == "sv":
                title = workbook_trait.get("label_sv") or trait_content.get("label_sv") or trait_key
            else:
                title = trait_content.get("label_en") or trait_key
            groups.append({"title": title, "items": items})
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

    localised_results = build_cognitive_insight_results(
        verbal_percentile=percentiles.get("verbal"),
        logical_percentile=percentiles.get("logical"),
        numerical_percentile=percentiles.get("numerical"),
        language_code=language_code,
    )
    results_by_key = {
        result["key"]: result
        for result in localised_results
        if result.get("completed")
    }

    groups = []
    for localized in results_by_key.values():
        interpretation = str(localized.get("interpretation") or "").strip()
        if not interpretation:
            continue
        groups.append(
            {
                "title": localized.get("title") or localized["key"],
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
        if language_code == "sv":
            text = FACTOR_CONTENT.get(key, {}).get("top_text", "")
            if not text:
                text = MOTIVATION_DEFINITIONS.get(key, "")
        else:
            text = MOTIVATION_DEFINITIONS.get(key, "")
        text = str(text or "").strip()
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
        "personality_library_version": CANDIDATE_PERSONALITY_CONTENT_SV.get(
            "library_version", ""
        ),
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


def generate_candidate_result_content(
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
        "personality_library_version": content.get("personality_library_version", ""),
        "locale": normalize_ai_language(language_code),
    }
    return content, library_metadata, source_fingerprint


def ensure_candidate_result_snapshot_current(
    snapshot: CandidateResultSnapshot | None,
) -> tuple[CandidateResultSnapshot | None, bool]:
    """Replace a legacy AI snapshot once while preserving its archived copy."""
    if snapshot is None:
        return None, False
    if snapshot.content_version == CANDIDATE_RESULT_CONTENT_VERSION:
        return snapshot, False

    content, _library_metadata, fingerprint = generate_candidate_result_content(
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

    content, _library_metadata, source_fingerprint = generate_candidate_result_content(
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
