from __future__ import annotations

from functools import wraps
from typing import Any

from .motivation_interpretation import MOTIVATION_DEFINITIONS
from .shared_context import build_shared_ai_context


_INSTALLED = False


def _normalise_name(value: Any) -> str:
    return str(value or "").strip().casefold()


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


def _motivation_precision_instruction(
    owner,
    motivation_results: list[dict[str, Any]],
) -> str:
    shared = build_shared_ai_context(owner)
    purpose = str(shared.get("purpose_label") or "").strip()
    context = str(shared.get("context_text") or "").strip()
    snapshot = _motivation_snapshot(motivation_results)

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
- Example: Autonomy concerns freedom to organise one's own time and approach.
  In a highly structured role, explore how the person experiences and uses the
  discretion that actually exists within clear routines rather than inventing
  broad independence that the role context does not support.
- Example: Recognition concerns visibility, praise and acknowledgement. Make
  the question about the effect of relevant feedback or acknowledgement in the
  work context rather than generic status-seeking.

ROLE-CONTEXT PRECISION

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

If any answer is missing, rewrite the item before returning it.
"""


def install_motivation_question_precision_policy() -> None:
    """Apply final factor-definition and role-context precision to motivation questions."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import motivation_questions

    original_prompt = motivation_questions.build_motivation_questions_prompt

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
        )

    motivation_questions.build_motivation_questions_prompt = motivation_prompt

    _INSTALLED = True
