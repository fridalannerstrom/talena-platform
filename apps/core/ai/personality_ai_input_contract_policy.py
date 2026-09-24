from __future__ import annotations

from functools import wraps

from .language import normalize_ai_language
from .personality_ai_evidence import build_owner_personality_ai_evidence
from .shared_context import build_shared_ai_context


_INSTALLED = False


def _language(value: str | None) -> str:
    return normalize_ai_language(value or "en")


def _replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> str:
    text = str(text or "")
    start = text.find(start_marker)
    if start < 0:
        return text

    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        return text

    return text[:start] + replacement + text[end:]


def _remove_between(
    text: str,
    start_marker: str,
    end_marker: str,
) -> str:
    return _replace_between(
        text,
        start_marker,
        end_marker,
        "",
    )


def _insert_before_marker(
    text: str,
    marker: str,
    section: str,
) -> str:
    text = str(text or "")
    section = str(section or "").strip()

    if not section:
        return text

    index = text.find(marker)
    if index < 0:
        return f"{text.rstrip()}\n\n{section}".strip()

    before = text[:index].rstrip()
    after = text[index:].lstrip("\n")
    return f"{before}\n\n{section}\n\n{after}".strip()


def _render_personality_result_summaries(
    owner,
    *,
    language_code: str,
) -> str:
    """
    Render the shared personality evidence used by personality AI features.

    Deliberately expose the already translated Result Summary rather than raw
    STEN values, low/high poles or separate indicator rows. The underlying
    indicator results are still what Talena uses to build the summary.
    """

    language_code = _language(language_code)
    evidence = build_owner_personality_ai_evidence(
        owner,
        language_code=language_code,
    )

    if not evidence:
        return ""

    if language_code == "sv":
        summary_heading = "KANDIDATENS RESULTATSAMMANFATTNING"
        missing = "Ingen resultatsammanfattning finns tillgänglig."
    else:
        summary_heading = "CANDIDATE-SPECIFIC RESULT SUMMARY"
        missing = "No result summary is available."

    blocks: list[str] = []

    for item in evidence:
        technical_name = str(
            item.get("source_name")
            or item.get("name")
            or ""
        ).strip()
        display_name = str(
            item.get("label")
            or item.get("name")
            or technical_name
        ).strip()
        summary = str(item.get("summary") or "").strip() or missing

        trait_heading = technical_name
        if display_name and display_name != technical_name:
            trait_heading = f"{technical_name} / {display_name}"

        blocks.append(
            f"PERSONALITY TRAIT: {trait_heading}\n"
            f"{summary_heading}:\n{summary}"
        )

    return "\n\n".join(blocks)


def _shared_personality_input(
    owner,
    *,
    language_code: str,
    include_process_context: bool = True,
) -> str:
    language_code = _language(language_code)
    summaries = _render_personality_result_summaries(
        owner,
        language_code=language_code,
    )
    shared = build_shared_ai_context(owner) if include_process_context else None
    context_section = (
        "PROCESS PURPOSE\n"
        f"{shared.get('purpose_label') or 'General insights'}\n\n"
        "PROCESS CONTEXT\n"
        f"{shared.get('context_text') or 'No additional process context supplied.'}"
        if shared else ""
    )
    context_rule = (
        "- Process context may make an interpretation concrete and relevant, "
        "but it must not change the meaning of the assessment result or create "
        "unsupported facts.\n"
        "- Use the supplied process context to understand WHERE, WHEN or WHY "
        "that indication may be useful to discuss for this process.\n"
        if shared else ""
    )

    if not summaries:
        summaries = (
            "No candidate-specific personality Result Summary is available."
            if language_code == "en"
            else "Ingen kandidatspecifik Resultatsammanfattning är tillgänglig."
        )

    return f"""
TALENA SHARED PERSONALITY AI INPUT

The personality evidence below is the translated candidate-specific meaning
used in Talena's Result Summary UI. Treat it as the primary personality meaning.
Do not re-derive the person's personality from raw STEN values, generic scale
poles or outside definitions.

{summaries}

{context_section}

SHARED EVIDENCE RULES

- Personality Result Summary text describes assessment indications, not proven
  behaviour, competence, performance or role fit.
- Use the Result Summary to understand WHAT is indicated for this candidate.
{context_rule}- Do not mechanically repeat the Result Summary in user-facing text. Use it as
  evidence for a nuanced, candidate-specific interpretation.
""".strip()


def _personality_interpretation_admin_guidance(
    *,
    language_code: str,
) -> str:
    from .personality_motivation_interaction_policy import (
        PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN,
        PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV,
    )
    from .prompt_templates import (
        get_ai_feature_prompt_instructions,
        get_global_ai_guidance,
    )

    language_code = _language(language_code)
    global_guidance = get_global_ai_guidance(language=language_code)
    overall = get_ai_feature_prompt_instructions(
        key="personality_interpretation",
        language=language_code,
    )
    dynamics = get_ai_feature_prompt_instructions(
        key="personality_trait_interplay",
        language=language_code,
    )
    motivation_default = (
        PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV
        if language_code == "sv"
        else PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN
    )
    motivation = get_ai_feature_prompt_instructions(
        key="personality_motivation_interaction",
        language=language_code,
        default=motivation_default,
    )
    supportive = get_ai_feature_prompt_instructions(
        key="personality_supportive_patterns",
        language=language_code,
    )
    explore = get_ai_feature_prompt_instructions(
        key="personality_areas_to_explore",
        language=language_code,
    )

    return f"""
ADMINISTRATOR AI GUIDANCE

GLOBAL ADMINISTRATOR AI GUIDANCE

The following effective global administrator guidance applies to EVERY
personality AI box in this call.

{global_guidance}

OVERALL PERSONALITY INTERPRETATION · BOX-SPECIFIC GUIDANCE

Applies only to interpretation_delta / Overall interpretation, together with
the global guidance above.

{overall}

COMBINED TRAIT DYNAMICS · BOX-SPECIFIC GUIDANCE

Applies only to profile_dynamics / Combined trait dynamics, together with the
global guidance above.

{dynamics}

PERSONALITY × MOTIVATION · BOX-SPECIFIC GUIDANCE

Applies only to motivation_interaction / Interaction with motivation, together
with the global guidance above.

{motivation}

For this box, the personality Result Summary and motivation assessment results
alone determine which interaction is supported. Do not infer an interaction
that is unsupported by the assessment evidence.

POTENTIAL STRENGTHS · BOX-SPECIFIC GUIDANCE

Applies only to supportive_patterns / Potential strengths, together with the
global guidance above.

{supportive}

WHAT TO EXPLORE OR VALIDATE · BOX-SPECIFIC GUIDANCE

Applies only to areas_to_explore / What to explore or validate, together with
the global guidance above.

{explore}

ADMIN GUIDANCE APPLICATION RULE

Every box uses exactly two administrator layers:
1. GLOBAL ADMINISTRATOR AI GUIDANCE; and
2. the BOX-SPECIFIC GUIDANCE for that box.

Do not let one box's feature-specific prompt control another box. The overall
personality prompt is not a substitute for a dedicated box prompt. Global
guidance remains active everywhere.
""".strip()


def _response_style_admin_guidance(*, language_code: str) -> str:
    from .prompt_templates import (
        get_ai_feature_prompt_instructions,
        get_global_ai_guidance,
    )

    language_code = _language(language_code)
    global_guidance = get_global_ai_guidance(language=language_code)
    interpretation = get_ai_feature_prompt_instructions(
        key="response_style_interpretation",
        language=language_code,
    )
    interview = get_ai_feature_prompt_instructions(
        key="response_style_interview_approach",
        language=language_code,
    )

    return f"""
ADMINISTRATOR AI GUIDANCE

GLOBAL ADMINISTRATOR AI GUIDANCE

Applies to every response-style AI output in this call.

{global_guidance}

RESPONSE-STYLE INTERPRETATION · BOX-SPECIFIC GUIDANCE

Applies to summary_delta, how_to_interpret, combination_note and context_note,
together with the global guidance above.

{interpretation}

INTERVIEW APPROACH · BOX-SPECIFIC GUIDANCE

Applies to recommended_approach and questions, together with the global
guidance above.

{interview}

ADMIN GUIDANCE APPLICATION RULE

Every response-style output uses the global guidance plus its own dedicated
feature guidance. Do not let interview-approach instructions rewrite the
response-style interpretation, and do not let interpretation-specific guidance
silently replace the interview-approach prompt.
""".strip()


def _install_personality_interpretation_contract(module) -> None:
    original = module.build_personality_interpretation_prompt

    if getattr(original, "_talena_personality_ai_input_contract", False):
        return

    @wraps(original)
    def wrapped(
        owner,
        personality_results,
        *,
        motivation_results=None,
        language_code="en",
    ):
        language_code = _language(language_code)
        prompt = original(
            owner,
            personality_results,
            motivation_results=motivation_results,
            language_code=language_code,
        )

        # Remove the old raw parent-trait score payload. Talena has already
        # translated those scores into the Result Summary supplied below.
        prompt = _replace_between(
            prompt,
            "\nPERSONALITY ASSESSMENT DATA\n",
            "\nMOTIVATION ASSESSMENT DATA\n",
            (
                "\nPERSONALITY ASSESSMENT DATA\n"
                "Use TALENA SHARED PERSONALITY AI INPUT below. Raw parent-trait "
                "STEN values are intentionally not the interpretation input.\n"
            ),
        )

        # #231's earlier wrapper may have inserted a detailed STEN/indicator
        # evidence block. Remove it so there is one personality source of truth.
        prompt = _remove_between(
            prompt,
            "\nTALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE\n",
            "\n\nADMINISTRATOR AI GUIDANCE\n",
        )

        shared_input = _shared_personality_input(
            owner,
            language_code=language_code,
            include_process_context=False,
        )
        prompt = _insert_before_marker(
            prompt,
            "\nADMINISTRATOR AI GUIDANCE\n",
            shared_input,
        )

        # Rebuild admin guidance cleanly from the effective global prompt plus
        # the effective prompt for each exact UI box.
        prompt = _replace_between(
            prompt,
            "\nADMINISTRATOR AI GUIDANCE\n",
            "\nTALENA TECHNICAL OUTPUT CONTRACT\n",
            (
                "\n"
                + _personality_interpretation_admin_guidance(
                    language_code=language_code
                )
                + "\n\n"
            ),
        )

        return str(prompt).strip()

    wrapped._talena_personality_ai_input_contract = True
    module.build_personality_interpretation_prompt = wrapped


def _install_response_style_contract(module) -> None:
    original = module.build_response_style_guidance_prompt

    if getattr(original, "_talena_personality_ai_input_contract", False):
        return

    @wraps(original)
    def wrapped(
        *,
        guidance_owner,
        response_styles,
        language_code="en",
    ):
        language_code = _language(language_code)
        prompt = original(
            guidance_owner=guidance_owner,
            response_styles=response_styles,
            language_code=language_code,
        )

        shared_input = _shared_personality_input(
            guidance_owner,
            language_code=language_code,
        )
        response_style_rule = """
RESPONSE-STYLE EVIDENCE BOUNDARY

Response-style results remain the primary evidence for claims about how the
questionnaire was answered. The personality Result Summary is supporting
context for understanding the profile that those response styles qualify.
Do not infer a response-style result from the trait summaries, and do not use a
response-style result to rewrite the candidate's personality Result Summary.
""".strip()

        prompt = _insert_before_marker(
            prompt,
            "\nADMINISTRATOR AI GUIDANCE\n",
            f"{shared_input}\n\n{response_style_rule}",
        )

        prompt = _replace_between(
            prompt,
            "\nADMINISTRATOR AI GUIDANCE\n",
            "\nTALENA TECHNICAL OUTPUT CONTRACT\n",
            (
                "\n"
                + _response_style_admin_guidance(
                    language_code=language_code
                )
                + "\n\n"
            ),
        )

        return str(prompt).strip()

    wrapped._talena_personality_ai_input_contract = True
    module.build_response_style_guidance_prompt = wrapped


def install_personality_ai_input_contract_policy() -> None:
    """
    Give personality AI features a shared Result Summary evidence layer.

    Personality Questions retain their dedicated purpose and process context
    for interview preparation. Personality Interpretation uses only assessment
    evidence, while Response Styles keeps its existing contextual input.
    """

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import personality_interpretation
    from apps.core.ai import response_style_guidance

    _install_personality_interpretation_contract(personality_interpretation)
    _install_response_style_contract(response_style_guidance)

    _INSTALLED = True
