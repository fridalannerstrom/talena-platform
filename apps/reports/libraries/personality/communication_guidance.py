"""Approved, deterministic profile and social-desirability guidance."""

from __future__ import annotations

import math
import re
from typing import Any

from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)


PROFILE_MIDDLE_THRESHOLD = 10
PROFILE_CLEAR_THRESHOLD = 9
MINIMUM_EXPECTED_COVERAGE = 0.5

_MIDDLE_PROFILE_TEXT = (
    "Profilen tyder på att personens beteende till stor del beror på situationen. "
    "Utforska när personen känner igen sig i beskrivningen till vänster respektive "
    "till höger i profilen. Be gärna om konkreta exempel.",
    "Personen kan behöva mer sammanhang för att svara på intervjufrågorna. Var därför "
    "beredd att förtydliga frågorna och avsätt lite extra tid för samtalet.",
)

_CLEAR_PROFILE_TEXT = (
    "Profilen ger en tydlig bild av hur personen brukar agera. Personen kommer "
    "troligtvis att känna igen sig i beskrivningarna och ha lätt att ge konkreta exempel.",
    "Använd beskrivningarna som utgångspunkt för samtalet. Utforska också om det finns "
    "situationer där personen agerar på andra sätt, för att få en mer nyanserad bild.",
)

_SOCIAL_DESIRABILITY_TEXT = {
    "low": (
        "Personens självskattning är betydande mer självkritisk jämfört med andra. "
        "Ha ett coachande och uppmuntrande förhållningssätt.",
        "Inled med att lyfta resultatet och fråga om personen känner igen sig och vilka "
        "referenspunkter hen använder när hen bedömer sig själv. Fråga exempelvis: "
        "”Dina svar tyder på att du bedömer dig själv mer självkritiskt än andra brukar "
        "göra. Känner du igen dig i det? Vem eller vilka jämför du dig med?”",
        "Hjälp personen att nyansera bilden av både vad som varit svårt och vad hen "
        "faktiskt har lyckats med genom att utforska ett karaktärsdrag per område där "
        "personen kan ha underskattat sig själv.",
        "Be om konkreta exempel och undersök om självbeskrivningen gör personens agerande "
        "rättvisa. Det kan också vara hjälpsamt att utforska hur andra har beskrivit "
        "personens styrkor och bidrag.",
        "Fråga exempelvis:",
        "”Du har skattat X som att det kommer mindre naturligt för dig. Kan du berätta "
        "om ett tillfälle när det ändå fungerade bra? Vad gjorde du då?”",
        "”Vilka styrkor har andra lyft hos dig? Kan du ge ett exempel på när de kom till "
        "uttryck?”",
    ),
    "mild_low": (
        "Personens självskattning tenderar att vara mer självkritisk jämfört med andra. "
        "Utforska om personen känner igen sig i detta och vilka referenspunkter hen "
        "använder när hen bedömer sig själv. Fråga exempelvis: ”Dina svar tyder på att "
        "du kan vara något självkritisk i din bedömning av dig själv. Känner du igen "
        "dig i det? Vem eller vilka jämför du dig med?”",
        "Under samtalet kan du vara uppmärksam på om personen tonar ned sina styrkor "
        "eller fokuserar på det som kunde ha gått bättre. Välj ett karaktärsdrag i "
        "profilen att utforska närmare, där personen kan ha underskattat sig själv.",
        "Be om konkreta exempel och hjälp personen att sätta ord på sitt eget bidrag. "
        "Det kan också vara hjälpsamt att utforska hur andra har beskrivit personens "
        "styrkor och bidrag.",
        "Fråga exempelvis:",
        "”Vad bidrog du själv med i den situationen, även om allt inte blev som du hade "
        "önskat? Vad skulle någon som var med lyfta fram som ditt bidrag?”",
    ),
    "balanced": (
        "Personens självskattning ligger inom genomsnittet. Det tyder på att personen "
        "har beskrivit sig själv på ett balanserat sätt, utan någon tydlig tendens att "
        "framställa sig själv överdrivet positivt eller vara alltför självkritisk.",
        "Utgå från profilen och be om konkreta exempel på hur personen brukar agera. "
        "Utforska både situationer där beskrivningarna stämmer och situationer där "
        "personen agerar annorlunda. Det hjälper dig att förstå när och hur beteendena "
        "kommer till uttryck.",
        "Fråga exempelvis:",
        "”När känner du igen dig i den här beskrivningen? Finns det situationer där du "
        "agerar på ett annat sätt?”",
    ),
    "mild_high": (
        "Personens självskattning tenderar att vara mer socialt önskvärd jämfört med "
        "andra. Följ upp positiva beskrivningar med konkreta exempel.",
        "Tydliggör vad personen själv har gjort, särskilt när svaren handlar om vad "
        "”man” brukar göra eller vad ”vi” åstadkommit. Utforska också när beteendet "
        "har varit svårare att upprätthålla.",
        "Fråga exempelvis:",
        "”Du säger att ni löste situationen tillsammans. Vad var just ditt bidrag?”",
    ),
    "high": (
        "Personens självskattning är betydande mer socialt önskvärd jämfört med andra. "
        "Lägg extra vikt vid att förstå hur personens beskrivningar visar sig i praktiken "
        "kopplat till centrala områden för rollen.",
        "Be om flera konkreta exempel och följ upp personens eget agerande, resultatet "
        "och vad som varit utmanande. Skapa utrymme att berätta även om misstag och "
        "motgångar, med ett nyfiket och utforskande förhållningssätt.",
        "Fråga exempelvis:",
        "”Berätta om ett tillfälle när något inte gick som du hade tänkt och planerat. "
        "Vad hände? Vad gjorde du och vad lärde du dig?”",
    ),
}


def _normalise_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _expected_trait_keys() -> set[str]:
    return {
        _normalise_key(trait.get("trait_name"))
        for section in TRAIT_AND_INDICATOR_PROFILE.get("sections", [])
        for trait in section.get("traits", [])
        if trait.get("trait_name")
    }


def _valid_sten(value: Any) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or not numeric.is_integer():
        return None
    score = int(numeric)
    return score if 1 <= score <= 10 else None


def _available_trait_scores(
    personality_profile: dict[str, Any] | None,
) -> list[tuple[str, int]]:
    expected = _expected_trait_keys()
    seen: set[str] = set()
    available: list[tuple[str, int]] = []

    for section in (personality_profile or {}).get("sections", []):
        for trait in section.get("traits", []):
            key = _normalise_key(
                trait.get("canonical_key") or trait.get("name")
            )
            if key not in expected or key in seen:
                continue
            seen.add(key)
            score = _valid_sten(trait.get("sten"))
            if score is not None:
                available.append((key, score))

    return available


def _social_desirability_text(
    response_styles: list[dict[str, Any]] | None,
) -> tuple[str, ...]:
    style = next(
        (
            item for item in (response_styles or [])
            if item.get("key") == "social_desirability"
        ),
        None,
    )
    if not style or not style.get("available"):
        return ()

    score = _valid_sten(style.get("value"))
    if score is None:
        return ()
    if score <= 2:
        key = "low"
    elif score == 3:
        key = "mild_low"
    elif score <= 7:
        key = "balanced"
    elif score == 8:
        key = "mild_high"
    else:
        key = "high"
    return _SOCIAL_DESIRABILITY_TEXT[key]



def _format_social_desirability(
    paragraphs: tuple[str, ...],
) -> dict[str, Any] | None:
    """Separate interpretation, practical guidance, and example questions for display."""
    if not paragraphs:
        return None

    tips: list[str] = []
    questions: list[str] = []
    marker = " Fråga exempelvis: "

    for paragraph in paragraphs[1:]:
        if paragraph == "Fråga exempelvis:":
            continue
        if marker in paragraph:
            tip, question = paragraph.split(marker, maxsplit=1)
            if tip.strip():
                tips.append(tip.strip())
            if question.strip():
                questions.append(question.strip())
        elif paragraph.startswith("”"):
            questions.append(paragraph)
        else:
            tips.append(paragraph)

    return {
        "interpretation": paragraphs[0],
        "tips": tips,
        "questions": questions,
    }


def build_static_communication_guidance(
    personality_profile: dict[str, Any] | None,
    response_styles: list[dict[str, Any]] | None,
    *,
    language: str = "sv",
) -> dict[str, Any]:
    """Build the approved Swedish profile and response-style copy without AI."""
    language_key = "sv" if str(language or "").lower().startswith("sv") else "en"
    if language_key != "sv":
        return {"localized": False}

    scores = _available_trait_scores(personality_profile)
    expected_count = len(_expected_trait_keys())
    minimum_coverage = math.ceil(expected_count * MINIMUM_EXPECTED_COVERAGE)
    middle_count = sum(4 <= score <= 7 for _, score in scores)
    clear_count = sum(score <= 3 or score >= 8 for _, score in scores)

    profile_status = "unavailable"
    profile_title = ""
    profile_interpretation = ""
    profile_tips: list[str] = []

    if len(scores) >= minimum_coverage and middle_count >= PROFILE_MIDDLE_THRESHOLD:
        profile_status = "middle"
        profile_title = "Situationsbaserad profil"
        profile_interpretation, middle_follow_up = _MIDDLE_PROFILE_TEXT[0].split(
            " Utforska ",
            maxsplit=1,
        )
        profile_tips = [
            "Utforska " + middle_follow_up,
            _MIDDLE_PROFILE_TEXT[1],
        ]
    elif len(scores) >= minimum_coverage and clear_count >= PROFILE_CLEAR_THRESHOLD:
        profile_status = "clear"
        profile_title = "Tydlig profil"
        profile_interpretation = _CLEAR_PROFILE_TEXT[0]
        profile_tips = [_CLEAR_PROFILE_TEXT[1]]

    social_text = _social_desirability_text(response_styles)
    return {
        "localized": True,
        "profile_status": profile_status,
        "profile_title": profile_title,
        "profile_interpretation": profile_interpretation,
        "profile_tips": profile_tips,
        "social_desirability_available": bool(social_text),
        "social_desirability_guidance": _format_social_desirability(social_text),
        "available": profile_status != "unavailable" or bool(social_text),
        "available_trait_count": len(scores),
        "middle_trait_count": middle_count,
        "clear_trait_count": clear_count,
    }
