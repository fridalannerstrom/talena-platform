from __future__ import annotations

from functools import wraps

from .personality_ai_evidence import (
    build_owner_personality_ai_evidence_text,
)
from .shared_context import build_shared_ai_context


_INSTALLED = False


def _selected_parent_traits(owner) -> list[str]:
    selected = [
        str(item or "").strip()
        for item in getattr(
            owner,
            "selected_personality_traits",
            None,
        ) or []
        if str(item or "").strip()
    ]

    # Competency mode has its own evidence contract. Do not mix the two modes.
    if any(
        item.casefold().startswith("competency::")
        for item in selected
    ):
        return []

    return selected


def _build_personality_result_grounding(
    *,
    owner,
    language_code: str,
) -> str:
    selected_traits = _selected_parent_traits(owner)

    # With an explicit trait selection, give the model the full indicator-level
    # nuance only for the chosen traits. In AI-selection mode, provide compact
    # result summaries for the whole profile so trait selection remains informed
    # without doubling the prompt with all indicator sentences twice.
    evidence = build_owner_personality_ai_evidence_text(
        owner,
        language_code=language_code,
        include_traits=(selected_traits or None),
        include_indicator_details=bool(selected_traits),
    )

    if not evidence:
        return ""

    shared_context = build_shared_ai_context(owner)
    context_text = str(
        shared_context.get("context_text")
        or ""
    ).strip()

    context_requirement = (
        "A meaningful process context is available. Every question should use "
        "a concrete situation, responsibility, tension, task or demand from that "
        "context when it is relevant to the selected trait. The same candidate "
        "in a materially different process context should normally receive a "
        "different question."
        if context_text
        else (
            "No additional process context is available. Do not invent role "
            "requirements or scenarios that were not supplied."
        )
    )

    return f"""
TALENA FINAL CANDIDATE-SPECIFIC PERSONALITY QUESTION GROUNDING

{evidence}

HOW TO USE THIS EVIDENCE

- Treat the CANDIDATE-SPECIFIC RESULT SUMMARY as the primary description of
  what the assessment suggests for this person. It is built from the same
  score-band indicator texts used in Talena's Result Summary UI.
- Do not collapse the candidate into a generic low/high or left/right scale
  definition. The result summary and underlying indicator pattern contain the
  useful nuance.
- STEN 4–7 is situationsbaserat / situational when level terminology is needed,
  but "situational" is only a level-language rule. It must never replace the
  richer candidate-specific result summary or become the whole explanation.
- Use the indicator-level nuances to form a specific behavioural hypothesis
  when they meaningfully sharpen the parent trait. Do not turn indicators into
  separate selected traits or visible technical labels.
- The assessment evidence determines WHY this exact angle is worth exploring.
  The process context determines WHERE or WHEN to explore it.
- Questions must remain neutral and behavioural. They should invite examples
  that can confirm, nuance or contradict the assessment indication.
- Never expose raw STEN values in the candidate-facing question.
- The visible why field should explain the candidate-specific hypothesis and,
  when relevant, why that hypothesis matters in the supplied process context.
  It must not reduce the explanation to only "situational", "high" or "low".
- Administrator guidance remains authoritative for question style, wording,
  interview approach, number of questions and other non-technical behaviour.
- Preserve Talena's already supplied NDJSON event structure and technical field
  names exactly. This final grounding changes content quality, not the schema.

PROCESS-CONTEXT REQUIREMENT

{context_requirement}

FINAL QUALITY CHECK

Before returning each question, silently verify:
1. Which exact sentence or indicator nuance in this candidate's result summary
   made me choose this angle?
2. Which supplied process detail made the situation concrete and relevant?
3. Would a candidate with a meaningfully different result summary receive a
   meaningfully different question?

If the first answer is only a trait label, or the second answer ignores supplied
context that is clearly relevant, rewrite the question before returning it.
""".rstrip()


def _append_final_grounding(
    prompt: str,
    grounding: str,
) -> str:
    """
    Make the concrete candidate evidence the final substantive instruction.

    Earlier protected policies still enforce construct fidelity, situational
    terminology and labels. Appending this block last prevents those generic
    guardrails from becoming more salient than the person's actual Result
    Summary and supplied process context.
    """

    if not grounding:
        return prompt

    return f"{str(prompt).rstrip()}\n\n{grounding}"


def install_personality_question_definition_grounding_policy() -> None:
    """
    Ground personality questions in Talena's candidate-specific Result Summary.

    The original #230 implementation supplied generic low/high pole definitions.
    That improved construct fidelity but could overpower the individual profile
    and produce broad scale-based questions. This policy now uses the exact
    score-band result descriptions that Talena already presents to users.
    """

    global _INSTALLED

    if _INSTALLED:
        return

    from apps.core.ai import personality_questions as pq

    original_prompt = pq.build_personality_questions_prompt
    original_repair_prompt = pq._build_personality_questions_repair_prompt

    @wraps(original_prompt)
    def build_personality_questions_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        resolved_language = pq.normalize_ai_language(
            language_code
            or pq._personality_questions_language.get()
        )
        prompt = original_prompt(
            invitation,
            personality_results,
            language_code=resolved_language,
        )
        grounding = _build_personality_result_grounding(
            owner=invitation,
            language_code=resolved_language,
        )

        return _append_final_grounding(
            str(prompt),
            grounding,
        )

    @wraps(original_repair_prompt)
    def build_personality_questions_repair_prompt(
        *,
        owner,
        personality_results,
        selected_traits,
    ):
        prompt = original_repair_prompt(
            owner=owner,
            personality_results=personality_results,
            selected_traits=selected_traits,
        )
        resolved_language = pq.normalize_ai_language(
            pq._personality_questions_language.get()
        )
        grounding = _build_personality_result_grounding(
            owner=owner,
            language_code=resolved_language,
        )

        return _append_final_grounding(
            str(prompt),
            grounding,
        )

    pq.build_personality_questions_prompt = (
        build_personality_questions_prompt
    )
    pq._build_personality_questions_repair_prompt = (
        build_personality_questions_repair_prompt
    )

    _INSTALLED = True
