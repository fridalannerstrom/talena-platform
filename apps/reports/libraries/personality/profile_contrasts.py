"""Deterministic response-style profile contrasts based on approved indicator pairs."""
from __future__ import annotations

from typing import Any

from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)

CONTRAST_CATALOG_VERSION = "indicator-extremes-8-10-v1"
LOW_MAXIMUM = 3
HIGH_MINIMUM = 8


def _pair(
    pair_id: str,
    trait_key: str,
    left_key: str,
    right_key: str,
    high_side: str,
    hypothesis_sv: str,
    hypothesis_en: str,
) -> dict[str, Any]:
    return {
        "id": pair_id,
        "trait_key": trait_key,
        "left_key": left_key,
        "right_key": right_key,
        "high_side": high_side,
        "hypothesis": {"sv": hypothesis_sv, "en": hypothesis_en},
    }


# Fixed hypotheses from "Kontraster i indikatorer Uppdaterad.docx".
# The document's 7–10 upper range is corrected to 8–10 per product decision.
CONTRAST_CATALOG = (
    _pair("cooperative_sensitivity_teamwork", "cooperative", "sensitivity", "teamwork", "left",
          "Kan vara lyhörd för andra men behöver troligtvis inte föredra att arbeta tillsammans med dem",
          "May be attentive to others without necessarily preferring to work together with them."),
    _pair("cooperative_teamwork_agreeableness", "cooperative", "teamwork", "agreeableness", "left",
          "Gillar troligen grupparbete men kan ändå säga ifrån",
          "Probably enjoys group work but can still speak up."),
    _pair("empathy_listening_warmth", "empathy", "listening", "warmth", "left",
          "Lyssnar gärna och tar in perspektiv utan att nödvändigtvis vara särskilt relationsskapande",
          "Enjoys listening and taking in perspectives without necessarily being especially relationship-oriented."),
    _pair("empathy_tolerance_listening", "empathy", "tolerance", "listening", "right",
          "Vill troligen gärna förstå andra men kan samtidigt ha relativt tydliga krav på dem",
          "Probably wants to understand others while also having relatively clear expectations of them."),
    _pair("supporting_helpfulness_developing_others", "supporting", "helpfulness", "developing_others", "left",
          "Kan hjälpa här och nu men lämnar kanske utvecklingsansvaret till individen",
          "May help in the moment while leaving responsibility for development to the individual."),
    _pair("supporting_considerate_helpfulness", "supporting", "considerate", "helpfulness", "right",
          "Troligen mer uppgiftsfokuserad och tänker kanske inte så mycket på hur andra kan stöttas, men ingriper troligen om någon aktivt ber om hjälp",
          "Probably more task-focused and may not think much about how others can be supported, but will likely step in if someone actively asks for help."),
    _pair("connecting_open_communication_initiating_contact", "connecting", "open_communication", "initiating_contact", "left",
          "Troligtvis mer bekväm när kontakten väl finns, men initierar den inte nödvändigtvis",
          "Probably more comfortable once contact has been established, but does not necessarily initiate it."),
    _pair("connecting_initiating_contact_building_networks", "connecting", "initiating_contact", "building_networks", "left",
          "Tar förmodligen lätt nya kontakter utan att kanske lägga lika mycket energi på att bygga mer långvariga nätverk",
          "Probably makes new contacts easily without necessarily putting as much effort into building longer-term networks."),
    _pair("dynamic_energetic_risk_appetite", "dynamic", "energetic", "risk_appetite", "left",
          "Kan ha högt tempo och tar sig antagligen an mycket men är troligen mer hänsynsfull vid själva beslutsfattandet",
          "May work at a high pace and take on a lot, while probably being more considerate when making decisions."),
    _pair("dynamic_enthusiastic_energetic", "dynamic", "enthusiastic", "energetic", "left",
          "Kan vara snabb med att agera och komma igång med en uppgift, men föredrar kanske att arbeta i ett jämnare tempo med möjlighet att fokusera på färre saker",
          "May be quick to act and get started on a task, but may prefer a steadier pace with the chance to focus on fewer things."),
    _pair("influential_persuading_desire_to_lead", "influential", "persuading", "desire_to_lead", "left",
          "Kan tycka om att påverka, utan att nödvändigtvis ha behov av att ta befälet",
          "May enjoy influencing others without necessarily needing to take charge."),
    _pair("influential_desire_to_lead_assertive", "influential", "desire_to_lead", "assertive", "left",
          "Tar troligen gärna befälet, men behöver inte alltid vara särskilt pådrivande med egna åsikter",
          "Probably enjoys taking charge, but does not necessarily push personal opinions strongly."),
    _pair("influential_assertive_persuading", "influential", "assertive", "persuading", "right",
          "Sannolikt mer bekväm att övertyga andra, men har kanske inget större behov att pådyvla sin egen åsikt på andra",
          "Probably more comfortable persuading others, but may have little need to impose personal opinions on them."),
    _pair("goal_focused_self_discipline_competitive", "goal_focused", "self_discipline", "competitive", "left",
          "Kan vara mer uthållig och disciplinerad, utan att för den sakens skull kanske drivas av konkurrens med andra",
          "May be more persistent and disciplined without necessarily being driven by competition with others."),
    _pair("goal_focused_challenge_self_discipline", "goal_focused", "challenge", "self_discipline", "left",
          "Lockas troligen av mer utmanande mål men det säger kanske inte automatiskt något om disciplinen i själva genomförandet",
          "Probably drawn to more challenging goals, though that does not automatically indicate discipline in carrying them out."),
    _pair("structured_planning_attention_to_detail", "structured", "planning_and_organising", "attention_to_detail", "left",
          "Planerar sannolikt mer systematiskt men kan vara mindre detaljorienterad",
          "Probably plans more systematically but may be less detail-oriented."),
    _pair("structured_keeping_promises_planning", "structured", "keeping_promises", "planning_and_organising", "left",
          "Har troligen en starkare leveransplikt medan vägen dit kan vara mer flexibel och spontan i arbetssättet",
          "Probably has a stronger sense of delivery, while the way of getting there may be more flexible and spontaneous."),
    _pair("analytical_data_focus_problem_analysis", "analytical", "data_focus", "analysing_problems", "right",
          "Analyserar förmodligen gärna olika informationskällor och perspektiv vid komplexa problem, men behöver inte nödvändigtvis föredra siffror och statistik",
          "Probably enjoys analysing different information sources and perspectives in complex problems, without necessarily preferring numbers and statistics."),
    _pair("analytical_evaluating_data_focus", "analytical", "evaluating", "data_focus", "right",
          "Troligen ett starkare intresse för siffror och statistik, men kanske inte nödvändigtvis kritiskt granskar och utvärderar olika situationer",
          "Probably has a stronger interest in numbers and statistics, but may not necessarily critically examine and evaluate different situations."),
    _pair("complex_thinking_strategy_curiosity", "complex_thinking", "strategic_thinking", "curiosity", "left",
          "Kan gilla komplexa problem men behöver kanske inte alltid vara villig att sätta sig in i och lära sig nya metoder och arbetssätt",
          "May enjoy complex problems without always being willing to learn new methods and ways of working."),
    _pair("complex_thinking_conceptual_strategy", "complex_thinking", "conceptual", "strategic_thinking", "left",
          "Tänker troligen gärna abstrakt och brett men behöver inte alltid vilja lösa strategiskt komplexa problem",
          "Probably enjoys thinking abstractly and broadly, but may not always want to solve strategically complex problems."),
    _pair("creativity_ideas_experimenting", "creativity", "generating_ideas", "experimenting", "left",
          "Genererar sannolikt gärna idéer men är kanske inte lika intresserad att testa dem i praktiken",
          "Probably enjoys generating ideas but may be less interested in testing them in practice."),
    _pair("creativity_ideas_innovating", "creativity", "generating_ideas", "innovating", "left",
          "Kan troligen generera en större mängd idéer, vilka kanske tenderar att vara mer ‘innanför boxen’ och främst baserade på beprövade metoder",
          "May generate a larger number of ideas, which may tend to stay within the box and rely mainly on proven methods."),
    _pair("creativity_innovating_ideas", "creativity", "generating_ideas", "innovating", "right",
          "Troligen mindre bekväm att generera idéer på rak arm, men tänker gärna utanför boxen",
          "Probably less comfortable generating ideas on the spot, but enjoys thinking outside the box."),
    _pair("adaptability_variety_change", "adaptability", "variety", "adapting_to_change", "left",
          "Kan söka variation men kanske behöva tid när förändringen inte är självvald",
          "May seek variety but need time when a change is not self-chosen."),
    _pair("adaptability_flexible_variety", "adaptability", "flexible", "variety", "left",
          "Anpassar troligen sitt synsätt efter situationen, utan att för den sakens skull behöva ständig omväxling",
          "Probably adapts their perspective to the situation without needing constant variety."),
    _pair("straightforward_earnest_candid", "straightforward", "earnest", "candid", "right",
          "Kan förmodligen ha en mer rak kommunikation, men visar kanske inte fullt ut vad hen själv egentligen tycker eller känner",
          "May communicate more directly, but may not fully show what they really think or feel."),
    _pair("straightforward_earnest_candid_reverse", "straightforward", "earnest", "candid", "left",
          "Kan troligen ha en tydlig och genuint förankrad uppfattning, men kan kanske vara mer försiktig med att uttrycka den öppet till andra",
          "May have a clear and genuinely held view, while being more cautious about expressing it openly to others."),
    _pair("status_collective_egalitarian", "status_avoidance", "collective", "egalitarian", "left",
          "Tycks kanske helst inte vilja stå ut eller få särskild uppmärksamhet som individ, samtidigt som hen kan ha en viss förväntan på att en särskild roll eller position får betydelse för hur man blir bemött",
          "May prefer not to stand out or receive special attention as an individual, while still expecting a particular role or position to affect how they are treated."),
    _pair("status_avoiding_status_collective_low", "status_avoidance", "avoiding_status", "collective", "right",
          "Kan kanske lägga vikt vid status och den egna positionen, samtidigt som hen inte verkar ha något större behov av personlig uppmärksamhet eller uppskattning",
          "May value status and personal position while not seeming to need much personal attention or appreciation."),
    _pair("status_avoiding_status_collective_high", "status_avoidance", "avoiding_status", "collective", "left",
          "Lägger troligen inte särskilt stor vikt vid titel eller formell status, men kan samtidigt kanske vilja bli uppmärksammad och erkänd för sina egna egenskaper och bidrag",
          "Probably places little importance on title or formal status, while perhaps wanting recognition for personal qualities and contributions."),
    _pair("modesty_modest_avoiding_attention", "modesty", "modest", "avoiding_attention", "right",
          "Talar troligen inte mycket om egna bedrifter men kan ändå trivas med att stå i centrum",
          "Probably does not talk much about personal achievements but may still enjoy being the centre of attention."),
    _pair("modesty_humble_modest", "modesty", "humble", "modest", "right",
          "Kan vilja bli sedd och uppskattad för sina insatser, men lyfter kanske inte alltid själv fram vad hen själv har åstadkommit",
          "May want their efforts to be seen and appreciated, but may not always highlight what they have achieved."),
    _pair("resilience_tough_minded_recovering", "resilience", "tough_minded", "recovering", "left",
          "Kritik kan lättare rinna av medan motgångar kan ta tid att återhämta sig från",
          "Criticism may roll off more easily, while setbacks may take time to recover from."),
    _pair("resilience_optimistic_tough_minded", "resilience", "optimistic", "tough_minded", "left",
          "Ser troligen positivt på utmaningar men kan kanske vara känslig för kritik",
          "Probably sees challenges positively but may be sensitive to criticism."),
    _pair("resilience_optimistic_recovering", "resilience", "optimistic", "recovering", "left",
          "Kan sannolikt möta situationer med optimism och fokus på möjligheter, men kan ha svårare att gå vidare när något faktiskt har gått fel eller blivit en motgång",
          "May approach situations with optimism and focus on possibilities, but find it harder to move on when something has gone wrong or become a setback."),
    _pair("emotional_control_stress_composed", "emotional_control", "controlling_stress", "composed", "right",
          "Kan kanske reagera känslomässigt och låta det märkas under press, men verkar samtidigt kunna behålla kontrollen över sitt agerande när situationen blir utmanande",
          "May react emotionally and show it under pressure, while still seeming able to control their actions when things become challenging."),
    _pair("emotional_control_stress_calm", "emotional_control", "controlling_stress", "calm", "left",
          "Kan troligen känna en tydlig oro i utmanande situationer, samtidigt som hen kan ha lättare att lyckas reglera sina känslor och inte visa så mycket utåt",
          "May feel clear anxiety in challenging situations, while finding it easier to regulate emotions and show little outwardly."),
    _pair("emotional_control_calm_composed", "emotional_control", "calm", "composed", "left",
          "Oroar sig troligen sällan i vanliga situationer, men kan kanske få svårare att behålla självbehärskningen när belastningen blir riktigt hög",
          "Probably rarely worries in everyday situations, but may find it harder to stay composed under very high strain."),
    _pair("independence_self_reliant_independent_thinking", "independence", "self_reliant", "thinking_independently", "left",
          "Kan sannolikt driva sitt arbete utan vägledning men ändå uppskatta bollning inför beslut ibland",
          "May drive their work without guidance while still appreciating discussion before decisions."),
    _pair("independence_self_contained_self_reliant", "independence", "self_contained", "self_reliant", "left",
          "Behöver förmodligen inte så mycket socialt stöd men kan fortfarande uppskatta praktisk vägledning",
          "Probably does not need much social support but may still appreciate practical guidance."),
    _pair("independence_independent_thinking_self_contained", "independence", "thinking_independently", "self_contained", "left",
          "Föredrar troligtvis att tänka själv men kan uppskatta emotionellt stöd från andra",
          "Probably prefers to think independently but may appreciate emotional support from others."),
)


def expected_profile_dimension_count() -> int:
    return sum(
        1 + len(trait.get("indicators") or [])
        for section in TRAIT_AND_INDICATOR_PROFILE.get("sections", [])
        for trait in section.get("traits", [])
    )


def _score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        result = int(round(float(value)))
    except (TypeError, ValueError, OverflowError):
        return None
    return result if 1 <= result <= 10 else None


def _flatten_profile(profile: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    dimensions: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    if not isinstance(profile, dict):
        return dimensions

    for section in profile.get("sections") or []:
        for trait in section.get("traits") or []:
            for item in [trait, *(trait.get("indicators") or [])]:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("canonical_key") or "").strip().lower()
                status = str(item.get("mapping_status") or "").strip().lower()
                if not key or status in {"duplicate", "ambiguous"}:
                    continue
                value = _score(item.get("sten"))
                if value is None:
                    continue
                record = {
                    "key": key,
                    "label": str(item.get("label") or item.get("name") or key),
                    "sten": value,
                }
                previous = dimensions.get(key)
                if previous and previous["sten"] != value:
                    dimensions.pop(key, None)
                    ambiguous.add(key)
                elif key not in ambiguous:
                    dimensions.setdefault(key, record)
    return dimensions


def _graph_segments(selected_sten: int) -> list[dict[str, Any]]:
    """Return the same ten filled/selected markers used by the personality chart."""
    return [
        {
            "score": score,
            "selected": score == selected_sten,
            "filled_toward_midpoint": (
                selected_sten <= score <= 5
                if selected_sten <= 5
                else 6 <= score <= selected_sten
            ),
        }
        for score in range(1, 11)
    ]


def _rule_matches(rule: dict[str, Any], left: int, right: int) -> bool:
    high_side = rule.get("high_side")
    if high_side == "left":
        return left >= HIGH_MINIMUM and right <= LOW_MAXIMUM
    if high_side == "right":
        return right >= HIGH_MINIMUM and left <= LOW_MAXIMUM
    return False


def build_profile_contrast_analysis(
    personality_profile: dict[str, Any] | None,
    *,
    language: str = "sv",
    source: str = "sova_assessment",
) -> dict[str, Any]:
    """Return fixed contrast hypotheses whose indicators meet opposite extremes."""
    language = "sv" if str(language or "").lower().startswith("sv") else "en"
    dimensions = _flatten_profile(personality_profile)
    activated = []

    for entry in CONTRAST_CATALOG:
        left = dimensions.get(entry["left_key"])
        right = dimensions.get(entry["right_key"])
        if not left or not right or not _rule_matches(entry, left["sten"], right["sten"]):
            continue
        high = left["sten"] if entry["high_side"] == "left" else right["sten"]
        low = right["sten"] if entry["high_side"] == "left" else left["sten"]
        activated.append({
            "id": entry["id"],
            "trait_key": entry["trait_key"],
            "left_key": entry["left_key"],
            "right_key": entry["right_key"],
            "left_label": left["label"],
            "right_label": right["label"],
            "left_sten": left["sten"],
            "right_sten": right["sten"],
            "dimensions": [
                {"label": left["label"], "sten": left["sten"], "graph_segments": _graph_segments(left["sten"])},
                {"label": right["label"], "sten": right["sten"], "graph_segments": _graph_segments(right["sten"])},
            ],
            "hypothesis": entry["hypothesis"].get(language) or entry["hypothesis"]["en"],
            "strength": min(high - HIGH_MINIMUM, LOW_MAXIMUM - low),
            "catalog_version": CONTRAST_CATALOG_VERSION,
        })

    activated.sort(key=lambda item: (-item["strength"], item["id"]))

    if language == "sv":
        neutral_message = (
            "Inga indikatorpar med tydliga ytterlägen matchar de fördefinierade mönstren."
        )
    else:
        neutral_message = (
            "No indicator pairs at the defined extremes match the predefined patterns."
        )

    return {
        "catalog_version": CONTRAST_CATALOG_VERSION,
        "source": source,
        "available_dimension_count": len(dimensions),
        "expected_dimension_count": expected_profile_dimension_count(),
        "activated_contrasts": activated,
        "neutral_message": neutral_message,
    }
