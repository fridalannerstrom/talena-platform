"""Approved localized static copy used by candidate result reports."""

CANDIDATE_SKILL_COPY_VERSION = "candidate-skills-v1"

CANDIDATE_SKILL_ABILITIES = {
    "sv": {
        "logical": "se mönster och dra logiska slutsatser",
        "numerical": "förstå och arbeta med numerisk information",
        "verbal": "förstå och utvärdera skriftlig information",
    },
    "en": {
        "logical": "identify patterns and reach logical conclusions",
        "numerical": "understand and work with numerical information",
        "verbal": "understand and evaluate written information",
    },
}

CANDIDATE_SKILL_COPY = {
    "sv": {
        "very-low": "Du kan uppleva det som betydligt svårare än för de flesta i referensgruppen att {ability}.",
        "low": "Du kan uppleva det som svårare än för många andra i referensgruppen att {ability}.",
        "average": "Du kan förvänta dig att det är ungefär lika lätt för dig som för de flesta i referensgruppen att {ability}.",
        "high": "Du kan ha lättare än många andra i referensgruppen att {ability}.",
        "very-high": "Du kan ha betydligt lättare än de flesta i referensgruppen att {ability}.",
    },
    "en": {
        "very-low": "You may find it considerably more difficult than most people in the reference group to {ability}.",
        "low": "You may find it more difficult than many others in the reference group to {ability}.",
        "average": "You are likely to find it about as easy as most people in the reference group to {ability}.",
        "high": "You may find it easier than many others in the reference group to {ability}.",
        "very-high": "You may find it considerably easier than most people in the reference group to {ability}.",
    },
}

CANDIDATE_SKILL_TITLES = {
    "sv": {
        "logical": "Logiskt resonemang",
        "numerical": "Numeriskt resonemang",
        "verbal": "Verbalt resonemang",
    },
    "en": {
        "logical": "Logical reasoning",
        "numerical": "Numerical reasoning",
        "verbal": "Verbal reasoning",
    },
}

CANDIDATE_COGNITIVE_REPORT_COPY = {
    "sv": {
        "title": "Kandidatrapport",
        "intro": "Resultatet ger en bild av hur du kan uppleva uppgifter som rör den här typen av information.",
        "test_description": "Testet undersöker din förmåga att {ability}. Texten nedan beskriver hur du kan uppleva uppgifter av den här typen.",
    },
    "en": {
        "title": "Candidate Report",
        "intro": "This result gives an indication of how you may experience tasks involving this type of information.",
        "test_description": "The assessment looks at your ability to {ability}. The text below describes how you may experience tasks of this kind.",
    },
}


def candidate_cognitive_level_key(percentile):
    """Map a completed cognitive percentile to the approved five text bands."""
    if percentile is None:
        return None
    try:
        percentile = int(round(float(percentile)))
    except (TypeError, ValueError):
        return None
    percentile = max(0, min(100, percentile))
    if percentile <= 9:
        return "very-low"
    if percentile <= 24:
        return "low"
    if percentile <= 74:
        return "average"
    if percentile <= 90:
        return "high"
    return "very-high"


def resolve_candidate_skill_text(test_key, percentile, language_code="sv"):
    """Return the localized static candidate interpretation for one result."""
    locale = str(language_code or "sv").lower()[:2]
    if locale not in {"sv", "en"}:
        locale = "sv"

    ability = CANDIDATE_SKILL_ABILITIES.get(locale, {}).get(test_key)
    level_key = candidate_cognitive_level_key(percentile)
    template = CANDIDATE_SKILL_COPY.get(locale, {}).get(level_key)
    if not ability or not template:
        return ""
    return template.format(ability=ability)
