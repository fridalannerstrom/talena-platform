from __future__ import annotations

import re
from functools import wraps
from typing import Any

from .motivation_interpretation import MOTIVATION_DEFINITIONS
from .shared_context import build_shared_ai_context


_INSTALLED = False


SWEDISH_FACTOR_LABELS = {
    "affiliation": "Samhörighet",
    "attachment": "Samhörighet",
    "customer service": "Kundservice",
    "work life balance": "Balans mellan arbete och fritid",
    "people development": "Utveckla andra",
    "stability": "Stabilitet",
    "authority": "Auktoritet",
    "acquisition": "Ekonomisk belöning",
    "autonomy": "Självständighet",
    "independence": "Självständighet",
    "recognition": "Erkännande",
    "making a difference": "Göra skillnad",
    "achievement": "Prestation",
    "quality": "Kvalitet",
    "learning": "Lärande",
    "ethics": "Etik",
    "commercial value": "Kommersiellt värde",
    "commercial focus": "Kommersiellt värde",
    "curiosity": "Nyfikenhet",
    "creativity": "Kreativitet",
    "enjoyment": "Arbetsglädje",
    "variety": "Variation",
    "risk": "Risktagande",
}


def _normalise_name(value: Any) -> str:
    text = str(value or "").strip().casefold()
    return " ".join(text.replace("_", " ").replace("-", " ").split())


def _factor_importance(score: Any) -> str:
    try:
        value = int(round(float(score)))
    except (TypeError, ValueError):
        return "unknown motivational importance"

    if value >= 4:
        return "more prominent motivational driver"
    if value <= 2:
        return "less central motivational driver"
    return "mid-range motivational importance"


def _motivation_snapshot(results: list[dict[str, Any]]) -> str:
    rows: list[str] = []

    for item in results or []:
        name = str(item.get("name") or "").strip()
        if not name or item.get("score") is None:
            continue

        definition = str(item.get("definition") or "").strip()
        if not definition:
            definition = MOTIVATION_DEFINITIONS.get(_normalise_name(name), "")

        rows.append(
            f"- {name}: {_factor_importance(item.get('score'))}"
            + (f" | Meaning: {definition}" if definition else "")
        )

    return "\n".join(rows) if rows else "No usable motivation evidence supplied."


def _swedish_user_facing_instruction(
    motivation_results: list[dict[str, Any]],
    language_code: str,
) -> str:
    if not str(language_code or "").lower().startswith("sv"):
        return ""

    label_rows: list[str] = []
    seen: set[str] = set()

    for item in motivation_results or []:
        source_name = str(item.get("name") or "").strip()
        if not source_name:
            continue

        label = SWEDISH_FACTOR_LABELS.get(_normalise_name(source_name))
        if not label or label in seen:
            continue

        seen.add(label)
        label_rows.append(f"- {source_name} -> {label}")

    mappings = "\n".join(label_rows) or (
        "- Use the established Swedish Talena motivation terminology."
    )

    return f"""

SWEDISH USER-FACING MOTIVATION LANGUAGE

The configured output language is Swedish.

- User-facing question, why and listen_for text must use natural Swedish
  motivation terminology. Do not expose English source labels such as
  Affiliation, Recognition, Autonomy or Achievement when a Swedish Talena
  label is available.
- Use the established Swedish factor name naturally in prose, with lower-case
  wording where grammatically appropriate. Do not make the sentence sound like
  a database field or assessment export.
- Prefer natural descriptions of motivational importance:
  * prominent -> "är en mer framträdande drivkraft" or equivalent natural prose
  * mid-range -> "har måttlig betydelse för motivationen" or equivalent
  * less central -> "är en mindre central källa till motivation" or equivalent
- Avoid mechanical phrases such as "måttligt viktig faktor", "medelstor
  motivation", "faktorn Recognition" or repeated score-report language.
- The visible why should read like useful interview guidance, not like a direct
  translation of an assessment data row.

SWEDISH FACTOR LABELS FOR THE SUPPLIED PROFILE
{mappings}
"""


def _normalise_swedish_user_facing_text(value: Any) -> str:
    """Guarantee Talena's Swedish factor terminology in generated question copy."""

    text = str(value or "").strip()
    if not text:
        return text

    source_labels = {
        "Affiliation": "Samhörighet",
        "Attachment": "Samhörighet",
        "Customer Service": "Kundservice",
        "Work-Life Balance": "Balans mellan arbete och fritid",
        "People Development": "Utveckla andra",
        "Stability": "Stabilitet",
        "Authority": "Auktoritet",
        "Acquisition": "Ekonomisk belöning",
        "Autonomy": "Självständighet",
        "Independence": "Självständighet",
        "Recognition": "Erkännande",
        "Making a Difference": "Göra skillnad",
        "Achievement": "Prestation",
        "Quality": "Kvalitet",
        "Learning": "Lärande",
        "Ethics": "Etik",
        "Commercial Value": "Kommersiellt värde",
        "Commercial Focus": "Kommersiellt värde",
        "Curiosity": "Nyfikenhet",
        "Creativity": "Kreativitet",
        "Enjoyment": "Arbetsglädje",
        "Variety": "Variation",
        "Risk": "Risktagande",
    }

    for source, target in sorted(
        source_labels.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = re.sub(
            rf"(?<![\wÅÄÖåäö]){re.escape(source)}(?![\wÅÄÖåäö])",
            target,
            text,
            flags=re.IGNORECASE,
        )

    text = re.sub(
        r"\bden\s+måttligt\s+viktiga\s+faktorn\s+"
        r"([A-ZÅÄÖ][A-Za-zÅÄÖåäö\s-]*?)(?=,|\.|\s+och\b)",
        r"\1, som har måttlig betydelse för motivationen",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bfaktorn\s+([A-ZÅÄÖ][A-Za-zÅÄÖåäö\s-]*?),\s+som\s+är\s+av\s+måttlig\s+vikt\b",
        r"\1, som har måttlig betydelse för motivationen",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bden\s+medelstora\s+motivationen\s+kopplad\s+till\s+"
        r"([A-ZÅÄÖ][A-Za-zÅÄÖåäö\s-]*?)(?=,|\.)",
        r"\1 har måttlig betydelse för motivationen",
        text,
        flags=re.IGNORECASE,
    )

    return " ".join(text.split())


def _normalise_swedish_questions_event(event: dict[str, Any]) -> dict[str, Any]:
    if str(event.get("type") or "").strip().lower() != "questions":
        return event

    normalised = dict(event)
    items: list[dict[str, Any]] = []

    for item in event.get("items") or []:
        if not isinstance(item, dict):
            items.append(item)
            continue

        updated = dict(item)
        for field in ("question", "why", "listen_for"):
            updated[field] = _normalise_swedish_user_facing_text(
                updated.get(field)
            )
        items.append(updated)

    normalised["items"] = items
    return normalised


def _motivation_precision_instruction(
    owner,
    motivation_results: list[dict[str, Any]],
    language_code: str = "en",
) -> str:
    shared = build_shared_ai_context(owner)
    purpose = str(shared.get("purpose_label") or "").strip()
    context = str(shared.get("context_text") or "").strip()
    snapshot = _motivation_snapshot(motivation_results)
    has_context = bool(shared.get("has_context"))
    swedish_language_rule = _swedish_user_facing_instruction(
        motivation_results,
        language_code,
    )

    context_anchor_rule = (
        """
MEANINGFUL PROCESS CONTEXT IS AVAILABLE.

This is a non-negotiable product requirement:
- At least two of three generated questions must explicitly use or clearly
  paraphrase a concrete situation, setting, responsibility or phrase from the
  supplied PROCESS CONTEXT.
- The remaining question must still be unmistakably plausible for the same
  process. A generic workplace question that could be reused unchanged for a
  very different job is invalid.
- Prefer the actual vocabulary supplied in the context over invented duties.
- The role/context must shape the scenario itself, not merely appear in the why
  field after a generic question has already been written.
"""
        if has_context
        else """
No meaningful process context is available. Keep scenarios broad and do not
invent role-specific details.
"""
    )

    return f"""

TALENA MOTIVATION QUESTION PRECISION STANDARD

This is the final protected quality check for motivation interview questions.
It is applied after administrator guidance, normal candidate grounding and the
candidate fingerprint standard.

PROCESS PURPOSE
{purpose or "No process purpose supplied."}

PROCESS CONTEXT
{context or "No additional process context supplied."}

MOTIVATION EVIDENCE SNAPSHOT
{snapshot}

FACTOR MEANING IS THE SOURCE OF TRUTH

- Use each factor's supplied Meaning/definition as the source of truth for the
  psychological construct being explored. The factor name is only a label.
- Do not turn the factor label into a literal interview scenario when that would
  sound unnatural in the supplied role context.
- Example: Risk means motivation connected to having scope to act despite
  uncertainty and take calculated risks. In a role where "taking risks" would
  sound unnatural or inappropriate, explore how the person responds when an
  unexpected or uncertain situation requires judgement, rather than asking them
  to describe taking risks for its own sake.
- HARD RULE FOR RISK: unless the supplied process context itself explicitly
  describes risk-taking, risk ownership, investment decisions or comparable
  discretion, do NOT ask the candidate to describe "taking a calculated risk",
  "taking risks", "kalkylerade risker", "ta risker" or equivalent wording.
  Translate the factor into a realistic question about uncertainty, incomplete
  information, judgement, unexpected events or acting without full certainty.
- Example: Autonomy concerns freedom to organise one's own time and approach.
  In a highly structured role, explore how the person experiences and uses the
  discretion that actually exists within clear routines rather than inventing
  broad independence that the role context does not support.
- Example: Recognition concerns visibility, praise and acknowledgement. Make
  the question about the effect of relevant feedback or acknowledgement in the
  work context rather than generic status-seeking.

ROLE-CONTEXT PRECISION

{context_anchor_rule}

- Every question must feel plausible for THIS process and the supplied role or
  process context. Motivation evidence determines WHAT is explored; context
  determines WHERE and HOW it is explored.
- When meaningful context exists, anchor the question in a realistic situation
  or demand from that context instead of asking a generic workplace question.
- Do not invent detailed duties, policies, tools or organisational facts that
  are not supported by the supplied context.
- If the context is sparse, use only broad situations safely implied by the
  supplied role description. Do not manufacture specificity.
- A question is too generic if it would read equally naturally for a completely
  different role after only changing the job title.

CANDIDATE-SPECIFIC MOTIVATION ANGLE

- A more prominent driver, a mid-range driver and a less-central driver must
  lead to meaningfully different hypotheses.
- Do not present a less-central driver as a weakness, lack of capability or
  inability to perform the corresponding behaviour.
- Do not make every visible why field sound like a score report. Vary the
  explanation naturally while keeping the candidate-specific motivation factor
  or factor pattern traceable.
- Use contrasts between factors when they create a more useful hypothesis, but
  do not force contrasts when a single factor gives the clearest question.

VISIBLE WHY FIELD REQUIREMENT

The why field must explain both sides of the selection:
1. which motivation factor or profile pattern made the question relevant for
   this candidate; and
2. why exploring that pattern is useful in the supplied process context.

The why field may describe a factor as more prominent, less central or
mid-range when useful, but it does not need to repeat that wording mechanically
for every question. Do not expose raw STIVE values.

A why that only explains why the topic matters for the role is too generic.
A why that only restates the motivation score without connecting it to the
process is also incomplete.

{swedish_language_rule}

FINAL SILENT CHECK FOR EACH QUESTION

Before returning each item, verify:
- Which exact motivation factor or factor pattern caused this question to be
  selected?
- Does the question reflect the supplied factor definition rather than merely
  literalising the factor name?
- What specific supplied process/role context shaped the scenario?
- Would this question still make sense if the candidate had the opposite
  motivation pattern? If yes, make the angle more candidate-specific.
- Would this question sound natural and credible to an interviewer in this
  process? If no, rewrite it using the factor meaning and supplied context.
- If this is a Risk question, does it violate the HARD RULE FOR RISK above? If
  yes, rewrite it before returning the response.

If any answer is missing, rewrite the item before returning it.
"""


def install_motivation_question_precision_policy() -> None:
    """Apply final factor-definition and role-context precision to motivation questions."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import motivation_questions

    original_prompt = motivation_questions.build_motivation_questions_prompt
    original_stream = motivation_questions.stream_motivation_questions

    @wraps(original_prompt)
    def motivation_prompt(
        *,
        owner,
        motivation_results,
        language_code="en",
    ):
        prompt = original_prompt(
            owner=owner,
            motivation_results=motivation_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _motivation_precision_instruction(
            owner,
            motivation_results,
            language_code=language_code,
        )

    @wraps(original_stream)
    def motivation_stream(
        *,
        owner,
        motivation_results,
        language_code="en",
    ):
        for event in original_stream(
            owner=owner,
            motivation_results=motivation_results,
            language_code=language_code,
        ):
            if str(language_code or "").lower().startswith("sv"):
                yield _normalise_swedish_questions_event(event)
            else:
                yield event

    motivation_questions.build_motivation_questions_prompt = motivation_prompt
    motivation_questions.stream_motivation_questions = motivation_stream

    _INSTALLED = True
