from __future__ import annotations

from typing import Any

from django.core.exceptions import ObjectDoesNotExist


SUPPORTED_PROMPT_LANGUAGES = {
    "sv",
    "en",
}


# ============================================================
# Talena AI prompt registry
# ============================================================
#
# This registry defines the administrator-editable business
# guidance for Talena's AI features.
#
# Technical rules, psychometric safeguards, evidence boundaries
# and output contracts remain protected in each AI implementation.
#
# Database entries in AIPromptTemplate are GLOBAL overrides.
# They affect all customers in Talena.
# ============================================================

RESPONSE_STYLE_GUIDANCE_DEFAULT = """
GENERAL PRINCIPLE

Response styles provide context for interpreting the personality
profile. They are not personality traits, measures of ability,
measures of suitability or proof of honesty.

They may help the practitioner understand how the candidate approached
the questionnaire and how much additional exploration may be useful.


SOCIAL DESIRABILITY

LOW
- May indicate a relatively self-critical way of describing oneself.
- Some personality preferences may be stronger than the displayed
  profile initially suggests.
- Do not assume low confidence or lack of capability.
- A useful next step is to ask the candidate which two or three traits
  someone who knows them well might rate more strongly.
- Invite the candidate to identify qualities they may have understated.

TYPICAL
- Usually suggests a reasonably balanced self-presentation.
- There is no clear tendency towards either overly critical or overly
  positive self-description.
- The personality profile may generally be interpreted in the usual way,
  while still validating important findings with examples.

HIGH
- May indicate a positive self-presentation.
- Some preferences may be less pronounced than the profile initially
  suggests.
- This must not be interpreted as dishonesty.
- A useful next step is to ask which two or three traits the candidate
  may possibly have rated somewhat generously.
- Validate strong results through specific behavioural examples.


PROFILE SPREAD

LOW
- The responses show less differentiation or consistency across
  questions connected to the same personality traits.
- This may have several possible explanations and none should be stated
  as fact.
- Possible areas to explore include:
  - whether the current role matches the person's natural preferences
  - a recent change of role, tasks, goals or responsibilities
  - a role that requires several different behaviours
  - strong situational adaptability
  - the influence of the current environment, manager or team
  - reluctance to take a firm position on some questions
  - uncertainty about how the person typically behaves
- Use neutral questions and explore context before drawing conclusions.

TYPICAL
- The candidate appears to have responded consistently in some parts
  of the questionnaire and with more variation in others.
- Clearer extremes in the personality profile may be the areas in which
  the candidate responded most consistently.
- Validate the most important findings and allow the candidate to add
  situational nuance.

HIGH
- The profile shows clear differentiation across the personality traits.
- The candidate appears to have responded consistently to questions
  connected to the same traits.
- The candidate may be more likely to recognise themselves in the
  resulting personality profile.
- Strong differences should still be explored rather than treated as
  fixed behaviour.


RATINGS SPREAD

LOW
- The candidate used a relatively narrow range of response options and
  made less use of the extreme ends of the scale.
- The candidate may be inclined to qualify answers or explain that their
  behaviour depends on the situation.
- Allow additional time during feedback.
- Use concrete examples and follow-up questions to help the candidate
  clarify where their preferences are strongest.

TYPICAL
- The candidate appears to have used the response scale without a strong
  preference for either neutral or extreme options.
- The profile may generally be interpreted in the usual way while still
  validating important conclusions with examples.

HIGH
- The candidate used a broad range of response options, including the
  more extreme ends of the scale.
- The candidate may express preferences and positions relatively clearly.
- Strong results should still be validated with examples and should not
  automatically be interpreted as fixed or inflexible behaviour.


KNOWN COMBINATION: PROFILE SPREAD HIGH AND RATINGS SPREAD HIGH

- The candidate used a broad range of ratings and appears to have
  responded consistently across related questions.
- The candidate may be relatively likely to recognise themselves in the
  personality profile.
- Consider the candidate's current situation when discussing why
  particular traits are especially pronounced.


KNOWN COMBINATION: PROFILE SPREAD LOW AND RATINGS SPREAD HIGH

- The candidate used clear or extreme ratings, while responses across
  questions connected to the same traits showed less consistency.
- Do not label this as poor self-awareness.
- Explore whether the pattern may relate to:
  - recent changes in role or responsibilities
  - a role requiring several different behaviours
  - strong situational adaptation
  - the influence of a manager, team or working environment
  - uncertainty about which situation to use as the reference point
  - a wish to present oneself in a particular way
- Treat the profile as a starting point for discussion and ask for
  concrete examples from different situations.
""".strip()


AI_PROMPT_REGISTRY: dict[str, dict[str, Any]] = {

    "personality_interpretation": {
        "name": "Personality interpretation",
        "category": "Personality",
        "description": (
            "Controls the tone, emphasis and communication style used "
            "when Talena interprets a candidate's personality profile."
        ),
        "defaults": {

            "sv": """
Skriv tolkningen på ett balanserat, professionellt och utvecklingsorienterat sätt.

Hjälp användaren förstå kandidatens viktigaste beteendepreferenser utan att
beskriva dem som fasta egenskaper.

Lyft både mönster som kan vara stödjande och områden som kan vara relevanta
att utforska vidare.

Var försiktig med negativa formuleringar. Beskriv möjliga utmaningar som
situationsberoende hypoteser eller områden att utforska, inte som konstaterade
brister.

Knyt tolkningen till processens syfte och kontext när det finns stöd för det,
men undvik att överdriva kopplingen.

Använd ett naturligt och lättillgängligt språk som fungerar för en professionell
bedömnings- eller utvecklingssituation.
""".strip(),

            "en": """
Write the interpretation in a balanced, professional and
development-oriented way.

Help the user understand the candidate's most important behavioural
preferences without describing them as fixed characteristics.

Highlight both patterns that may be supportive and areas that may be useful
to explore further.

Be cautious with negative wording. Describe potential challenges as
situational hypotheses or areas to explore, rather than confirmed weaknesses.

Relate the interpretation to the process purpose and context where supported
by the evidence, without overstating the connection.

Use natural and accessible language suitable for a professional assessment
or development context.
""".strip(),

        },
    },
    "response_style_guidance": {
        "name": "Response styles",
        "category": "Personality",
        "description": (
            "Controls the psychometric interpretation guidance used "
            "when Talena explains response styles and how the personality "
            "profile should be approached."
        ),
        "defaults": {
            "sv": RESPONSE_STYLE_GUIDANCE_DEFAULT,
            "en": RESPONSE_STYLE_GUIDANCE_DEFAULT,
        },
    },
}


def normalize_prompt_language(
    language: str | None,
) -> str:
    """
    Normalize language codes used for editable AI prompts.

    Examples:
    sv-SE -> sv
    sv_SE -> sv
    en-GB -> en
    """

    normalized = (
        str(language or "sv")
        .strip()
        .lower()
        .replace("_", "-")
    )

    base_language = normalized.split(
        "-",
        1,
    )[0]

    if base_language in SUPPORTED_PROMPT_LANGUAGES:
        return base_language

    return "sv"


def get_ai_prompt_definition(
    key: str,
) -> dict[str, Any]:
    """
    Return the registry definition for one AI prompt.
    """

    try:
        return AI_PROMPT_REGISTRY[key]

    except KeyError as exc:
        raise KeyError(
            f"Unknown AI prompt key: {key}"
        ) from exc


def get_default_ai_prompt(
    *,
    key: str,
    language: str,
) -> str:
    """
    Return Talena's protected default business guidance.
    """

    language = normalize_prompt_language(
        language
    )

    definition = get_ai_prompt_definition(
        key
    )

    defaults = definition.get(
        "defaults",
        {},
    )

    default_prompt = (
        defaults.get(language)
        or defaults.get("en")
        or defaults.get("sv")
        or ""
    )

    return str(
        default_prompt
    ).strip()


def get_ai_prompt_instructions(
    *,
    key: str,
    language: str,
    default: str | None = None,
) -> str:
    """
    Return the currently active GLOBAL business guidance.

    Priority:

    1. Active global administrator override from AIPromptTemplate.
    2. Explicit fallback supplied by the caller, for backwards compatibility.
    3. Protected Talena default from AI_PROMPT_REGISTRY.

    Customer/company-specific prompts are intentionally not supported here.
    """

    from apps.processes.models import AIPromptTemplate

    normalized_language = normalize_prompt_language(
        language
    )

    if default is None:
        protected_default = get_default_ai_prompt(
            key=key,
            language=normalized_language,
        )

    else:
        protected_default = str(
            default
        ).strip()

    try:
        prompt_template = AIPromptTemplate.objects.get(
            key=key,
            language=normalized_language,
            is_active=True,
        )

    except ObjectDoesNotExist:
        return protected_default

    prompt_text = (
        prompt_template.prompt_text
        or ""
    ).strip()

    if not prompt_text:
        return protected_default

    return prompt_text


def list_ai_prompt_definitions() -> list[dict[str, Any]]:
    """
    Return all registered AI features in display order.

    This is used by Talena's admin UI so prompts appear even
    when no database override has ever been created.
    """

    result = []

    for key, definition in AI_PROMPT_REGISTRY.items():
        result.append(
            {
                "key": key,
                "name": definition.get(
                    "name",
                    key,
                ),
                "category": definition.get(
                    "category",
                    "",
                ),
                "description": definition.get(
                    "description",
                    "",
                ),
            }
        )

    return sorted(
        result,
        key=lambda item: (
            item["category"],
            item["name"],
        ),
    )