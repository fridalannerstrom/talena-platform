from __future__ import annotations

import re
from functools import wraps
from typing import Any


_INSTALLED = False


def _situational_sten_band(value: Any) -> str:
    """Map personality STEN 4-7 to the product term 'situational'."""

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown"

    if score <= 3:
        return "low"
    if score >= 8:
        return "high"
    return "situational"


def _situational_sten_direction(value: Any) -> str:
    """Describe score direction without introducing middle/range language."""

    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return "unknown direction"

    if score <= 3:
        return "clearer low-side indication"
    if score >= 8:
        return "clearer high-side indication"
    return "situational behavioural pattern"


def _normalise_legacy_prompt_language(prompt: str) -> str:
    """
    Remove positive legacy descriptions of STEN 4-7 from the final runtime
    personality-question prompt without changing administrator prohibitions.
    """

    text = str(prompt or "")

    replacements = {
        (
            "STEN 4 till 7\n"
            "- kan indikera en mer mellanhög eller situationsberoende preferens"
        ): (
            "STEN 4 till 7\n"
            "- ska tolkas som ett situationsbaserat beteendemönster"
        ),
        (
            "Mellanhöga resultat kan ibland indikera moderation, flexibilitet\n"
            "eller större situationsberoende."
        ): (
            "Resultat 4 till 7 ska behandlas som situationsbaserade. Olika "
            "arbetssätt kan framträda beroende på situation, krav och sammanhang."
        ),
        (
            "STEN 4 to 7\n"
            "- may indicate a more mid-range or situational preference"
        ): (
            "STEN 4 to 7\n"
            "- should be interpreted as a situational behavioural pattern"
        ),
        (
            "Mid-range results may sometimes indicate moderation, flexibility\n"
            "or greater context dependence."
        ): (
            "STEN 4 to 7 results should be treated as situational. Different "
            "approaches may emerge depending on the situation, demands and context."
        ),
        "- STEN 4 till 7: typiskt eller måttligt": (
            "- STEN 4 till 7: situationsbaserat"
        ),
        "- STEN 4 to 7: typical or moderate": (
            "- STEN 4 to 7: situational"
        ),
        "more mid-range indication": "situational behavioural pattern",
        "a mid-range indication": "a situational behavioural pattern",
        "mid-range or situational patterns": "situational patterns",
        "(mid-range)": "(situational)",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def _normalise_visible_why_language(value: Any) -> str:
    """
    Final user-facing guard for the personality-question why field.

    The prompt should already produce the desired wording. This function only
    catches legacy level-language if a model or fallback still emits it.
    """

    text = str(value or "").strip()
    if not text:
        return ""

    phrase_replacements = (
        (
            r"ligger\s+närmare\s+mitten\s+av\s+kandidatens\s+profil",
            "visar ett mer situationsbaserat beteendemönster",
        ),
        (
            r"ligger\s+i\s+mitten",
            "är situationsbaserat",
        ),
        (
            r"resultat\s+nära\s+mitten",
            "situationsbaserat beteendemönster",
        ),
        (
            r"varken\s+hög\s+eller\s+låg",
            "situationsbaserat",
        ),
        (
            r"på\s+en\s+medelnivå",
            "situationsbaserat",
        ),
        (
            r"medelindikator",
            "situationsbaserat beteendemönster",
        ),
        (
            r"medelstor\s+preferens",
            "situationsbaserat beteendemönster",
        ),
        (
            r"medelnivå",
            "situationsbaserat beteende",
        ),
        (
            r"mellanhög(?:t|a)?",
            "situationsbaserat",
        ),
        (
            r"sits?\s+closer\s+to\s+the\s+middle\s+of\s+the\s+candidate'?s\s+profile",
            "shows a more situational behavioural pattern",
        ),
        (
            r"closer\s+to\s+the\s+middle",
            "more situational",
        ),
        (
            r"results?\s+near\s+the\s+middle",
            "situational behavioural pattern",
        ),
        (
            r"neither\s+high\s+nor\s+low",
            "situational",
        ),
        (
            r"mid[- ]range\s+indication",
            "situational behavioural pattern",
        ),
        (
            r"mid[- ]range\s+results?",
            "situational behavioural pattern",
        ),
        (
            r"mid[- ]range",
            "situational",
        ),
    )

    for pattern, replacement in phrase_replacements:
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )

    return text


def _situational_fallback_why(*, trait: str, language_code: str) -> str:
    if str(language_code or "").lower().startswith("sv"):
        return (
            "Beteendet verkar mer situationsbaserat. Det gör det relevant att "
            "förstå vad som påverkar vilket arbetssätt kandidaten använder i "
            "olika situationer och krav."
        )

    return (
        "The behaviour appears more situational. This makes it relevant to "
        "understand what influences which approach the candidate uses across "
        "different situations and demands."
    )


def install_personality_question_situational_language_policy() -> None:
    """Make 'situational' the only 4-7 level concept in personality questions."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import candidate_question_grounding_policy as grounding
    from apps.core.ai import personality_question_precision_policy as precision
    from apps.core.ai import personality_questions

    # These helpers feed candidate evidence into the runtime prompt. Keep 4-7
    # semantically situational before the model ever sees the evidence.
    grounding._sten_band = _situational_sten_band
    precision._sten_direction = _situational_sten_direction

    original_fallback = grounding._trait_fallback_text

    @wraps(original_fallback)
    def trait_fallback_text(*, trait: str, band: str, language_code: str, index: int):
        question, why, listen_for = original_fallback(
            trait=trait,
            band=band,
            language_code=language_code,
            index=index,
        )

        if str(band or "").casefold() in {"mid-range", "situational"}:
            why = _situational_fallback_why(
                trait=trait,
                language_code=language_code,
            )

        return (
            question,
            _normalise_visible_why_language(why),
            listen_for,
        )

    grounding._trait_fallback_text = trait_fallback_text

    # Run after all other personality-question prompt policies. Only known
    # positive legacy interpretations are replaced, so admin text saying
    # "never use mid-range" remains intact as a prohibition.
    original_prompt = personality_questions.build_personality_questions_prompt

    @wraps(original_prompt)
    def personality_prompt(
        invitation,
        personality_results,
        *,
        language_code=None,
    ):
        prompt = original_prompt(
            invitation,
            personality_results,
            language_code=language_code,
        )
        return _normalise_legacy_prompt_language(prompt)

    personality_questions.build_personality_questions_prompt = personality_prompt

    if hasattr(personality_questions, "_build_personality_questions_repair_prompt"):
        original_repair = personality_questions._build_personality_questions_repair_prompt

        @wraps(original_repair)
        def personality_repair(*args, **kwargs):
            return _normalise_legacy_prompt_language(
                original_repair(*args, **kwargs)
            )

        personality_questions._build_personality_questions_repair_prompt = (
            personality_repair
        )

    # User-facing safety net. The output contract remains unchanged, but the
    # visible why text can never reintroduce the legacy 4-7 level wording.
    original_normalise_questions = personality_questions._normalise_personality_questions

    @wraps(original_normalise_questions)
    def normalise_personality_questions(items, selected_traits):
        questions = original_normalise_questions(
            items,
            selected_traits,
        )

        for item in questions:
            item["why"] = _normalise_visible_why_language(
                item.get("why")
            )

        return questions

    personality_questions._normalise_personality_questions = (
        normalise_personality_questions
    )

    _INSTALLED = True
