from __future__ import annotations

from functools import wraps
from typing import Any


_INSTALLED = False


def _normalise_name(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _sten_band(value: Any) -> str:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if score <= 3:
        return "low"
    if score >= 8:
        return "high"
    return "mid-range"


def _motivation_band(value: Any) -> str:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if score <= 2:
        return "less central"
    if score >= 4:
        return "prominent"
    return "mid-range"


def _cognitive_band(value: Any) -> str:
    try:
        percentile = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if percentile <= 9:
        return "very low relative to the reference group"
    if percentile <= 24:
        return "low relative to the reference group"
    if percentile <= 74:
        return "within the typical range"
    if percentile <= 90:
        return "high relative to the reference group"
    return "very high relative to the reference group"


def _personality_snapshot(owner, personality_results: list[dict[str, Any]]) -> str:
    result_lookup = {
        _normalise_name(item.get("name")): item
        for item in personality_results or []
        if _normalise_name(item.get("name"))
    }

    selected = [
        str(item or "").strip()
        for item in getattr(owner, "selected_personality_traits", None) or []
        if str(item or "").strip()
    ]

    competency_mode = any(
        item.casefold().startswith("competency::")
        for item in selected
    )

    if competency_mode:
        return (
            "Question basis: user-selected competencies.\n"
            "Use the SUPPORTING PERSONALITY EVIDENCE supplied under each "
            "competency in the original prompt as the candidate-specific "
            "profile evidence. When supporting rows exist, their actual "
            "direction and pattern must materially affect the question angle."
        )

    rows = []
    selected_keys = {
        _normalise_name(item)
        for item in selected
    }

    relevant_results = [
        item
        for key, item in result_lookup.items()
        if not selected_keys or key in selected_keys
    ]

    if not relevant_results:
        relevant_results = list(personality_results or [])

    for item in relevant_results:
        name = str(item.get("name") or "").strip()
        sten = item.get("sten")
        if not name or sten is None:
            continue
        rows.append(
            f"- {name}: STEN {sten} of 10 ({_sten_band(sten)})"
        )

    if not rows:
        return "No usable personality score snapshot is available."

    return "\n".join(rows)


def _personality_grounding_instruction(
    owner,
    personality_results: list[dict[str, Any]],
) -> str:
    snapshot = _personality_snapshot(owner, personality_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. The user's selection controls WHAT
area the interview should explore. The candidate's actual assessment profile
controls WHICH ANGLE the question takes.

CANDIDATE-SPECIFIC PROFILE SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be materially grounded in this candidate's supplied
  personality evidence, not only in the selected trait or competency label.
- Use the actual score direction, relative prominence and meaningful profile
  contrasts to decide what hypothesis or behaviour is worth exploring.
- Two candidates with the same popup selection but meaningfully different
  assessment results should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable if the
  candidate had the opposite result pattern. If it would, rewrite it so the
  candidate's actual profile changes the angle being explored.
- Keep the main question neutral and non-leading. Do not reveal STEN values or
  tell the candidate that the assessment proves a behaviour.
- Ask for concrete examples that can confirm, nuance or contradict the
  assessment indication.
- The why field must explain the candidate-specific reason for asking the
  question. It should connect the selected area to the actual profile pattern,
  without exposing raw scores unless administrator guidance explicitly allows
  that in interviewer-facing explanatory text.
- The listen_for field must describe evidence that would help the interviewer
  validate, qualify or challenge the specific hypothesis behind the question.
- Use process purpose and supplied context to make the situation relevant, but
  never let process context replace the candidate's assessment evidence as the
  basis for the question.
- In competency mode, supporting personality evidence is contextual evidence,
  not a competency score. Use it to choose the angle only. Never convert it
  into a measured competency level.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "What exact candidate result made me choose
this angle?" If there is no concrete answer in the supplied assessment data,
rewrite the question.
"""


def _motivation_snapshot(motivation_results: list[dict[str, Any]]) -> str:
    rows = []
    valid = []

    for item in motivation_results or []:
        name = str(item.get("name") or "").strip()
        score = item.get("score")
        if not name or score is None:
            continue
        valid.append((name, score))

    valid.sort(key=lambda item: (-float(item[1]), item[0].casefold()))

    for name, score in valid:
        rows.append(
            f"- {name}: STIVE {score} of 5 ({_motivation_band(score)})"
        )

    if not rows:
        return "No usable motivation score snapshot is available."

    return "\n".join(rows)


def _motivation_grounding_instruction(
    motivation_results: list[dict[str, Any]],
) -> str:
    snapshot = _motivation_snapshot(motivation_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. Motivation questions must be built
from the shape of this candidate's actual motivation profile, not from generic
motivation topics or process context alone.

CANDIDATE-SPECIFIC MOTIVATION SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be traceable to one or more actual motivation factors in
  the supplied candidate data.
- Let the candidate's relative pattern determine the angle: prominent drivers,
  less central drivers, mid-range factors and meaningful contrasts should lead
  to different questions.
- When the evidence permits, distribute the question set across distinct parts
  of the profile rather than asking several versions of the same high-level
  motivation question.
- Two candidates with the same process purpose but different motivation
  profiles should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable if the factor
  pattern were reversed. If it would, rewrite it.
- Do not reveal STIVE values or phrase the main question as "your test says".
  Ask neutrally for examples, preferences, conditions or trade-offs that can
  validate or nuance the assessment indication.
- A low or less-central motivation score is not low ability, poor performance
  or absence of the quality named by the factor.
- The why field must state the candidate-specific profile reason for asking the
  question, without making the assessment sound deterministic.
- The listen_for field must identify evidence that would confirm, nuance or
  challenge the specific motivation hypothesis being explored.
- Use purpose and supplied process context to make questions practical, but do
  not let that context replace the candidate's motivation results as the basis.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "Which exact motivation result or contrast
made me choose this angle?" If the answer is only the process purpose or a
common interview topic, rewrite the question.
"""


def _cognitive_snapshot(cognitive_results: list[dict[str, Any]]) -> str:
    rows = []

    for item in cognitive_results or []:
        label = str(
            item.get("label")
            or item.get("key")
            or ""
        ).strip()
        percentile = item.get("percentile")
        if not label or percentile is None:
            continue
        rows.append(
            f"- {label}: percentile {percentile} "
            f"({_cognitive_band(percentile)})"
        )

    if not rows:
        return "No usable cognitive score snapshot is available."

    return "\n".join(rows)


def _cognitive_grounding_instruction(
    cognitive_results: list[dict[str, Any]],
) -> str:
    snapshot = _cognitive_snapshot(cognitive_results)

    return f"""

TALENA CANDIDATE-SPECIFIC QUESTION GROUNDING

This is a protected product requirement. Cognitive follow-up questions must
be shaped by this candidate's actual completed reasoning results.

CANDIDATE-SPECIFIC COGNITIVE SNAPSHOT
{snapshot}

REQUIRED GROUNDING BEHAVIOUR

- Every question must be traceable to at least one completed cognitive result.
- The actual percentile position and the pattern across completed abilities
  must materially affect what is worth exploring.
- When several abilities are available, use meaningful differences or
  contrasts where useful instead of producing three interchangeable questions.
- Two candidates with the same process purpose but different cognitive result
  patterns should normally receive meaningfully different questions.
- Do not write a generic question that would be equally suitable for a very
  high and a very low result on the same ability. If it would, rewrite it.
- Do not reveal percentile values in the main question and do not frame lower
  results as personal deficits or higher results as guaranteed performance.
- Keep questions behavioural and practical. Explore examples, strategies,
  conditions, complexity, pace, checking approaches or support needs where
  these are genuinely relevant to the supplied result and context.
- Do not infer personality, motivation or work ethic from cognitive scores.
- The why field must explain why this candidate's specific cognitive result
  pattern makes the question useful, without turning the result into a final
  judgement.
- The listen_for field must identify evidence that can add practical context
  to the exact reasoning result being explored.
- Use purpose and supplied process context to make the question relevant, but
  never let context replace the cognitive assessment result as the basis.

QUALITY CHECK BEFORE RETURNING

For each question, silently ask: "Which exact cognitive result made me choose
this angle?" If there is no concrete answer in the supplied assessment data,
rewrite the question.
"""


def _fallback_personality_questions(
    *,
    selected_traits: list[str],
    personality_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an evidence-aware last-resort personality question set.

    This path is used only after repeated AI generation failures. It deliberately
    remains conservative because trait definitions are controlled elsewhere,
    but unlike the old fallback it changes the interview angle according to the
    candidate's actual score direction.
    """

    from apps.processes.interview_config import get_interview_section_config

    traits = [
        str(item or "").strip()
        for item in selected_traits or []
        if str(item or "").strip()
    ]

    result_lookup = {
        _normalise_name(item.get("name")): item
        for item in personality_results or []
        if _normalise_name(item.get("name"))
    }

    if not traits:
        ranked = sorted(
            [
                item
                for item in personality_results or []
                if item.get("name") and item.get("sten") is not None
            ],
            key=lambda item: abs(float(item.get("sten")) - 5.5),
            reverse=True,
        )
        traits = [str(item.get("name")).strip() for item in ranked[:6]]

    if not traits:
        raise ValueError("No personality traits are available for the questions.")

    question_count = int(
        get_interview_section_config("personality").get("question_count", 8)
        or 8
    )

    questions = []

    for index in range(question_count):
        trait = traits[index % len(traits)]
        result = result_lookup.get(_normalise_name(trait)) or {}
        sten = result.get("sten")
        band = _sten_band(sten)

        if band == "high":
            question = (
                f"Thinking specifically about {trait}, tell me about a situation "
                "where this preference strongly shaped how you approached the "
                "work. What helped it work well, and when did you need to adapt it?"
            )
            why = (
                f"{trait} is one of the clearer high-side indications in the "
                "candidate's profile, so the question explores both how the "
                "preference shows up and where situational adjustment matters."
            )
            listen_for = (
                "A concrete example, observable behaviour, benefits of the usual "
                "approach, limits or trade-offs, and deliberate adaptation."
            )
        elif band == "low":
            question = (
                f"Thinking specifically about {trait}, tell me about a situation "
                "where the circumstances called for an approach that was less "
                "natural for you. How did you recognise that and what did you do?"
            )
            why = (
                f"{trait} is one of the clearer low-side indications in the "
                "candidate's profile, so the question explores how the person "
                "handles situations that may require behaviour outside that preference."
            )
            listen_for = (
                "A clear situational demand, self-awareness, specific adaptation, "
                "support or strategies used, and what happened as a result."
            )
        else:
            question = (
                f"Thinking specifically about {trait}, describe two situations "
                "where you approached similar demands differently. What in the "
                "context influenced the way you responded?"
            )
            why = (
                f"{trait} sits closer to the middle of the candidate's profile, "
                "so the question explores situational variation rather than "
                "assuming one strongly preferred behavioural direction."
            )
            listen_for = (
                "Different situational cues, deliberate choices, flexibility, and "
                "specific examples of how behaviour changed with the context."
            )

        questions.append(
            {
                "question": question,
                "traits": [trait],
                "why": why,
                "listen_for": listen_for,
            }
        )

    return {
        "type": "questions",
        "items": questions,
    }


def _append_grounding(original, instruction_builder):
    @wraps(original)
    def wrapped(*args, **kwargs):
        prompt = original(*args, **kwargs)
        instruction = instruction_builder(*args, **kwargs)
        return str(prompt).rstrip() + instruction

    wrapped._talena_candidate_question_grounding = True
    return wrapped


def install_candidate_question_grounding_policy() -> None:
    """Require candidate-specific evidence grounding for all question sets."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import cognitive_questions
    from apps.core.ai import motivation_questions
    from apps.core.ai import personality_questions

    original_personality_prompt = personality_questions.build_personality_questions_prompt

    @wraps(original_personality_prompt)
    def personality_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        prompt = original_personality_prompt(
            invitation,
            personality_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _personality_grounding_instruction(
            invitation,
            personality_results,
        )

    personality_questions.build_personality_questions_prompt = personality_prompt

    if hasattr(personality_questions, "_build_personality_questions_repair_prompt"):
        original_personality_repair = (
            personality_questions._build_personality_questions_repair_prompt
        )

        @wraps(original_personality_repair)
        def personality_repair(
            *,
            owner,
            personality_results,
            selected_traits,
        ):
            prompt = original_personality_repair(
                owner=owner,
                personality_results=personality_results,
                selected_traits=selected_traits,
            )
            return str(prompt).rstrip() + _personality_grounding_instruction(
                owner,
                personality_results,
            )

        personality_questions._build_personality_questions_repair_prompt = (
            personality_repair
        )

    # The former deterministic fallback used the same generic question wording
    # for candidates with opposite profiles. Keep a last-resort path, but make
    # its angle depend on the candidate's actual STEN direction.
    personality_questions._build_safe_personality_questions_event = (
        _fallback_personality_questions
    )

    original_motivation_prompt = motivation_questions.build_motivation_questions_prompt

    @wraps(original_motivation_prompt)
    def motivation_prompt(
        *,
        owner,
        motivation_results,
        language_code="en",
    ):
        prompt = original_motivation_prompt(
            owner=owner,
            motivation_results=motivation_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _motivation_grounding_instruction(
            motivation_results
        )

    motivation_questions.build_motivation_questions_prompt = motivation_prompt

    original_cognitive_prompt = cognitive_questions.build_cognitive_questions_prompt

    @wraps(original_cognitive_prompt)
    def cognitive_prompt(
        *,
        owner,
        cognitive_results,
        language_code="en",
    ):
        prompt = original_cognitive_prompt(
            owner=owner,
            cognitive_results=cognitive_results,
            language_code=language_code,
        )
        return str(prompt).rstrip() + _cognitive_grounding_instruction(
            cognitive_results
        )

    cognitive_questions.build_cognitive_questions_prompt = cognitive_prompt

    _INSTALLED = True
