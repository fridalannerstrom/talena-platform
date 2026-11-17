from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from django.db import transaction

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

from .audit import log_candidate_result_event
from .models import CandidateResultSnapshot


CANDIDATE_RESULT_CONTENT_VERSION = "candidate-static-v6-513"
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
            "Testresultaten är ett underlag för att skapa en bättre förståelse för "
            "vilka beteenden och arbetssätt som kan komma mer naturligt för dig, "
            "vad som motiverar dig och hur du tar dig an olika typer av uppgifter."
        ),
        "norm_before": "Dina resultat jämförs med en ",
        "norm_emphasis": "normgrupp",
        "norm_after": ", det vill säga en grupp personer som tidigare har genomfört samma test.",
        "caveat_emphasis": "Ett testresultat är en början, inte hela bilden.",
        "caveat_after": (
            " Resultaten ska inte ses som absoluta sanningar eller som en bedömning av "
            "vad du är bra eller mindre bra på. Hur dina egenskaper kommer till uttryck "
            "påverkas också av dina erfarenheter, sammanhanget och situationen."
        ),
        "comment_candidate": (
            "Om du vill kan du lämna en kommentar till ditt resultat, exempelvis för att "
            "förtydliga något, ge ett konkret exempel eller beskriva en situation där du "
            "inte riktigt känner igen dig. Dina kommentarer blir då en del av underlaget "
            "och hjälper den som tar del av rapporten att förstå resultatet i sitt sammanhang."
        ),
        "comment_preview": (
            "När rapporten delas med kandidaten och hen har verifierat sin åtkomst kan "
            "kandidaten lämna en kommentar till sitt resultat. Kommentarerna blir då en del "
            "av underlaget. Den här interna förhandsvisningen har ingen kommentarsfunktion."
        ),
        "section_introductions": {
            "personality": "Personlighetsformuläret beskriver dina typiska beteenden, preferenser och sätt att förhålla dig till olika situationer.",
            "motivation": "Motivationsformuläret beskriver vad som tenderar att ge dig engagemang i arbetet, och vad som kan vara mindre motiverande.",
            "skills": "Färdighetstestet ger en indikation på hur snabbt och korrekt du hanterar olika typer av uppgifter, exempelvis logisk, numerisk eller verbal problemlösning.",
        },
        "personality_title": "Personlighet",
        "skills_title": "Färdigheter",
        "motivation_title": "Motivation",
        "top_motivators_title": CANDIDATE_RESULT_SECTION_COPY["sv"]["title"],
    },
    "en": {
        "introduction_title": "Your results",
        "introduction_body": (
            "Assessment results provide a starting point for understanding the behaviours "
            "and working styles that may come more naturally to you, what motivates you, "
            "and how you approach different tasks."
        ),
        "norm_before": "Your results are compared with a ",
        "norm_emphasis": "norm group",
        "norm_after": ", a group of people who have previously completed the same assessment.",
        "caveat_emphasis": "An assessment result is a starting point, not the whole picture.",
        "caveat_after": (
            " The results are not absolute truths or a judgment of what you are good or "
            "less good at. How your characteristics appear also depends on your experiences, "
            "the context and the situation."
        ),
        "comment_candidate": (
            "If you wish, you can leave a comment on your results to clarify something, "
            "share an example or describe a situation where you do not fully recognise "
            "yourself. Your comments then become part of the information used to "
            "understand the results in context."
        ),
        "comment_preview": (
            "When the report is shared and the candidate has verified access, they can "
            "leave comments on their results. Comments then become part of the report "
            "context. This internal preview does not allow comments."
        ),
        "section_introductions": {
            "personality": "The personality questionnaire describes your typical behaviours, preferences and ways of approaching different situations.",
            "motivation": "The motivation questionnaire describes what tends to engage you at work and what may be less motivating.",
            "skills": "The ability assessment indicates how quickly and accurately you handle different types of tasks, such as logical, numerical or verbal reasoning.",
        },
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


# Ticket #513: exact and complete 18-trait mapping to the ten candidate-
# facing subheadings. These are presentation groupings, never SOVA score edits.
# The original order of traits inside each grouping is intentional.
CANDIDATE_PERSONALITY_TOPICS = {
    "leading_and_working_with_others": (
        (("Cooperative", "Connecting"), "Samarbete och relationer", "Collaboration and relationships"),
        (("Empathy", "Supporting"), "Hjälpsamhet och finnas där för andra", "Helping and supporting others"),
        (("Dynamic", "Influential"), "Påverka andra och komma framåt", "Influencing others and moving forward"),
    ),
    "organisation_and_thinking_style": (
        (("Goal-focused", "Structured"), "Planering och målfokus", "Planning and goal focus"),
        (("Analytical", "Complex Thinking"), "Analys och strategi", "Analysis and strategy"),
        (("Creativity", "Adaptability"), "Förändring och nytänkande", "Change and new ideas"),
    ),
    "interacting_and_managing_emotions": (
        (("Straightforward",), "Kommunikationsstil och principfasthet", "Communication style and principles"),
        (("Status Avoidance", "Modesty"), "Att synas eller smälta in", "Standing out or blending in"),
        (("Resilience", "Emotional Control"), "Stress och press", "Stress and pressure"),
        (("Independence",), "Självständigt arbete och förankring", "Independent work and alignment"),
    ),
}

# Catch accidental drift if the assessment schema changes: never silently
# drop or double count an indicator under a new heading.
for _section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
    _actual = [trait["trait_name"] for trait in _section["traits"]]
    _mapped = [
        name for group in CANDIDATE_PERSONALITY_TOPICS[_section["section_key"]]
        for name in group[0]
    ]
    if sorted(_actual) != sorted(_mapped):
        raise ValueError("Candidate personality topic mapping must cover each trait exactly once")


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
        trait_definitions = {
            trait["trait_name"]: trait for trait in section["traits"]
        }
        topics = []
        for trait_keys, title_sv, title_en in CANDIDATE_PERSONALITY_TOPICS[section["section_key"]]:
            sentences = []
            for trait_key in trait_keys:
                trait_definition = trait_definitions[trait_key]
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
                        text = (
                            indicator_definitions.get(indicator_key, {})
                            .get("score_texts", {})
                            .get(score_band, "")
                        )
                    else:
                        text = (
                            _CANDIDATE_PERSONALITY_TEXTS_EN
                            .get(indicator_key, {})
                            .get(score_band, "")
                        )
                    if text and text.strip():
                        sentences.append(text.strip())

            if sentences:
                topics.append({
                    "label": title_sv if language_code == "sv" else title_en,
                    "text": " ".join(sentences),
                })

        if topics:
            groups.append({
                "title": (
                    section_titles[language_code].get(section["section_key"])
                    or section["section_name"]
                ),
                "body": "",
                "items": topics,
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
            "norm_before": copy["norm_before"],
            "norm_emphasis": copy["norm_emphasis"],
            "norm_after": copy["norm_after"],
            "caveat_emphasis": copy["caveat_emphasis"],
            "caveat_after": copy["caveat_after"],
            "comment_candidate": copy["comment_candidate"],
            "comment_preview": copy["comment_preview"],
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
    for section_key in ("personality", "motivation", "skills"):
        if content.get(section_key) is not None:
            content[section_key]["introduction"] = copy["section_introductions"][section_key]
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
    actor=None,
) -> tuple[CandidateResultSnapshot, bool]:
    """Create a static snapshot, or safely upgrade an earlier AI snapshot."""
    # The static report is also used internally when candidate sharing is off.
    # Public access and outgoing emails are guarded separately by the sharing
    # toggle; creating this snapshot issues no credentials or notification.
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
    with transaction.atomic():
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
        from apps.activity.models import ActivityEvent

        log_candidate_result_event(
            invitation,
            verb=ActivityEvent.Verb.CANDIDATE_RESULT_SNAPSHOT_CREATED,
            actor=actor,
            meta={"content_version": CANDIDATE_RESULT_CONTENT_VERSION},
        )
    return snapshot, True
