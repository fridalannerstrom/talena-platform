from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from apps.core.ai.cognitive_interpretation import extract_cognitive_results
from apps.core.ai.language import normalize_ai_language
from apps.core.ai.motivation_interpretation import (
    _owner_motivation_results,
    get_motivation_factor_display_name,
)
from apps.processes.services.cognitive_insights import (
    build_cognitive_insight_results,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
)
from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)
from apps.reports.libraries.personality.builder import get_score_band, normalize_sten

from .models import CandidateResultSnapshot


CANDIDATE_RESULT_CONTENT_VERSION = "candidate-static-v4"
_PERSONALITY_LIBRARY_DIR = (
    Path(__file__).parents[1]
    / "reports"
    / "libraries"
    / "personality"
)
with (_PERSONALITY_LIBRARY_DIR / "candidate_content_sv.json").open(
    encoding="utf-8"
) as _personality_library_file:
    CANDIDATE_PERSONALITY_CONTENT_SV = json.load(
        _personality_library_file
    )
with (_PERSONALITY_LIBRARY_DIR / "candidate_content_en.json").open(
    encoding="utf-8"
) as _personality_translation_file:
    CANDIDATE_PERSONALITY_CONTENT_EN = json.load(
        _personality_translation_file
    )

_CANDIDATE_PERSONALITY_TEXTS_EN = {
    indicator_key: dict(zip(
        CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"],
        sentences,
    ))
    for indicator_key, sentences in (
        CANDIDATE_PERSONALITY_CONTENT_EN["indicators"].items()
    )
}
_EXPECTED_PERSONALITY_INDICATORS = {
    indicator["key"]
    for trait in CANDIDATE_PERSONALITY_CONTENT_SV.get("traits", [])
    for indicator in trait.get("indicators", [])
}
_TRANSLATED_PERSONALITY_INDICATORS = set(
    CANDIDATE_PERSONALITY_CONTENT_EN.get("indicators", {})
)
_MISSING_PERSONALITY_TRANSLATIONS = (
    _EXPECTED_PERSONALITY_INDICATORS - _TRANSLATED_PERSONALITY_INDICATORS
)
_EXTRA_PERSONALITY_TRANSLATIONS = (
    _TRANSLATED_PERSONALITY_INDICATORS - _EXPECTED_PERSONALITY_INDICATORS
)
_INVALID_PERSONALITY_TRANSLATION_LENGTHS = {
    indicator_key: len(sentences)
    for indicator_key, sentences in (
        CANDIDATE_PERSONALITY_CONTENT_EN.get("indicators", {}).items()
    )
    if (
        len(sentences)
        != len(CANDIDATE_PERSONALITY_CONTENT_EN["score_bands"])
        or any(not str(sentence).strip() for sentence in sentences)
    )
}
if (
    _MISSING_PERSONALITY_TRANSLATIONS
    or _EXTRA_PERSONALITY_TRANSLATIONS
    or _INVALID_PERSONALITY_TRANSLATION_LENGTHS
    or CANDIDATE_PERSONALITY_CONTENT_EN.get("score_bands")
    != CANDIDATE_PERSONALITY_CONTENT_SV.get("score_bands")
):
    raise ValueError(
        "English candidate personality copy must provide exactly one "
        "translation for every source indicator and score band."
    )


_FIXED_COPY = {
    "sv": {
        "introduction_title": "Ditt resultat",
        "introduction_body": (
            "Resultatet beskriver möjliga preferenser och tendenser utifrån dina svar. "
            "Det är inte en absolut sanning eller ett betyg, utan ett underlag för en vidare dialog."
        ),
        "personality_title": "Personlighet",
        "skills_title": "Färdigheter",
        "motivation_title": "Motivation",
        "top_motivators_title": "Dina tre främsta drivkrafter",
    },
    "en": {
        "introduction_title": "Your result",
        "introduction_body": (
            "The result describes possible preferences and tendencies based on your responses. "
            "It is not an absolute truth or a grade, but a basis for further conversation."
        ),
        "personality_title": "Personality",
        "skills_title": "Skills",
        "motivation_title": "Motivation",
        "top_motivators_title": "Your Top 3 Motivators",
    },
}

_CANDIDATE_SKILL_ABILITIES = {
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

_CANDIDATE_SKILL_COPY = {
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

_CANDIDATE_MOTIVATION_COPY = {
    "sv": {
        "attachment": "Du värdesätter social kontakt i arbetet. Det verkar vara en viktig drivkraft för dig. Du trivs med känslan av att höra till ett team och uppskattar nära, goda arbetsrelationer.",
        "customer_service": "Du trivs sannolikt i en kundorienterad roll där du får hjälpa och stötta andra. Du tycker om att bygga relationer med kunder och förstå deras behov, och det motiverar dig att möta och gärna överträffa deras förväntningar.",
        "work_life_balance": "Du värdesätter en balans mellan arbete och privatliv som gör att du kan ta hand om dina åtaganden både på jobbet och utanför. Tydliga gränser kan hjälpa dig att koppla av efter arbetsdagen och ge tid åt annat som är viktigt för dig.",
        "people_development": "Du får energi av att hjälpa och stötta andra i deras utveckling. Du trivs med att vägleda människor genom utmaningar och uppmuntra dem att växa.",
        "stability": "Trygghet och stabilitet på jobbet verkar vara viktigt för dig. Du föredrar troligen en bransch eller organisation som känns stabil och en roll där du kan känna dig säker på din position.",
        "authority": "Du värdesätter möjligheten att ta ledande ansvar och utvecklas mot befordran. Du uppskattar roller där du får ange riktning, organisera arbetet och bidra till att det genomförs väl.",
        "acquisition": "Ekonomisk belöning verkar motivera dig. En välbetald roll och attraktiva löne- och förmånsnivåer kan ge dig möjlighet att göra sådant du värdesätter utan att behöva oroa dig för kostnader.",
        "independence": "Du värdesätter friheten att fatta egna beslut om hur du planerar din tid och organiserar ditt arbete. Du får goda förutsättningar när du får förtroende att sätta riktning och välja hur du genomför dina uppgifter.",
        "recognition": "Du motiveras av erkännande, beröm och uppskattning. Du uppskattar när ditt arbete och det värde du bidrar med blir synligt, och positiv återkoppling kan ge dig energi.",
        "making_a_difference": "Du vill gärna känna att ditt arbete gör positiv skillnad för andra. Det kan vara viktigt för dig att arbeta i en organisation med mål och syfte som känns meningsfulla och där du ser hur ditt arbete bidrar till samhället.",
        "achievement": "Du får energi av tydliga och utmanande mål. Professionella utmaningar och konkurrens kan motivera dig, särskilt när du får möjlighet att jämföra dina resultat med andra.",
        "quality": "Du motiveras av att leverera jämnt hög kvalitet. Du är stolt när ditt arbete håller vad du lovat och motsvarar förväntningarna, och du strävar efter att göra ett så genomarbetat arbete som möjligt.",
        "learning": "Du drivs av möjligheten att lära dig och utveckla din expertis. Du trivs sannolikt när du får tillgång till fortlöpande utbildning, utveckling och nya färdigheter att bemästra.",
        "ethics": "Du värdesätter höga etiska standarder, både hos dig själv och i organisationen. Du följer gärna riktlinjer och god praxis, känner stolthet över din professionella integritet och trivs när organisationens värderingar stämmer med dina egna.",
        "commercial_focus": "Du trivs sannolikt i en roll med kommersiellt fokus där du bidrar till organisationens ekonomiska resultat. Du får energi av att se sambandet mellan ditt arbete och verksamhetens framgång.",
        "curiosity": "Du drivs av att utforska och upptäcka nytt. Du söker kunskap och erfarenheter, tar gärna vara på möjligheter att möta nya perspektiv och fördjupar dig i sådant som fångar ditt intresse.",
        "creativity": "Du uppskattar att använda din kreativitet, tänka i nya banor och hitta lösningar. Du bidrar gärna med idéer som både är nyskapande och användbara.",
        "enjoyment": "Du värdesätter en arbetsmiljö där du trivs och kan ha roligt med kollegorna. Du uppskattar en lättsam stämning där du kan visa din lekfulla sida, dela humor och känna dig accepterad som du är.",
        "variety": "Du motiveras av variation och möjligheten att arbeta med olika saker. Du trivs sannolikt med en mångsidig roll där du växlar mellan uppgifter och projekt och får använda flera av dina färdigheter.",
        "risk": "Du motiveras av att möta situationer där utfallet är osäkert. Du är bekväm med att fatta riskfyllda beslut och trivs sannolikt i roller där det finns utrymme att ta initiativ och se vad det leder till.",
    },
    "en": {
        "attachment": "You value social interaction at work. It seems to be an important source of motivation for you. You enjoy feeling part of a team and building close, positive working relationships.",
        "customer_service": "You are likely to enjoy a customer-focused role where you can help and support others. You value building relationships with customers and understanding their needs, and you are motivated by meeting and exceeding their expectations.",
        "work_life_balance": "You value a balance between work and life outside work that lets you meet your commitments in both. Clear boundaries can help you switch off at the end of the workday and make time for other things that matter to you.",
        "people_development": "You get energy from helping and supporting others as they develop. You enjoy guiding people through challenges and encouraging them to grow.",
        "stability": "Feeling secure and having stability at work seem important to you. You are likely to prefer an industry or organisation that feels stable and a role where you can feel secure in your position.",
        "authority": "You value opportunities to take on leadership responsibility and progress in your career. You appreciate roles where you can set direction, organise work and help ensure it is done well.",
        "acquisition": "Financial reward seems to motivate you. A well-paid role and attractive salary and benefits can help you afford the things you value without worrying about costs.",
        "independence": "You value the freedom to make your own decisions about how you plan your time and organise your work. You are likely to do your best when you are trusted to set direction and decide how to complete your tasks.",
        "recognition": "Recognition, praise and appreciation motivate you. You value it when your work and contribution are visible, and positive feedback can give you energy.",
        "making_a_difference": "You want to feel that your work makes a positive difference to others. It may be important to you to work for an organisation with meaningful goals and to see how your work can benefit society.",
        "achievement": "You get energy from clear, challenging goals. Professional challenges and competition can motivate you, especially when you have the opportunity to compare your results with others.",
        "quality": "You are motivated by consistently delivering high-quality work. You take pride in meeting your commitments and expectations, and you aim to produce work that is as thorough as possible.",
        "learning": "You are driven by opportunities to learn and develop your expertise. You are likely to enjoy an environment with ongoing training, development and new skills to master.",
        "ethics": "You value high ethical standards in yourself and in the organisation. You take pride in your professional integrity, follow guidelines and good practice, and enjoy working where the organisation's values align with your own.",
        "commercial_focus": "You are likely to enjoy a commercially focused role where you contribute to the organisation's financial results. You get energy from seeing the connection between your work and the organisation's success.",
        "curiosity": "You are driven to explore and discover new things. You seek knowledge and experience, welcome opportunities for new perspectives and explore what captures your interest.",
        "creativity": "You enjoy using your creativity, thinking in new ways and finding solutions. You like contributing ideas that are both original and useful.",
        "enjoyment": "You value a work environment where you enjoy your work and have fun with colleagues. You appreciate an easy-going atmosphere where you can express your playful side, share humour and feel accepted as you are.",
        "variety": "You are motivated by variety and the opportunity to work on different things. You are likely to enjoy a diverse role with a mix of tasks and projects that lets you use several of your skills.",
        "risk": "You are motivated by facing situations where the outcome is uncertain. You are comfortable making risky decisions and are likely to enjoy roles that give you room to take a chance and see what happens.",
    },
}


def _normalise_name(value: Any) -> str:
    value = str(value or "").strip().casefold().replace("&", "and")
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()


def _personality_indicator_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for indicator_key, content in INDICATOR_PROFILE_CONTENT.items():
        for alias in (
            indicator_key,
            content.get("label_sv"),
            content.get("label_en"),
        ):
            normalized = _normalise_name(alias)
            if normalized:
                lookup[normalized] = indicator_key
    return lookup


_PERSONALITY_INDICATOR_LOOKUP = _personality_indicator_lookup()


def _personality_results(invitation) -> dict[str, int]:
    """Return available personality indicator STEN values by library key."""
    results: dict[str, int] = {}
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        activity_name = _normalise_name(activity.get("activity"))
        if not any(
            marker in activity_name
            for marker in ("personality", "personality questionnaire", "personlighet", "trait")
        ):
            continue

        for competency in activity.get("competencies") or []:
            if not isinstance(competency, dict):
                continue
            competency_name = competency.get("competency") or competency.get("name")
            key = _PERSONALITY_INDICATOR_LOOKUP.get(_normalise_name(competency_name))
            if not key:
                continue

            sten = normalize_sten(competency.get("sten_rounded"))
            if sten is None:
                sten = normalize_sten(competency.get("sten"))
            if sten is not None:
                results[key] = sten
    return results


def _candidate_personality_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    scores = _personality_results(invitation)
    if not scores:
        return []

    workbook_traits = {
        trait["key"]: trait
        for trait in CANDIDATE_PERSONALITY_CONTENT_SV.get("traits", [])
    }
    section_titles = {
        "sv": {
            "leading_and_working_with_others": "Leda och arbeta med andra",
            "organisation_and_thinking_style": "Organisering och tankemönster",
            "interacting_and_managing_emotions": "Interaktion och känslohantering",
        },
        "en": {
            "leading_and_working_with_others": "Leading and Working with Others",
            "organisation_and_thinking_style": "Organising and Thought Patterns",
            "interacting_and_managing_emotions": "Interaction and Emotional Regulation",
        },
    }
    groups = []
    for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
        sentences = []
        for trait_definition in section["traits"]:
            trait_key = trait_definition["trait_name"]
            workbook_trait = workbook_traits.get(trait_key, {})
            indicator_definitions = {
                item["key"]: item
                for item in workbook_trait.get("indicators", [])
            }

            for indicator_key in trait_definition.get("indicators", []):
                sten = scores.get(indicator_key)
                score_band = get_score_band(sten)
                if score_band is None:
                    continue

                if language_code == "sv":
                    candidate_text = indicator_definitions.get(
                        indicator_key,
                        {},
                    )
                    text = candidate_text.get(
                        "score_texts",
                        {},
                    ).get(score_band, "")
                else:
                    text = _CANDIDATE_PERSONALITY_TEXTS_EN.get(
                        indicator_key,
                        {},
                    ).get(score_band, "")

                if text and text.strip():
                    sentences.append(text.strip())

        if not sentences:
            continue

        title = (
            section_titles[language_code].get(section["section_key"])
            or section["section_name"]
        )
        groups.append({
            "title": title,
            "body": " ".join(sentences),
        })
    return groups


def _candidate_skills_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    cognitive_results = extract_cognitive_results(invitation)
    percentiles = {}
    for result in cognitive_results:
        percentiles.setdefault(result["key"], result["percentile"])

    # Some Sova payloads label the activity generically (for example,
    # "Skills") while naming the actual ability in each competency.
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        activity_name = _normalise_name(activity.get("activity"))
        for competency in activity.get("competencies") or []:
            if not isinstance(competency, dict):
                continue
            competency_name = _normalise_name(
                competency.get("competency") or competency.get("name")
            )
            source_name = f"{activity_name} {competency_name}"
            key = next(
                (
                    result_key
                    for result_key, keywords in (
                        ("logical", ("logical", "logisk")),
                        ("numerical", ("numerical", "numeric", "numerisk")),
                        ("verbal", ("verbal",)),
                    )
                    if any(keyword in source_name for keyword in keywords)
                ),
                None,
            )
            percentile = competency.get("percentile")
            if key and percentile is not None:
                percentiles.setdefault(key, percentile)

    if not percentiles:
        return []

    localised_results = build_cognitive_insight_results(
        verbal_percentile=percentiles.get("verbal"),
        logical_percentile=percentiles.get("logical"),
        numerical_percentile=percentiles.get("numerical"),
        language_code=language_code,
    )
    groups = []
    for localized in localised_results:
        if not localized.get("completed"):
            continue
        key = localized["key"]
        ability = _CANDIDATE_SKILL_ABILITIES[language_code].get(key)
        template = _CANDIDATE_SKILL_COPY[language_code].get(
            localized.get("level_key")
        )
        if not ability or not template:
            continue
        interpretation = template.format(ability=ability)
        groups.append(
            {
                "title": localized.get("title") or key,
                "items": [{"label": "", "text": interpretation}],
            }
        )
    return groups


def _candidate_motivation_groups(
    invitation,
    *,
    language_code: str,
) -> list[dict[str, Any]]:
    results = sorted(
        _owner_motivation_results(invitation),
        key=lambda item: (-float(item["score"]), item["key"]),
    )[:3]

    items = []
    for result in results:
        key = result["key"]
        text = _CANDIDATE_MOTIVATION_COPY.get(language_code, {}).get(key, "")
        if not text:
            continue

        label = get_motivation_factor_display_name(
            result.get("name") or key,
            language_code=language_code,
        )
        items.append({"label": label, "text": text})

    if not items:
        return []
    return [{
        "title": _FIXED_COPY[language_code]["top_motivators_title"],
        "items": items,
    }]


def _area_content(title: str, groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not groups:
        return None
    return {"title": title, "body": "", "points": [], "groups": groups}


def build_static_candidate_result_content(
    invitation,
    *,
    language_code: str = "sv",
) -> dict[str, Any]:
    """Build the candidate report from approved static libraries only."""
    language_code = normalize_ai_language(language_code)
    language_code = language_code if language_code in {"sv", "en"} else "sv"
    copy = _FIXED_COPY[language_code]

    content: dict[str, Any] = {
    "library_version": CANDIDATE_RESULT_CONTENT_VERSION,
        "personality_library_version": (
            f'{CANDIDATE_PERSONALITY_CONTENT_SV.get("library_version", "")}/'
            f'{CANDIDATE_PERSONALITY_CONTENT_EN.get("library_version", "")}'
        ),
        "introduction": {
            "title": copy["introduction_title"],
            "body": copy["introduction_body"],
        },
        "personality": _area_content(
            copy["personality_title"],
            _candidate_personality_groups(
                invitation,
                language_code=language_code,
            ),
        ),
        "skills": _area_content(
            copy["skills_title"],
            _candidate_skills_groups(
                invitation,
                language_code=language_code,
            ),
        ),
        "motivation": _area_content(
            copy["motivation_title"],
            _candidate_motivation_groups(
                invitation,
                language_code=language_code,
            ),
        ),
    }
    return {key: value for key, value in content.items() if value is not None}


def generate_candidate_result_content(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Compatibility entry point that now returns static content, never AI text."""
    content = build_static_candidate_result_content(
        invitation,
        language_code=language_code,
    )
    source_fingerprint = hashlib.sha256(
        json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    library_metadata = {
        "content_version": CANDIDATE_RESULT_CONTENT_VERSION,
        "personality_library_version": content.get("personality_library_version", ""),
        "locale": normalize_ai_language(language_code),
    }
    return content, library_metadata, source_fingerprint


def ensure_candidate_result_snapshot_current(
    snapshot: CandidateResultSnapshot | None,
) -> tuple[CandidateResultSnapshot | None, bool]:
    """Refresh changed static copy or replace a legacy AI snapshot."""
    if snapshot is None:
        return None, False
    if snapshot.content_version == CANDIDATE_RESULT_CONTENT_VERSION:
        return snapshot, False

    content, _library_metadata, fingerprint = generate_candidate_result_content(
        snapshot.invitation,
        language_code=snapshot.locale,
    )

    old_content = snapshot.content if isinstance(snapshot.content, dict) else {}
    old_prompt_versions = (
        snapshot.prompt_versions
        if isinstance(snapshot.prompt_versions, dict)
        else {}
    )

    updated = CandidateResultSnapshot.objects.filter(
        pk=snapshot.pk,
    ).exclude(
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
    ).update(
        content=content,
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
        legacy_content=snapshot.legacy_content or old_content,
        legacy_prompt_versions=(
            snapshot.legacy_prompt_versions or old_prompt_versions
        ),
        prompt_versions={},
        source_fingerprint=fingerprint,
    )
    snapshot.refresh_from_db()
    return snapshot, bool(updated)


def create_candidate_result_snapshot(
    invitation,
    *,
    language_code: str = "sv",
) -> tuple[CandidateResultSnapshot, bool]:
    """Create a static snapshot, or safely upgrade an earlier AI snapshot."""
    if not invitation.process.candidate_results_enabled:
        raise ValueError("Candidate results are not enabled for this process.")
    if invitation.status != "completed":
        raise ValueError("Candidate result snapshots require a completed invitation.")

    existing = CandidateResultSnapshot.objects.filter(invitation=invitation).first()
    if existing:
        current, upgraded = ensure_candidate_result_snapshot_current(existing)
        return current, upgraded

    content, _library_metadata, source_fingerprint = generate_candidate_result_content(
        invitation,
        language_code=language_code,
    )
    snapshot = CandidateResultSnapshot.objects.create(
        invitation=invitation,
        candidate=invitation.candidate,
        process=invitation.process,
        locale=normalize_ai_language(language_code),
        content=content,
        content_version=CANDIDATE_RESULT_CONTENT_VERSION,
        prompt_versions={},
        source_fingerprint=source_fingerprint,
    )
    return snapshot, True
