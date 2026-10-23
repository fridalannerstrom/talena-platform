from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.core.ai.cognitive_interpretation import extract_cognitive_results
from apps.core.ai.motivation_interpretation import extract_motivation_results
from apps.core.ai.personality_ai_evidence import (
    build_owner_personality_ai_evidence_text,
)

from apps.core.ai.language import (
    get_ai_language_instruction,
    get_ai_system_language_instruction,
    normalize_ai_language,
)
from apps.core.ai.openai_client import (
    get_chat_model,
    get_openai_client,
)
from apps.core.ai.prompt_templates import (
    get_ai_feature_prompt_instructions,
    get_default_ai_prompt,
    get_global_ai_guidance,
)
from apps.processes.models import AIPromptTemplate

from .models import CandidateResultSnapshot


CANDIDATE_RESULT_PROMPT_KEYS = {
    "introduction": "candidate_result_introduction",
    "personality": "candidate_result_personality",
    "skills": "candidate_result_skills",
    "motivation": "candidate_result_motivation",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (AttributeError, TypeError, ValueError):
            pass
    return value


def _process_context(invitation) -> str:
    try:
        role_context = invitation.process.role_context
        return (role_context.get_current_context_text() or "").strip()
    except Exception:
        return ""


def _has_result_value(competency: dict[str, Any]) -> bool:
    return any(
        competency.get(field_name) is not None
        for field_name in (
            "score",
            "stive",
            "stive_rounded",
            "sten",
            "sten_rounded",
            "percentile",
        )
    )


def _personality_evidence(invitation, *, language_code: str) -> str:
    try:
        return build_owner_personality_ai_evidence_text(
            invitation,
            language_code=language_code,
            include_indicator_details=True,
        )
    except (AttributeError, TypeError, ValueError, KeyError):
        return ""


def _candidate_result_areas(
    invitation,
    *,
    language_code: str,
) -> dict[str, dict[str, Any]]:
    """Identify only the assessment areas supported by real evidence."""
    personality_evidence = _personality_evidence(
        invitation,
        language_code=language_code,
    )
    motivation_results = extract_motivation_results(invitation)
    cognitive_results = extract_cognitive_results(invitation)

    has_personality_evidence = bool(personality_evidence)
    if not has_personality_evidence:
        for activity in invitation.sova_activities or []:
            activity_name = str(activity.get("activity") or "").lower()
            if not any(
                keyword in activity_name
                for keyword in (
                    "personality",
                    "personlighet",
                    "trait",
                    "karaktär",
                )
            ):
                continue
            if any(
                _has_result_value(competency)
                for competency in activity.get("competencies") or []
                if isinstance(competency, dict)
            ):
                has_personality_evidence = True
                break

    has_skills_evidence = bool(cognitive_results)
    if not has_skills_evidence:
        for activity in invitation.sova_activities or []:
            activity_name = str(activity.get("activity") or "").lower()
            if not any(
                keyword in activity_name
                for keyword in (
                    "skill",
                    "färdighet",
                    "numer",
                    "logical",
                    "logisk",
                    "verbal",
                    "reasoning",
                    "förmåga",
                )
            ):
                continue
            if any(
                _has_result_value(competency)
                for competency in activity.get("competencies") or []
                if isinstance(competency, dict)
            ):
                has_skills_evidence = True
                break

    customer_personality = (
        invitation.ai_personality_interpretation or {}
    )
    customer_motivation = (
        invitation.ai_motivation_interpretation or {}
    )
    customer_cognitive = (
        invitation.ai_cognitive_interpretation or {}
    )

    return {
        "personality": {
            "available": has_personality_evidence,
            "evidence": personality_evidence,
        },
        "skills": {
            "available": has_skills_evidence,
            "evidence": {
                "cognitive_results": _json_safe(cognitive_results),
            },
        },
        "motivation": {
            "available": bool(motivation_results),
            "evidence": {
                "motivation_results": _json_safe(motivation_results),
            },
        },
    }


def build_candidate_result_source(
    invitation,
    *,
    language_code: str = "sv",
) -> dict[str, Any]:
    """Build one canonical source and mark unavailable areas explicitly."""
    areas = _candidate_result_areas(
        invitation,
        language_code=language_code,
    )

    customer_evidence = {
        "summary": invitation.ai_summary or "",
        "personality": (
            _json_safe(invitation.ai_personality_interpretation or {})
            if areas["personality"]["available"]
            else {}
        ),
        "motivation": (
            _json_safe(invitation.ai_motivation_interpretation or {})
            if areas["motivation"]["available"]
            else {}
        ),
        "cognitive": (
            _json_safe(invitation.ai_cognitive_interpretation or {})
            if areas["skills"]["available"]
            else {}
        ),
    }

    return {
        "candidate": {"reference": "CANDIDATE_A"},
        "process": {
            "purpose": invitation.process.purpose or "",
            "job_title": invitation.process.job_title or "",
            "context": _process_context(invitation),
        },
        "available_result_areas": {
            area: {
                "available": details["available"],
                "evidence": details["evidence"],
            }
            for area, details in areas.items()
        },
        "personality_result_evidence": areas["personality"]["evidence"],
        "customer_result_evidence": customer_evidence,
    }


def _prompt_metadata(*, key: str, language_code: str) -> dict[str, Any]:
    language_code = normalize_ai_language(language_code)
    default_prompt = get_default_ai_prompt(key=key, language=language_code)
    override = (
        AIPromptTemplate.objects.filter(
            key=key,
            language=language_code,
            is_active=True,
        ).first()
    )
    effective_prompt = (
        override.prompt_text.strip()
        if override and override.prompt_text
        else default_prompt
    )
    latest_version = (
        override.versions.order_by("-saved_at", "-id").first()
        if override
        else None
    )
    metadata = {
        "key": key,
        "language": language_code,
        "source": "override" if override else "default",
        "prompt_hash": hashlib.sha256(
            effective_prompt.encode("utf-8")
        ).hexdigest(),
    }
    if override:
        metadata["template_id"] = override.pk
        metadata["updated_at"] = override.updated_at.isoformat()
    if latest_version:
        metadata["version_id"] = latest_version.pk
        metadata["version_saved_at"] = latest_version.saved_at.isoformat()
    return metadata


def get_candidate_result_prompt_metadata(
    *, language_code: str,
) -> dict[str, dict[str, Any]]:
    language_code = normalize_ai_language(language_code)
    return {
        section: _prompt_metadata(key=key, language_code=language_code)
        for section, key in CANDIDATE_RESULT_PROMPT_KEYS.items()
    }


def build_candidate_result_prompt(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[str, dict[str, dict[str, Any]]]:
    """Build one candidate-result prompt from one canonical source."""
    language_code = normalize_ai_language(language_code)
    source = build_candidate_result_source(
        invitation,
        language_code=language_code,
    )
    available_areas = source["available_result_areas"]
    available_area_lines = "\n".join(
        f"- {section}: {'AVAILABLE' if details['available'] else 'NOT AVAILABLE'}"
        for section, details in available_areas.items()
    )
    prompt_metadata = get_candidate_result_prompt_metadata(
        language_code=language_code
    )
    feature_guidance = {
        section: get_ai_feature_prompt_instructions(
            key=key,
            language=language_code,
        )
        for section, key in CANDIDATE_RESULT_PROMPT_KEYS.items()
    }
    source_json = json.dumps(source, ensure_ascii=False, indent=2, default=str)

    prompt = f"""
TALENA CANDIDATE RESULT GENERATION

Create a supportive candidate-facing result from the supplied canonical
assessment source.

The available_result_areas and customer_result_evidence contain selected
assessment evidence and earlier customer-facing interpretations. Preserve
their substantive meaning. You may simplify, shorten and phrase the result
more warmly, but never reverse, exaggerate or contradict the interpretation.
Do not infer or request full Sova activities, projects, report objects or URLs.

PROTECTED RULES

- Write for the candidate, not for a recruiter or administrator.
- Use positive, respectful and non-judgemental language.
- Do not use good/bad, strong/weak, pass/fail, suitable/unsuitable or hiring
  language.
- Do not expose raw scores, STEN values, percentiles, internal codes,
  recommendations or private process notes.
- Treat assessment results as indications or hypotheses, never absolute truths.
- Do not diagnose the candidate or introduce unsupported psychological claims.
- Skills/färdighet must remain descriptive. Do not turn skills into personality,
  motivation or guaranteed job performance.
- Do not frame lower skills results as deficits, weaknesses or personal
  shortcomings. Avoid telling the candidate that they need to develop,
  improve or train a skill. Where supported by the evidence, describe instead
  that certain task types may require more time, focus or support.
- If evidence is missing, say less rather than inventing content.
- Address the candidate without using any personal name.
- Return valid JSON only, with exactly the four top-level keys shown below.

OUTPUT LANGUAGE

{get_ai_language_instruction(language_code)}

GLOBAL ADMINISTRATOR GUIDANCE

{get_global_ai_guidance(language=language_code)}

AVAILABLE RESULT AREAS

{available_area_lines}

Only write substantive content for areas marked AVAILABLE. For every area
marked NOT AVAILABLE, return an empty body and an empty points array. Never
infer that a test was taken from the process name, job title or another
assessment area.

SECTION PROMPTS

INTRODUCTION
{feature_guidance['introduction']}

PERSONALITY
{feature_guidance['personality']}

SKILLS / FÄRDIGHET
{feature_guidance['skills']}

MOTIVATION
{feature_guidance['motivation']}

CANONICAL SOURCE

{source_json}

JSON STRUCTURE

{{
  "introduction": {{
    "title": "A welcoming result title",
    "body": "A short, reassuring introduction to the result."
  }},
  "personality": {{
    "title": "Personality",
    "body": "A concise, nuanced candidate-facing interpretation.",
    "points": ["Optional practical points"]
  }},
  "skills": {{
    "title": "Skills",
    "body": "A strictly descriptive interpretation of available skills results.",
    "points": ["Optional practical points"]
  }},
  "motivation": {{
    "title": "Motivation",
    "body": "A concise, supportive interpretation of available motivation results.",
    "points": ["Optional practical points"]
  }}
}}
""".strip()
    return prompt, prompt_metadata


def _parse_json_content(raw_content: str) -> dict[str, Any]:
    text = (raw_content or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Candidate result generation did not return valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Candidate result generation must return a JSON object.")
    return payload


def _normalise_section(
    value: Any,
    fallback_title: str,
    *,
    available: bool = True,
) -> dict[str, Any]:
    if isinstance(value, dict):
        title = str(value.get("title") or fallback_title).strip()
        body = str(value.get("body") or "").strip()
        points = value.get("points") or []
    else:
        title = fallback_title
        body = str(value or "").strip()
        points = []

    if not available:
        body = ""
        points = []
    if not isinstance(points, list):
        points = [points]
    return {
        "title": title,
        "body": body,
        "points": [str(point).strip() for point in points if str(point).strip()],
    }


def normalise_candidate_result_content(
    payload: dict[str, Any],
    *,
    available_areas: dict[str, dict[str, Any]] | None = None,
    language_code: str = "sv",
) -> dict[str, dict[str, Any]]:
    available_areas = available_areas or {
        "personality": {"available": True},
        "skills": {"available": True},
        "motivation": {"available": True},
    }
    titles = {
        "sv": {
            "introduction": "Ditt resultat",
            "personality": "Personlighet",
            "skills": "Färdigheter",
            "motivation": "Motivation",
        },
        "en": {
            "introduction": "Your result",
            "personality": "Personality",
            "skills": "Skills",
            "motivation": "Motivation",
        },
    }.get(language_code, {})
    return {
        "introduction": _normalise_section(
            payload.get("introduction"),
            titles.get("introduction", "Your result"),
        ),
        "personality": _normalise_section(
            payload.get("personality"),
            titles.get("personality", "Personality"),
            available=available_areas.get("personality", {}).get(
                "available",
                False,
            ),
        ),
        "skills": _normalise_section(
            payload.get("skills"),
            titles.get("skills", "Skills"),
            available=available_areas.get("skills", {}).get(
                "available",
                False,
            ),
        ),
        "motivation": _normalise_section(
            payload.get("motivation"),
            titles.get("motivation", "Motivation"),
            available=available_areas.get("motivation", {}).get(
                "available",
                False,
            ),
        ),
    }


def generate_candidate_result_content(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], str]:
    """Generate candidate-facing content without mutating the invitation."""
    language_code = normalize_ai_language(language_code)
    source = build_candidate_result_source(
        invitation,
        language_code=language_code,
    )
    prompt, prompt_metadata = build_candidate_result_prompt(
        invitation,
        language_code=language_code,
    )
    from apps.core.ai.candidate_name_privacy import redact_candidate_name

    client = get_openai_client()
    prompt = redact_candidate_name(prompt, invitation.candidate)
    response = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Talena's candidate-result AI component. "
                    "Follow the protected candidate-result rules and the "
                    "administrator guidance. "
                    f"{get_ai_system_language_instruction(language_code)}"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = normalise_candidate_result_content(
        _parse_json_content(response.choices[0].message.content),
        available_areas=source["available_result_areas"],
        language_code=language_code,
    )
    fingerprint_payload = {
        "source": source,
        "prompt_versions": prompt_metadata,
        "locale": language_code,
    }
    source_fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return content, prompt_metadata, source_fingerprint


def create_candidate_result_snapshot(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[CandidateResultSnapshot, bool]:
    """Generate and persist one immutable candidate result snapshot."""
    if not invitation.process.candidate_results_enabled:
        raise ValueError("Candidate results are not enabled for this process.")
    if invitation.status != "completed":
        raise ValueError("Candidate result snapshots require a completed invitation.")

    existing = CandidateResultSnapshot.objects.filter(invitation=invitation).first()
    if existing:
        return existing, False
    content, prompt_metadata, source_fingerprint = generate_candidate_result_content(
        invitation,
        language_code=language_code,
    )
    snapshot = CandidateResultSnapshot.objects.create(
        invitation=invitation,
        candidate=invitation.candidate,
        process=invitation.process,
        locale=normalize_ai_language(language_code),
        content=content,
        prompt_versions=prompt_metadata,
        source_fingerprint=source_fingerprint,
    )
    return snapshot, True
