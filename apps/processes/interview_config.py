from __future__ import annotations


INTERVIEW_SECTION_DEFAULTS = {
    "cognitive": {
        "order": 1,
        "question_count": 3,
        "estimated_minutes": 10,
        "copy": {
            "en": {
                "guidance_label": "How to use these questions",
                "guidance": (
                    "Use these questions to explore how the candidate works with "
                    "information, complexity and problem solving in practice. Ask for "
                    "concrete examples of working methods, priorities and how the "
                    "person checks their work. Treat the assessment result as an "
                    "indication from the test situation, not as a measure of the "
                    "candidate's overall ability or competence."
                ),
                "transition_label": "Suggested transition",
                "transition": (
                    "I'd like to spend a few minutes on how you approach information "
                    "and problem solving in practice. I'll ask for a few concrete "
                    "examples from your experience."
                ),
            },
            "sv": {
                "guidance_label": "Så använder du frågorna",
                "guidance": (
                    "Använd frågorna för att utforska hur kandidaten arbetar med "
                    "information, komplexitet och problemlösning i praktiken. Be om "
                    "konkreta exempel på arbetssätt, prioriteringar och hur personen "
                    "kontrollerar sitt arbete. Se testresultatet som en indikation "
                    "från testsituationen, inte som ett mått på kandidatens samlade "
                    "förmåga eller kompetens."
                ),
                "transition_label": "Förslag på övergång",
                "transition": (
                    "Nu skulle jag vilja prata lite om hur du tar dig an information "
                    "och problemlösning i praktiken. Jag kommer att be om några "
                    "konkreta exempel från din erfarenhet."
                ),
            },
        },
    },
    "motivation": {
        "order": 2,
        "question_count": 3,
        "estimated_minutes": 10,
        "copy": {
            "en": {
                "guidance_label": "How to use these questions",
                "guidance": (
                    "Use these questions to understand what may create energy and "
                    "engagement, what may reduce motivation and how different drivers "
                    "are balanced in practice. Ask for concrete situations and avoid "
                    "treating higher or lower results as inherently good or bad."
                ),
                "transition_label": "Suggested transition",
                "transition": (
                    "I'd like to talk a little about what tends to give you energy "
                    "and engagement at work, and what can affect your motivation. "
                    "I'll ask for a few concrete examples."
                ),
            },
            "sv": {
                "guidance_label": "Så använder du frågorna",
                "guidance": (
                    "Använd frågorna för att förstå vad som kan skapa energi och "
                    "engagemang, vad som kan minska motivationen och hur olika "
                    "drivkrafter balanseras i praktiken. Be om konkreta situationer "
                    "och undvik att tolka högre eller lägre resultat som bra eller "
                    "dåliga i sig."
                ),
                "transition_label": "Förslag på övergång",
                "transition": (
                    "Nu skulle jag vilja prata lite om vad som brukar ge dig energi "
                    "och engagemang i arbetet, och vad som kan påverka din motivation. "
                    "Jag kommer att be om några konkreta exempel."
                ),
            },
        },
    },
    "personality": {
        "order": 3,
        "question_count": 8,
        "estimated_minutes": 20,
        "copy": {
            "en": {
                "guidance_label": "How to use these questions",
                "guidance": (
                    "Use these questions to explore how the candidate's personality "
                    "preferences appear in real situations. Ask for concrete examples "
                    "of what the person did, how they adapted and what the outcome was. "
                    "Treat the assessment result as a hypothesis to explore, not as "
                    "proof of behaviour or competence."
                ),
                "transition_label": "Suggested transition",
                "transition": (
                    "I'd like to talk a little about how you tend to act in different "
                    "work situations. I'll ask for concrete examples, and there are no "
                    "right or wrong ways to be."
                ),
            },
            "sv": {
                "guidance_label": "Så använder du frågorna",
                "guidance": (
                    "Använd frågorna för att utforska hur kandidatens "
                    "personlighetsmässiga preferenser visar sig i verkliga situationer. "
                    "Be om konkreta exempel på vad personen gjorde, hur hen anpassade "
                    "sig och vad resultatet blev. Se testresultatet som en hypotes att "
                    "utforska, inte som bevis på beteende eller kompetens."
                ),
                "transition_label": "Förslag på övergång",
                "transition": (
                    "Nu skulle jag vilja prata lite om hur du brukar agera i olika "
                    "arbetssituationer. Jag kommer att be om konkreta exempel, och det "
                    "finns inga rätt eller fel sätt att vara."
                ),
            },
        },
    },
}


def _normalise_language_code(language_code: str | None) -> str:
    normalised = str(language_code or "en").strip().lower()
    normalised = normalised.replace("_", "-").split("-", 1)[0]
    return "sv" if normalised == "sv" else "en"


def get_interview_section_config(
    key: str,
    language_code: str | None = None,
) -> dict:
    normalised_key = str(key or "").strip().lower()

    config = INTERVIEW_SECTION_DEFAULTS.get(
        normalised_key,
        {},
    )

    language = _normalise_language_code(language_code)
    copy_by_language = config.get("copy") or {}
    section_copy = copy_by_language.get(language) or copy_by_language.get("en") or {}

    return {
        "key": normalised_key,
        "order": int(config.get("order", 99)),
        "question_count": int(
            config.get("question_count", 0)
        ),
        "estimated_minutes": int(
            config.get("estimated_minutes", 0)
        ),
        "guidance_label": str(section_copy.get("guidance_label") or ""),
        "guidance": str(section_copy.get("guidance") or ""),
        "transition_label": str(section_copy.get("transition_label") or ""),
        "transition": str(section_copy.get("transition") or ""),
    }
