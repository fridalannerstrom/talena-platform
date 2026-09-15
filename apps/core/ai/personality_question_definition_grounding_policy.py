from __future__ import annotations

from functools import wraps

from .personality_ai_evidence import (
    build_owner_personality_ai_evidence,
)
from .shared_context import build_shared_ai_context


_INSTALLED = False


def _selected_parent_traits(owner) -> list[str] | None:
    selected = [
        str(item or "").strip()
        for item in getattr(
            owner,
            "selected_personality_traits",
            None,
        ) or []
        if str(item or "").strip()
    ]

    # Competency mode has its own evidence contract. None is deliberately
    # different from [] here: [] means AI may choose parent traits, while None
    # means do not inject parent-trait grounding into competency questions.
    if any(
        item.casefold().startswith("competency::")
        for item in selected
    ):
        return None

    return selected


def _render_question_result_summaries(
    *,
    owner,
    language_code: str,
) -> str:
    """
    Render only the candidate-specific Result Summary meaning for each trait.

    Raw STEN values, low/high poles and separate indicator rows are intentionally
    omitted from the Personality Questions prompt. Talena first performs the
    psychometric translation, then the model receives the finished candidate
    description and can let administrator guidance control how it is used.
    """

    selected_traits = _selected_parent_traits(owner)
    if selected_traits is None:
        return ""

    evidence = build_owner_personality_ai_evidence(
        owner,
        language_code=language_code,
        include_traits=(selected_traits or None),
    )

    if not evidence:
        return ""

    if str(language_code or "").casefold().startswith("sv"):
        heading = "KANDIDATENS RESULTATSAMMANFATTNING"
        missing = "Ingen resultatsammanfattning finns tillgänglig."
    else:
        heading = "CANDIDATE-SPECIFIC RESULT SUMMARY"
        missing = "No result summary is available."

    blocks: list[str] = []

    for item in evidence:
        technical_name = str(item.get("source_name") or item.get("name") or "").strip()
        display_name = str(item.get("label") or item.get("name") or technical_name).strip()
        summary = str(item.get("summary") or "").strip() or missing

        trait_heading = technical_name
        if display_name and display_name != technical_name:
            trait_heading = f"{technical_name} / {display_name}"

        blocks.append(
            f"PERSONALITY TRAIT: {trait_heading}\n"
            f"{heading}:\n{summary}"
        )

    return "\n\n".join(blocks)


def _replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    start = text.find(start_marker)
    if start < 0:
        return text

    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        return text

    return text[:start] + replacement + text[end:]


def _remove_parent_trait_score_layers(prompt: str) -> str:
    """
    Remove legacy score-direction evidence from parent-trait question prompts.

    #230 originally stacked raw STEN snapshots and direction-oriented quality
    policies on top of the administrator prompt. Those layers could overpower
    the richer Result Summary and make questions broad or mechanically focused
    on high/low/situational language. The underlying policies remain available
    for competency/fallback paths, but parent-trait runtime prompts are reduced
    to the translated candidate summary instead.
    """

    text = str(prompt or "")

    # Base prompt: keep the section for structural clarity but remove raw STEN
    # rows. The translated Result Summary is appended below.
    text = _replace_between(
        text,
        "\nPERSONALITY ASSESSMENT DATA\n",
        "\nAVAILABLE TECHNICAL TRAIT NAMES\n",
        (
            "\nPERSONALITY ASSESSMENT DATA\n"
            "Candidate-specific Result Summary text is supplied in the final "
            "personality evidence section below. Raw STEN values are "
            "intentionally not supplied to question generation.\n"
        ),
    )

    # Remove the older raw-score candidate snapshot while preserving the later
    # candidate-fingerprint/context standard.
    text = _replace_between(
        text,
        "\nTALENA CANDIDATE-SPECIFIC QUESTION GROUNDING\n",
        "\nTALENA CANDIDATE FINGERPRINT STANDARD\n",
        "\n",
    )

    # Remove the older direction-based precision block while preserving the
    # label/8-trait technical contract installed after it.
    text = _replace_between(
        text,
        "\nTALENA PERSONALITY QUESTION PRECISION STANDARD\n",
        "\nTALENA PERSONALITY QUESTION LABEL CONTRACT\n",
        "\n",
    )

    return text.rstrip()


def _build_final_result_summary_grounding(
    *,
    owner,
    language_code: str,
) -> str:
    summaries = _render_question_result_summaries(
        owner=owner,
        language_code=language_code,
    )

    if not summaries:
        return ""

    shared_context = build_shared_ai_context(owner)
    context_text = str(
        shared_context.get("context_text")
        or ""
    ).strip()

    context_requirement = (
        "Meaningful process context is available. Use concrete situations, "
        "responsibilities, tensions, tasks or demands from that context when "
        "they make the selected personality hypothesis more relevant and "
        "specific. The same candidate in a materially different process should "
        "normally receive different questions."
        if shared_context.get("has_context")
        else (
            "No additional process context is available. Do not invent role "
            "requirements or scenarios that were not supplied."
        )
    )

    return f"""
TALENA FINAL PERSONALITY QUESTION EVIDENCE

The following text is the candidate-specific personality meaning Talena has
already derived from the assessment. It uses the same approved score-band
indicator interpretations that build the Result Summary shown in the UI.

Do NOT re-derive the person's personality from raw scores, generic low/high
poles or scale-direction assumptions. Use the Result Summary below as the
primary personality evidence.

{summaries}

PROCESS CONTEXT
{context_text or "No additional process context supplied."}

HOW TO USE THE EVIDENCE

- The Result Summary determines the candidate-specific behavioural hypothesis.
- Process context determines the concrete situation in which that hypothesis is
  useful to explore.
- Administrator guidance remains authoritative for question style, wording,
  interview method, tone, question count, why/listen-for content and other
  non-technical behaviour.
- Do not mechanically repeat the Result Summary. Translate its specific nuance
  into a neutral behavioural question that can confirm, nuance or contradict
  the assessment indication.
- Do not expose raw assessment values or explain scale mechanics to the
  candidate.
- If level terminology is needed, STEN 4–7 is described as situational, but do
  not reduce a richer candidate description to the single word situational.
- Trait labels in technical output must still follow Talena's technical label
  contract.

PROCESS-CONTEXT REQUIREMENT
{context_requirement}

FINAL QUALITY CHECK

Before returning each question, silently verify:
1. Which concrete statement in this candidate's Result Summary made this angle
   worth asking?
2. Which supplied process detail made the scenario specific and relevant?
3. Would a candidate with a meaningfully different Result Summary normally get
   a meaningfully different question?

If the first answer is only the trait name, or relevant supplied context is
ignored, rewrite the question before returning it.
""".strip()


def _finalise_parent_trait_prompt(
    prompt: str,
    *,
    owner,
    language_code: str,
) -> str:
    grounding = _build_final_result_summary_grounding(
        owner=owner,
        language_code=language_code,
    )

    # Competency mode returns no parent-trait summary. Leave its established
    # evidence path untouched.
    if not grounding:
        return prompt

    cleaned = _remove_parent_trait_score_layers(prompt)
    return f"{cleaned}\n\n{grounding}".strip()


def install_personality_question_definition_grounding_policy() -> None:
    """
    Make Talena's Result Summary the personality evidence for interview questions.

    Raw scores are still used internally to build the approved Result Summary,
    but parent-trait question generation receives only that translated summary,
    the process context and administrator guidance. This keeps psychometric
    translation deterministic while leaving question strategy to the admin
    prompt and the model.
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
        return _finalise_parent_trait_prompt(
            str(prompt),
            owner=invitation,
            language_code=resolved_language,
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
        return _finalise_parent_trait_prompt(
            str(prompt),
            owner=owner,
            language_code=resolved_language,
        )

    pq.build_personality_questions_prompt = (
        build_personality_questions_prompt
    )
    pq._build_personality_questions_repair_prompt = (
        build_personality_questions_repair_prompt
    )

    _INSTALLED = True
