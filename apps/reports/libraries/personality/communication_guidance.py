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



_MIDDLE_PROFILE_TEXT_EN = (
    "The profile suggests that the person's behaviour depends largely on the situation. "
    "Explore when the person recognises themselves in the descriptions on the left and "
    "right of the profile. Ask for specific examples.",
    "The person may need more context to answer interview questions. Be prepared to "
    "clarify questions and allow a little extra time for the conversation.",
)

_CLEAR_PROFILE_TEXT_EN = (
    "The profile gives a clear picture of how the person tends to act. They are likely "
    "to recognise themselves in the descriptions and find it easy to give specific examples.",
    "Use the descriptions as a starting point for the conversation. Also explore whether "
    "there are situations in which the person acts differently, to gain a more nuanced picture.",
)

_SOCIAL_DESIRABILITY_TEXT_EN = {
    "low": (
        "The person's self-assessment is significantly more self-critical compared with "
        "others. Take a coaching and encouraging approach.",
        "Start by sharing the result and asking whether the person recognises themselves "
        "in it and what reference points they use when assessing themselves. For example: "
        "“Your answers suggest that you assess yourself more critically than other people "
        "tend to. Do you recognise that? Who or what do you compare yourself with?”",
        "Help the person develop a more balanced view of both what has been difficult and "
        "what they have achieved by exploring one trait in each area where they may have "
        "underestimated themselves.",
        "Ask for specific examples and explore whether the person's self-description does "
        "justice to their actions. It may also help to explore how others have described "
        "their strengths and contributions.",
        "For example:",
        "“You rated X as something that comes less naturally to you. Can you tell me about "
        "a time when it still went well? What did you do?”",
        "“What strengths have others recognised in you? Can you give an example of when "
        "they showed up?”",
    ),
    "mild_low": (
        "The person's self-assessment tends to be more self-critical compared with others. "
        "Explore whether they recognise this and what reference points they use when "
        "assessing themselves. For example: “Your answers suggest that you may be somewhat "
        "self-critical in how you assess yourself. Do you recognise that? Who or what do "
        "you compare yourself with?”",
        "During the conversation, be alert to whether the person downplays their strengths "
        "or focuses on what could have gone better. Choose a trait in the profile to explore "
        "further where the person may have underestimated themselves.",
        "Ask for specific examples and help the person put their own contribution into "
        "words. It may also help to explore how others have described their strengths and "
        "contributions.",
        "For example:",
        "“What did you contribute in that situation, even if everything did not go as you "
        "had hoped? What might someone who was there say you contributed?”",
    ),
    "balanced": (
        "The person's self-assessment is within the average range. This suggests that they "
        "have described themselves in a balanced way, with no clear tendency to present "
        "themselves as overly positive or to be overly self-critical.",
        "Use the profile and ask for specific examples of how the person tends to act. "
        "Explore both situations where the descriptions fit and situations where the person "
        "acts differently. This helps you understand when and how the behaviours show up.",
        "For example:",
        "“When do you recognise yourself in this description? Are there situations where "
        "you act differently?”",
    ),
    "mild_high": (
        "The person's self-ratings tend to present them in a more socially desirable light "
        "compared with others. Follow up positive descriptions with specific examples.",
        "Clarify what the person themselves did, especially when their answers refer to what "
        "“people” usually do or what “we” achieved. Also explore when it has been harder to "
        "maintain that behaviour.",
        "For example:",
        "“You said that you solved the situation together. What was your specific contribution?”",
    ),
    "high": (
        "The person's self-ratings are significantly more socially desirable compared with "
        "others. Pay particular attention to how their descriptions show up in practice in "
        "areas that matter for the role.",
        "Ask for several specific examples and follow up on the person's own actions, the "
        "outcome and what was challenging. Create space for them to talk about mistakes and "
        "setbacks, using a curious and exploratory approach.",
        "For example:",
        "“Tell me about a time when something did not go as you had planned. What happened? "
        "What did you do, and what did you learn?”",
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
    language: str = "sv",
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
    content = _SOCIAL_DESIRABILITY_TEXT if language == "sv" else _SOCIAL_DESIRABILITY_TEXT_EN
    return content[key]



def _format_social_desirability(
    paragraphs: tuple[str, ...],
    language: str = "sv",
) -> dict[str, Any] | None:
    """Separate interpretation, practical guidance, and example questions for display."""
    if not paragraphs:
        return None

    tips: list[str] = []
    questions: list[str] = []
    marker = " Fråga exempelvis: " if language == "sv" else " For example: "
    example_label = "Fråga exempelvis:" if language == "sv" else "For example:"
    interpretation = paragraphs[0]

    if marker in interpretation:
        interpretation, question = interpretation.split(marker, maxsplit=1)
        if question.strip():
            questions.append(question.strip())

    for paragraph in paragraphs[1:]:
        if paragraph == example_label:
            continue
        if marker in paragraph:
            tip, question = paragraph.split(marker, maxsplit=1)
            if tip.strip():
                tips.append(tip.strip())
            if question.strip():
                questions.append(question.strip())
        elif paragraph.startswith(("”", "“")):
            questions.append(paragraph)
        else:
            tips.append(paragraph)

    return {
        "interpretation": interpretation.strip(),
        "tips": tips,
        "questions": questions,
    }


def build_static_communication_guidance(
    personality_profile: dict[str, Any] | None,
    response_styles: list[dict[str, Any]] | None,
    *,
    language: str = "sv",
) -> dict[str, Any]:
    """Build fixed localized profile and response-style copy without AI."""
    language_key = "sv" if str(language or "").lower().startswith("sv") else "en"
    middle_profile_text = (
        _MIDDLE_PROFILE_TEXT if language_key == "sv" else _MIDDLE_PROFILE_TEXT_EN
    )
    clear_profile_text = (
        _CLEAR_PROFILE_TEXT if language_key == "sv" else _CLEAR_PROFILE_TEXT_EN
    )

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
        profile_title = (
            "Situationsbaserad profil"
            if language_key == "sv"
            else "Situational profile"
        )
        split_marker = " Utforska " if language_key == "sv" else " Explore "
        profile_interpretation, middle_follow_up = middle_profile_text[0].split(
            split_marker,
            maxsplit=1,
        )
        profile_tips = [
            ("Utforska " if language_key == "sv" else "Explore ") + middle_follow_up,
            middle_profile_text[1],
        ]
    elif len(scores) >= minimum_coverage and clear_count >= PROFILE_CLEAR_THRESHOLD:
        profile_status = "clear"
        profile_title = "Tydlig profil" if language_key == "sv" else "Clear profile"
        profile_interpretation = clear_profile_text[0]
        profile_tips = [clear_profile_text[1]]

    social_text = _social_desirability_text(response_styles, language_key)
    return {
        "localized": True,
        "language": language_key,
        "profile_status": profile_status,
        "profile_title": profile_title,
        "profile_interpretation": profile_interpretation,
        "profile_tips": profile_tips,
        "social_desirability_available": bool(social_text),
        "social_desirability_guidance": _format_social_desirability(
            social_text,
            language_key,
        ),
        "available": profile_status != "unavailable" or bool(social_text),
        "available_trait_count": len(scores),
        "middle_trait_count": middle_count,
        "clear_trait_count": clear_count,
    }
