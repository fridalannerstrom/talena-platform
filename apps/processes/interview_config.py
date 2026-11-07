from __future__ import annotations


# #437: Interviewer-facing content. These texts are not part of an AI prompt.
COMMON_INTERVIEW_GUIDANCE = {
    "sv": (
        "De AI-genererade frågorna är tänkta som inspiration och stöd inför intervjun. "
        "Utgå från din kunskap om rollen och bedöm vilka frågor som är relevanta, "
        "vilka som behöver justeras eller tas bort och om något behöver kompletteras."
    ),
    "en": (
        "The AI-generated questions are intended as inspiration and support "
        "when preparing for the interview. Use your understanding of the role "
        "to decide which questions are relevant, which need adjusting or removing, "
        "and whether anything should be added."
    ),
}

INTERVIEW_AREA_COPY = {
    "cognitive": {
        "sv": {
            "area_label": "Färdighet",
            "area_description": "Utforska hur färdighetsresultaten kan relateras till praktiska krav och arbetssätt.",
            "questions_label": "Tips på färdighetsfrågor",
            "intro_questions": (
                "Har du gjort något liknande test innan?",
                "Är det något typ av test du brukar ha lättare för?",
                "Hur upplevde du det här testet?",
            ),
            "comparison_question": "Kändes något lättare än det andra?",
        },
        "en": {
            "area_label": "Skills",
            "area_description": "Explore how skills assessment results relate to practical demands and working methods.",
            "questions_label": "Suggested skills questions",
            "intro_questions": (
                "Have you taken a similar test before?",
                "Are there any types of tests you usually find easier?",
                "How did you experience this test?",
            ),
            "comparison_question": "Did you find one of the tests easier than the others?",
        },
    },
    "motivation": {
        "sv": {
            "area_label": "Motivation",
            "area_description": "Utforska vad som kan skapa energi, engagemang och hållbar motivation.",
            "questions_label": "Tips på motivationsfrågor",
            "intro_questions": (
                "Hur kändes det att svara på formuläret - var det lätt eller svårt att ta ställning?",
            ),
        },
        "en": {
            "area_label": "Motivation",
            "area_description": "Explore what may create energy, engagement and sustainable motivation.",
            "questions_label": "Suggested motivation questions",
            "intro_questions": (
                "How did it feel to complete the questionnaire - was it easy or difficult to make a choice?",
            ),
        },
    },
    "personality": {
        "sv": {
            "area_label": "Personlighet",
            "area_description": "Utforska hur personlighetspreferenser visar sig i praktiska situationer.",
            "questions_label": "Tips på personlighetsfrågor",
            "intro_questions": (
                "Hur kändes det att svara på formuläret - var det lätt eller svårt att ta ställning?",
            ),
        },
        "en": {
            "area_label": "Personality",
            "area_description": "Explore how relevant personality preferences appear in practical situations.",
            "questions_label": "Suggested personality questions",
            "intro_questions": (
                "How did it feel to complete the questionnaire - was it easy or difficult to make a choice?",
            ),
        },
    },
}

INTRO_QUESTIONS_LABEL = {
    "sv": "Inledande frågor",
    "en": "Opening questions",
}

_COMPLETED_STATUSES = {
    "completed", "complete", "finished", "done", "result available", "result_available",
}
_RESULT_FIELDS = ("score", "stive", "stive_rounded", "sten", "sten_rounded", "percentile")
_COGNITIVE_ALIASES = {
    "logical": ("logical", "logisk"),
    "numerical": ("numerical", "numeric", "numerisk"),
    "verbal": ("verbal",),
}


def _completed_interview_areas(owner) -> tuple[set[str], set[str]]:
    """Use actual Sova result evidence; never count tests merely sent or started."""
    areas: set[str] = set()
    completed_cognitive: set[str] = set()
    for activity in (getattr(owner, "sova_activities", None) or []):
        if not isinstance(activity, dict):
            continue
        name = str(activity.get("activity") or "").strip().lower()
        status = str(activity.get("status") or "").strip().lower()
        if status and status not in _COMPLETED_STATUSES:
            continue
        competencies = activity.get("competencies") or []
        if not isinstance(competencies, list) or not any(
            isinstance(comp, dict) and any(comp.get(field) is not None for field in _RESULT_FIELDS)
            for comp in competencies
        ):
            continue
        if "personality" in name:
            areas.add("personality")
        if "motivation" in name:
            areas.add("motivation")
        if any(isinstance(comp, dict) and comp.get("percentile") is not None for comp in competencies):
            for key, aliases in _COGNITIVE_ALIASES.items():
                if any(alias in name for alias in aliases):
                    completed_cognitive.add(key)
                    areas.add("cognitive")
                    break
    return areas, completed_cognitive


def get_available_interview_areas(owner) -> set[str]:
    return _completed_interview_areas(owner)[0]


def get_completed_cognitive_test_keys(owner) -> set[str]:
    return _completed_interview_areas(owner)[1]


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
                    "I'd like to remind you that this skills assessment is just one "
                    "small part of the overall picture. These tests capture performance "
                    "at a particular moment, and your experience in the area also carries "
                    "significant weight. I'd now like to talk about how you approach "
                    "information and problem solving in practice. I'll ask for some "
                    "concrete examples from your experience."
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
                    "Vill påminna om att färdighetstestet är en liten pusselbit av en helhet. "
                    "Dessa färdighetstester är en ögonblicksbild och din erfarenhet inom området "
                    "väger också tungt. Därför skulle jag nu vilja prata om hur du tar dig an "
                    "information och problemlösning i praktiken. Jag kommer att be om några "
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
    *,
    completed_cognitive_tests: int = 0,
) -> dict:
    normalised_key = str(key or "").strip().lower()

    config = INTERVIEW_SECTION_DEFAULTS.get(
        normalised_key,
        {},
    )

    language = _normalise_language_code(language_code)
    copy_by_language = config.get("copy") or {}
    section_copy = copy_by_language.get(language) or copy_by_language.get("en") or {}
    area_copy = (INTERVIEW_AREA_COPY.get(normalised_key) or {}).get(language) or {}
    opening_questions = list(area_copy.get("intro_questions") or ())
    if normalised_key == "cognitive" and completed_cognitive_tests >= 2:
        opening_questions.append(area_copy["comparison_question"])

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
        "common_guidance": COMMON_INTERVIEW_GUIDANCE[language],
        "guidance": str(section_copy.get("guidance") or ""),
        "area_label": str(area_copy.get("area_label") or ""),
        "area_description": str(area_copy.get("area_description") or ""),
        "questions_label": str(area_copy.get("questions_label") or ""),
        "intro_questions_label": INTRO_QUESTIONS_LABEL[language],
        "intro_questions": opening_questions,
        "transition_label": str(section_copy.get("transition_label") or ""),
        "transition": str(section_copy.get("transition") or ""),
    }
