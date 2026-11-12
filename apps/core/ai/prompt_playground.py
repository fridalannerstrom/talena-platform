from __future__ import annotations

from typing import Any

from .language import (
    get_ai_language_instruction,
    normalize_ai_language,
)

from .openai_client import (
    get_chat_model,
    get_openai_client,
)

from .prompt_templates import (
    get_global_ai_guidance,
    get_purpose_ai_guidance,
)


# ============================================================
# Fixed playground candidate
# ============================================================

SAMPLE_CANDIDATE_NAME = "CANDIDATE_A"


PERSONALITY_EVIDENCE = """
PERSONALITY RESULTS

- Emotional Control: STEN 3
- Adaptability: STEN 2
- Altruism: STEN 9
- Networking: STEN 8
- Analytical: STEN 6
- Structured: STEN 4
- Creativity: STEN 8
- Decisiveness: STEN 7
""".strip()


MOTIVATION_EVIDENCE = """
MOTIVATION RESULTS

- Achievement: high
- Learning: high
- Autonomy: high
- Stability: low
- Recognition: medium
- Collaboration: medium
""".strip()


COGNITIVE_EVIDENCE = """
COGNITIVE RESULTS

- Verbal reasoning: 72nd percentile
- Logical reasoning: 65th percentile
- Numerical reasoning: 48th percentile
""".strip()


RESPONSE_STYLE_EVIDENCE = """
RESPONSE STYLE RESULTS

- Social desirability: STEN 4
- Profile spread: STEN 8
- Ratings spread: STEN 7
""".strip()


INTERVIEW_EVIDENCE = """
SAMPLE INTERVIEW NOTES

- Alex described successfully building a long-term relationship
  with a demanding customer.

- Alex gave an example of independently identifying a commercial
  opportunity and developing the proposal.

- Alex described fast organisational change as stressful and said
  that clear priorities helped.

- Alex gave a less detailed example when asked about handling
  several competing priorities at the same time.

These are sample interview notes only.
""".strip()


ALL_ASSESSMENT_EVIDENCE = "\n\n".join(
    [
        PERSONALITY_EVIDENCE,
        MOTIVATION_EVIDENCE,
        COGNITIVE_EVIDENCE,
        RESPONSE_STYLE_EVIDENCE,
    ]
)


# ============================================================
# Fixed process contexts
# ============================================================

RECRUITMENT_CONTEXT = """
Role: Key Account Manager.

The role involves:

- building long-term customer relationships
- working independently
- identifying commercial opportunities
- adapting to changing customer needs

Do not assume any requirements beyond the information above.
""".strip()


TEAM_DEVELOPMENT_CONTEXT = """
The person is part of an existing customer-facing team.

The team wants to improve:

- collaboration
- communication
- understanding of different working preferences
- how team members use complementary strengths

This is a development process, not a selection process.
""".strip()


LEADER_DEVELOPMENT_CONTEXT = """
The person currently has leadership responsibility.

The development process focuses on:

- leading through change
- communication
- delegation
- decision-making
- supporting team members

This is a leadership development process, not a recruitment decision.
""".strip()


FLEXIBLE_CONTEXT = """
This is a general development process.

There is no predefined role requirement or selection decision.

Use the available assessment information to identify useful
areas for reflection and further exploration.
""".strip()


# ============================================================
# Playground scenarios
# ============================================================

PLAYGROUND_SCENARIOS = {

    # --------------------------------------------------------
    # Global
    # --------------------------------------------------------

    "global_ai_guidance": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate a concise overall Talena candidate insight.

Demonstrate how the tested global administrator guidance affects:

- interpretation
- language
- terminology
- caution
- communication style

Use several types of assessment evidence so the administrator can
see whether the global guidance is applied consistently.
""".strip(),
    },


    # --------------------------------------------------------
    # Purpose guidance
    # --------------------------------------------------------

    "purpose_hiring_guidance": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate a concise candidate insight specifically for a recruitment
process.

Show how the tested Recruitment guidance changes what Talena
prioritises, interprets and recommends exploring.
""".strip(),
    },

    "purpose_team_development_guidance": {
        "purpose": "team_development",
        "purpose_label": "Team development",
        "context": TEAM_DEVELOPMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate a concise development insight for an existing team member.

Focus on how the tested Team development guidance affects the
interpretation of contribution, collaboration, working preferences
and useful areas for team discussion.
""".strip(),
    },

    "purpose_leader_development_guidance": {
        "purpose": "leader_development",
        "purpose_label": "Leader development",
        "context": LEADER_DEVELOPMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate a concise leadership development insight.

Show how the tested Leader development guidance affects the
interpretation of possible leadership behaviours, strengths,
development areas and useful reflection.
""".strip(),
    },

    "purpose_flexible_guidance": {
        "purpose": "unsure",
        "purpose_label": "Flexible process",
        "context": FLEXIBLE_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate a concise general development insight.

Show how the tested Flexible process guidance affects the
interpretation without assuming recruitment, team or leadership
requirements that are not supplied.
""".strip(),
    },


    # --------------------------------------------------------
    # Overview / assistant
    # --------------------------------------------------------

    "ai_overview": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate only sample content for:

Overall interpretation

Create a concise overall synthesis using the available assessment
evidence and supplied process context.

Do not generate supportive patterns, areas to explore
or recommended next steps.
""".strip(),
    },

    "candidate_chat": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Act as Talena's candidate-aware AI assistant.

Answer this sample user question:

"What are the three most useful things I should explore further
with Alex in the interview?"

Give a concise, practical answer grounded only in the supplied
assessment evidence and process context.
""".strip(),
    },

    "ai_overview_supportive_patterns": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate only sample content for:

What supports the purpose

Identify assessment patterns that may be potentially supportive
in relation to the supplied process purpose and context.

Do not generate the overall interpretation or areas to explore.
""".strip(),
    },

    "ai_overview_areas_to_explore": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate only sample content for:

What to explore or consider

Identify areas where additional information, discussion or
behavioural evidence may improve understanding.

Do not generate the overall interpretation or supportive patterns.
""".strip(),
    },


    # --------------------------------------------------------
    # Personality
    # --------------------------------------------------------

    "personality_interpretation": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Generate only sample content for:

Overall personality interpretation

Create a concise and balanced synthesis of the supplied
personality results in relation to the process context.

Do not generate profile dynamics, supportive patterns
or areas to explore.
""".strip(),
    },

    "personality_trait_interplay": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Generate only the sample content for:

Profile dynamics / Personality trait interplay

Focus specifically on how two or more supplied personality
preferences may interact, reinforce, balance or create possible
tensions.

Do not generate the full personality interpretation.
""".strip(),
    },

    "personality_supportive_patterns": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Generate only sample content for:

Potentially supportive patterns

Use the supplied personality results and process context.

Do not generate the overall personality interpretation,
profile dynamics or areas to explore.
""".strip(),
    },

    "personality_areas_to_explore": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Generate only sample content for:

What to explore or validate

Use the supplied personality results and process context.

Describe useful areas for further exploration without treating
them automatically as weaknesses or risks.

Do not generate the overall personality interpretation,
profile dynamics or supportive patterns.
""".strip(),
    },

    "personality_trait_selection": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Simulate Talena's automatic personality trait selection.

The user has NOT manually selected any personality traits.

Return:

Selected traits:
Trait name
Trait name

Then briefly explain why each selected trait was prioritised.

Use only exact personality trait names supplied in the sample results.
""".strip(),
    },

    "personality_questions": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": PERSONALITY_EVIDENCE,
        "task": """
Generate sample personality interview questions.

Assume these personality traits were selected:

- Emotional Control
- Adaptability
- Networking

For each question show:

Question
Trait or traits
Why this matters
What to listen for

Keep the preview reasonably concise.
""".strip(),
    },

    "response_style_interpretation": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": RESPONSE_STYLE_EVIDENCE,
        "task": """
Generate only sample content for:

Response-style interpretation

Explain what the supplied response pattern may indicate and what
should be kept in mind when reading the personality profile.

Do not generate interview approach guidance or interview questions.
""".strip(),
    },

    "response_style_interview_approach": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": RESPONSE_STYLE_EVIDENCE,
        "task": """
Generate only sample content for:

How to approach the conversation

Use the supplied response-style indicators to provide practical,
non-accusatory interview guidance and useful open questions.

Do not generate or change the separate personality-profile
interpretation.
""".strip(),
    },


    # --------------------------------------------------------
    # Motivation
    # --------------------------------------------------------

    "motivation_interpretation": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": MOTIVATION_EVIDENCE,
        "task": """
Generate only sample content for:

Overall motivation interpretation

Create a concise overall synthesis of the supplied motivation
results in relation to the process context.

Do not generate expectation setting, engagement conditions
or areas to clarify.
""".strip(),
    },

    "motivation_expectation_setting": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": MOTIVATION_EVIDENCE,
        "task": """
Generate only sample content for:

Realistic expectation setting

Use the supplied motivation results and process context.

Show what may be useful to clarify with the person about
expectations, circumstances or working conditions.

Do not generate the overall motivation interpretation,
engagement conditions or areas to clarify.
""".strip(),
    },

    "motivation_engagement_conditions": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": MOTIVATION_EVIDENCE,
        "task": """
Generate only sample content for:

Conditions likely to support engagement

Use the supplied motivation results and process context.

Describe possible conditions that may support energy and engagement
without treating them as absolute requirements.

Do not generate the overall motivation interpretation,
expectation setting or areas to clarify.
""".strip(),
    },

    "motivation_areas_to_clarify": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": MOTIVATION_EVIDENCE,
        "task": """
Generate only sample content for:

What to explore or clarify

Use the supplied motivation results and process context.

Identify useful topics for further discussion without treating
less prominent motivation factors automatically as problems.

Do not generate the overall motivation interpretation,
expectation setting or engagement conditions.
""".strip(),
    },

    "motivation_questions": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": MOTIVATION_EVIDENCE,
        "task": """
Generate sample motivation interview questions.

For each question show:

Question
Motivational area
Why this matters
What to listen for

Use the supplied motivation results and process context.
""".strip(),
    },


    # --------------------------------------------------------
    # Cognitive
    # --------------------------------------------------------

    "cognitive_interpretation": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": COGNITIVE_EVIDENCE,
        "task": """
Generate a sample Talena cognitive interpretation.

Describe the available verbal, logical and numerical results
carefully and in relation to the supplied process context.

Distinguish measured cognitive performance from assumptions about
overall competence or future job performance.
""".strip(),
    },

    "cognitive_considerations": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": COGNITIVE_EVIDENCE,
        "task": """
Generate only sample content for:

Relevant considerations

Use the supplied cognitive assessment results and process context.

Highlight useful considerations, limitations or areas where
additional behavioural evidence may improve understanding.

Do not generate the practical cognitive interpretation.
""".strip(),
    },

    "cognitive_questions": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": COGNITIVE_EVIDENCE,
        "task": """
Generate sample interview questions that can help add behavioural
context to the cognitive assessment results.

For each question show:

Question
Why this matters
What to listen for

Do not ask the candidate to repeat or solve assessment test items.
""".strip(),
    },


    # --------------------------------------------------------
    # Decision support
    # --------------------------------------------------------

    "pre_interview_decision_support": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE,
        "task": """
Generate sample pre-interview decision support.

The interview has not yet taken place.

Summarise:

Evidence relevant to the process
Potentially supportive indications
Important uncertainties
What should be validated in interview
Suggested next interview focus

Do not invent interview evidence.
""".strip(),
    },

    "post_interview_decision_support": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": """
Generate only sample content for After interview · Overall synthesis.
Do not generate the other After interview sections.
""".strip(),
    },

    "post_interview_supported_indications": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": "Generate only Evidence supporting assessment indications.",
    },

    "post_interview_added_nuance": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": "Generate only What the interview adds or nuances.",
    },

    "post_interview_contradictions": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": "Generate only Contradictions or tensions to consider.",
    },

    "post_interview_remaining_uncertainties": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": "Generate only Remaining uncertainties.",
    },

    "post_interview_suggested_follow_up": {
        "purpose": "hiring",
        "purpose_label": "Recruitment",
        "context": RECRUITMENT_CONTEXT,
        "evidence": ALL_ASSESSMENT_EVIDENCE + "\n\n" + INTERVIEW_EVIDENCE,
        "task": "Generate only Suggested follow-up.",
    },

}


SUPPORTED_PLAYGROUND_PROMPTS = frozenset(
    PLAYGROUND_SCENARIOS.keys()
)


PURPOSE_PROMPT_TO_PURPOSE = {
    "purpose_hiring_guidance": "hiring",
    "purpose_team_development_guidance": "team_development",
    "purpose_leader_development_guidance": "leader_development",
    "purpose_flexible_guidance": "unsure",
}

PLAYGROUND_PURPOSE_LABELS = {
    "hiring": "Recruitment",
    "team_development": "Team development",
    "leader_development": "Leader development",
    "unsure": "Flexible process",
}


# ============================================================
# Public helpers
# ============================================================

def is_prompt_playground_available(
    prompt_key: str,
) -> bool:
    return (
        str(prompt_key or "").strip()
        in SUPPORTED_PLAYGROUND_PROMPTS
    )


def list_playground_prompt_keys() -> list[str]:
    return sorted(
        SUPPORTED_PLAYGROUND_PROMPTS
    )


def get_playground_sample_data(
    prompt_key: str,
    *,
    purpose: str | None = None,
    context: str | None = None,
) -> dict[str, Any] | None:
    """
    Return the sample data used by the playground.

    Purpose and context may be overridden by the administrator.

    Purpose-specific guidance prompts keep their own fixed purpose.
    """

    prompt_key = str(
        prompt_key or ""
    ).strip()

    scenario = PLAYGROUND_SCENARIOS.get(
        prompt_key
    )

    if not scenario:
        return None

    locked_purpose = PURPOSE_PROMPT_TO_PURPOSE.get(
        prompt_key
    )

    if locked_purpose:
        effective_purpose = locked_purpose

    else:
        requested_purpose = str(
            purpose or ""
        ).strip()

        if requested_purpose in PLAYGROUND_PURPOSE_LABELS:
            effective_purpose = requested_purpose

        else:
            effective_purpose = scenario.get(
                "purpose",
                "hiring",
            )

    if context is None:
        effective_context = scenario.get(
            "context",
            "",
        )

    else:
        # Empty string is intentionally allowed.
        effective_context = str(context)

    return {
        "candidate_name": SAMPLE_CANDIDATE_NAME,

        "purpose": effective_purpose,
        "purpose_label": PLAYGROUND_PURPOSE_LABELS.get(
            effective_purpose,
            effective_purpose,
        ),

        "purpose_locked": bool(
            locked_purpose
        ),

        "context": effective_context,

        "evidence": scenario.get(
            "evidence",
            "",
        ),
    }


# ============================================================
# Prompt layer builder
# ============================================================

def _build_playground_system_instruction(
    *,
    prompt_key: str,
    prompt_text: str,
    language_code: str,
    purpose: str | None,
) -> str:
    """
    Build the shared guidance hierarchy for the playground.

    The currently edited prompt replaces its corresponding layer
    when testing Global or Purpose guidance.

    Feature-specific prompts are injected separately in the
    playground user prompt.
    """

    if prompt_key == "global_ai_guidance":
        global_guidance = prompt_text

    else:
        global_guidance = get_global_ai_guidance(
            language=language_code,
        )

    tested_purpose = (
        PURPOSE_PROMPT_TO_PURPOSE.get(
            prompt_key
        )
    )

    if tested_purpose:
        purpose_guidance = prompt_text

    else:
        purpose_guidance = (
            get_purpose_ai_guidance(
                purpose=purpose,
                language=language_code,
            )
            if purpose
            else ""
        )

    language_instruction = (
        get_ai_language_instruction(
            language_code
        )
    )

    parts = [
        """
You are running inside Talena's administrator AI prompt playground.

This is a preview only.

Never treat the sample candidate as a real person.

Use only the evidence explicitly supplied in the playground.

Do not invent assessment results, experience, requirements,
interview evidence or other candidate information.
""".strip(),

        "GLOBAL ADMINISTRATOR AI GUIDANCE",
        global_guidance,
    ]

    if purpose_guidance:
        parts.extend(
            [
                "PURPOSE-SPECIFIC ADMINISTRATOR AI GUIDANCE",
                purpose_guidance,
            ]
        )

    parts.extend(
        [
            "OUTPUT LANGUAGE",
            language_instruction,
        ]
    )

    return "\n\n".join(
        str(part).strip()
        for part in parts
        if str(part or "").strip()
    )


# ============================================================
# Main playground runner
# ============================================================

def run_prompt_playground(
    *,
    prompt_key: str,
    prompt_text: str,
    language_code: str = "sv",
    purpose: str | None = None,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Run an unsaved administrator prompt against fixed sample data.

    Nothing is saved.
    No real candidate data is used.
    """

    prompt_key = str(
        prompt_key or ""
    ).strip()

    prompt_text = str(
        prompt_text or ""
    ).strip()

    language_code = normalize_ai_language(
        language_code
    )

    if not prompt_text:
        raise ValueError(
            "Prompt text is required."
        )

    scenario = PLAYGROUND_SCENARIOS.get(
        prompt_key
    )

    if not scenario:
        raise ValueError(
            "This AI prompt is not yet supported "
            "by the playground."
        )

    sample_data = get_playground_sample_data(
        prompt_key,
        purpose=purpose,
        context=context,
    )

    if not sample_data:
        raise ValueError(
            "Could not build playground sample data."
        )

    effective_purpose = sample_data[
        "purpose"
    ]

    effective_context = sample_data[
        "context"
    ]

    system_instruction = (
        _build_playground_system_instruction(
            prompt_key=prompt_key,
            prompt_text=prompt_text,
            language_code=language_code,
            purpose=effective_purpose,
        )
    )

    # Global and purpose prompts are already inserted in their
    # correct system-level guidance layer.
    #
    # Feature prompts are inserted here as the feature-specific
    # guidance being tested.

    if (
        prompt_key == "global_ai_guidance"
        or prompt_key in PURPOSE_PROMPT_TO_PURPOSE
    ):
        tested_guidance_block = """
The administrator guidance being tested has already replaced the
corresponding Global or Purpose guidance layer in the system
instructions.

Apply that guidance when completing the preview task.
""".strip()

    else:
        tested_guidance_block = f"""
FEATURE-SPECIFIC ADMINISTRATOR AI GUIDANCE BEING TESTED

The following text is the administrator's current, possibly
unsaved guidance for this AI feature.

For the playground preview, treat this text as the active
feature-specific administrator guidance.

--- TESTED GUIDANCE START ---

{prompt_text}

--- TESTED GUIDANCE END ---
""".strip()

    user_prompt = f"""
TALENA AI PROMPT PLAYGROUND


SAMPLE CANDIDATE

Name: {SAMPLE_CANDIDATE_NAME}


PROCESS PURPOSE

{sample_data["purpose_label"]}


PROCESS CONTEXT

{effective_context if effective_context.strip() else "No process context supplied."}


AVAILABLE SAMPLE EVIDENCE

{scenario["evidence"]}


TESTED ADMINISTRATOR GUIDANCE

{tested_guidance_block}


PREVIEW TASK

{scenario["task"]}


PLAYGROUND OUTPUT RULES

Generate only a concise preview that helps an administrator
understand how the tested guidance affects AI output.

Do not discuss the playground itself.

Do not mention that the prompt is unsaved.

Do not use Markdown syntax.

Do not use Markdown headings, asterisks or code fences.

Use plain text with clear section headings when sections are useful.

Do not invent information that is not present in the supplied
sample evidence or process context.
""".strip()

    client = get_openai_client()

    response = client.chat.completions.create(
        model=get_chat_model(),
        messages=[
            {
                "role": "system",
                "content": system_instruction,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        stream=False,
    )

    output = (
        response.choices[0].message.content
        or ""
    ).strip()

    return {
        "prompt_key": prompt_key,
        "language": language_code,

        "sample_candidate": (
            sample_data["candidate_name"]
        ),

        "sample_purpose": (
            sample_data["purpose"]
        ),

        "sample_purpose_label": (
            sample_data["purpose_label"]
        ),

        "sample_context": (
            sample_data["context"]
        ),

        "output": output,
    }
