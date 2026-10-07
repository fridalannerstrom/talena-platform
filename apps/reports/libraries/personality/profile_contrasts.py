"""Rule-based, versioned profile contrasts and middle-profile evidence.

The catalog and activation policy are versioned. Expert approval is recorded
with each pair so the display remains traceable.
"""
from __future__ import annotations

from math import ceil
from typing import Any

from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)

CONTRAST_CATALOG_VERSION = "2026-10-07-expert-reviewed-v1"
MIDDLE_PROFILE_RULE_VERSION = "middle-profile-v1"
MIDDLE_PROFILE_MINIMUM_COUNT = 10
MIDDLE_PROFILE_MINIMUM_SHARE = 0.5
MIDDLE_PROFILE_MINIMUM_COVERAGE = 0.5
MAX_PROFILE_CONTRASTS = 5


def _pair(pair_id: str, trait_key: str, left_key: str, right_key: str,
          hypothesis_sv: str, hypothesis_en: str) -> dict[str, Any]:
    return {
        "id": pair_id,
        "trait_key": trait_key,
        "left_key": left_key,
        "right_key": right_key,
        "hypothesis": {"sv": hypothesis_sv, "en": hypothesis_en},
        "approved": False,
        "activation_rule": None,
        "rule_version": None,
        "approval_source": None,
        "display_priority": None,
    }


# Starter hypotheses from issue #282. The draft entries deliberately have no
# activation thresholds. A pair remains inactive until an expert-reviewed rule
# and its approval source/version are recorded here.
CONTRAST_CATALOG = (
    _pair("cooperative_sensitivity_teamwork", "cooperative", "sensitivity", "teamwork",
          "Kan vara lyhörd för andra utan att föredra grupparbete.",
          "May be attentive to others without preferring group work."),
    _pair("cooperative_teamwork_agreeableness", "cooperative", "teamwork", "agreeableness",
          "Kan trivas i grupp och samtidigt säga ifrån; eller samarbeta smidigt utan att söka grupparbete.",
          "May enjoy group work while still speaking up, or collaborate smoothly without seeking group work."),
    _pair("empathy_listening_warmth", "empathy", "listening", "warmth",
          "Tar in andras perspektiv utan att nödvändigtvis söka nära relationer.",
          "Takes in other perspectives without necessarily seeking close relationships."),
    _pair("empathy_tolerance_listening", "empathy", "tolerance", "listening",
          "Vill förstå andra men kan ändå ställa tydliga krav.",
          "Wants to understand others while still being able to set clear expectations."),
    _pair("supporting_helpfulness_developing_others", "supporting", "helpfulness", "developing_others",
          "Hjälper gärna i stunden men lämnar kanske utvecklingsansvaret åt individen.",
          "May gladly help in the moment while leaving development responsibility with the individual."),
    _pair("supporting_considerate_helpfulness", "supporting", "considerate", "helpfulness",
          "Tänker på stöd men agerar inte alltid praktiskt, eller tvärtom.",
          "May be considerate of support needs without always acting practically, or the reverse."),
    _pair("connecting_open_communication_initiating_contact", "connecting", "open_communication", "initiating_contact",
          "Är bekväm i etablerad kontakt men tar inte alltid initiativet.",
          "May be comfortable in established contact without always taking the initiative."),
    _pair("connecting_initiating_contact_building_networks", "connecting", "initiating_contact", "building_networks",
          "Tar nya kontakter lättare än hen bygger långvariga nätverk.",
          "May find it easier to make new contacts than to build lasting networks."),
    _pair("dynamic_energetic_risk_appetite", "dynamic", "energetic", "risk_appetite",
          "Håller högt tempo men fattar ändå försiktiga beslut.",
          "May maintain a high pace while still making cautious decisions."),
    _pair("dynamic_enthusiastic_risk_appetite", "dynamic", "enthusiastic", "risk_appetite",
          "Agerar snabbt utan att nödvändigtvis vara riskbenägen.",
          "May act quickly without necessarily being inclined to take risks."),
    _pair("influential_persuading_desire_to_lead", "influential", "persuading", "desire_to_lead",
          "Påverkar gärna utan att söka en ledarroll.",
          "May enjoy influencing others without seeking a leadership role."),
    _pair("influential_desire_to_lead_assertive", "influential", "desire_to_lead", "assertive",
          "Tar gärna befälet utan att alltid driva egna åsikter hårt.",
          "May be willing to take the lead without always pushing personal views strongly."),
    _pair("influential_assertive_persuading", "influential", "assertive", "persuading",
          "Är tydlig med sin åsikt utan starkt behov av att övertyga andra.",
          "May express views clearly without a strong need to persuade others."),
    _pair("goal_focused_self_discipline_competitive", "goal_focused", "self_discipline", "competitive",
          "Är uthållig utan att drivas av konkurrens.",
          "May be persistent without being driven by competition."),
    _pair("goal_focused_challenge_self_discipline", "goal_focused", "challenge", "self_discipline",
          "Lockas av höga mål, men uthållighet i genomförandet behöver utforskas separat.",
          "May be drawn to ambitious goals, while persistence in carrying them through needs separate exploration."),
    _pair("structured_planning_attention_to_detail", "structured", "planning_and_organising", "attention_to_detail",
          "Planerar systematiskt men fokuserar mindre på detaljer, eller tvärtom.",
          "May plan systematically while focusing less on detail, or the reverse."),
    _pair("structured_keeping_promises_planning", "structured", "keeping_promises", "planning_and_organising",
          "Levererar på åtaganden trots ett flexibelt arbetssätt.",
          "May deliver on commitments while working flexibly."),
    _pair("analytical_data_focus_problem_analysis", "analytical", "data_focus", "analysing_problems",
          "Analyserar komplexa problem men föredrar inte nödvändigtvis siffror.",
          "May analyse complex problems without necessarily preferring numerical data."),
    _pair("analytical_evaluating_data_focus", "analytical", "evaluating", "data_focus",
          "Granskar kritiskt utan starkt intresse för kvantitativa data.",
          "May review information critically without a strong interest in quantitative data."),
    _pair("complex_thinking_strategy_curiosity", "complex_thinking", "strategic_thinking", "curiosity",
          "Gillar komplexa frågor men söker inte alltid nya perspektiv.",
          "May enjoy complex questions without always seeking new perspectives."),
    _pair("complex_thinking_conceptual_strategy", "complex_thinking", "conceptual", "strategic_thinking",
          "Tänker abstrakt utan att alltid vilja lösa strategiska problem.",
          "May think abstractly without always wanting to solve strategic problems."),
    _pair("creativity_ideas_experimenting", "creativity", "generating_ideas", "experimenting",
          "Tar fram idéer men är försiktig med att testa dem.",
          "May generate ideas while being cautious about testing them."),
    _pair("creativity_innovating_experimenting", "creativity", "innovating", "experimenting",
          "Söker nya lösningar men föredrar ett kontrollerat genomförande.",
          "May seek new solutions while preferring a controlled implementation."),
    _pair("adaptability_variety_change", "adaptability", "variety", "adapting_to_change",
          "Söker variation men kan behöva tid vid ofrivillig förändring.",
          "May seek variety while needing time to adjust to unplanned change."),
    _pair("adaptability_flexible_variety", "adaptability", "flexible", "variety",
          "Anpassar synsätt utan att behöva ständig omväxling.",
          "May adapt their approach without needing constant variety."),
    _pair("straightforward_candid_rules", "straightforward", "candid", "adhering_to_rules",
          "Kan vara rak i kommunikationen men pragmatisk med regler; det rör skilda aspekter av samma drag.",
          "May communicate candidly while being pragmatic about rules; these are distinct aspects of the broader trait."),
    _pair("straightforward_earnest_candid", "straightforward", "earnest", "candid",
          "Upplevs som genuin utan att alltid uttrycka åsikter direkt.",
          "May come across as genuine without always expressing views directly."),
    _pair("status_egalitarian_avoiding_status", "status_avoidance", "egalitarian", "avoiding_status",
          "Vill ha jämlikt bemötande men uppskattar kanske erkännande.",
          "May value equal treatment while still appreciating recognition."),
    _pair("status_collective_avoiding_status", "status_avoidance", "collective", "avoiding_status",
          "Föredrar gruppfokus utan att sakna intresse för status.",
          "May prefer a group focus without lacking interest in status."),
    _pair("modesty_modest_avoiding_attention", "modesty", "modest", "avoiding_attention",
          "Tonar ned egna prestationer men kan trivas med synlighet.",
          "May downplay personal achievements while still being comfortable with visibility."),
    _pair("modesty_humble_avoiding_attention", "modesty", "humble", "avoiding_attention",
          "Ser sig som en i gruppen men undviker inte nödvändigtvis uppmärksamhet.",
          "May see themselves as one of the group without necessarily avoiding attention."),
    _pair("resilience_tough_minded_recovering", "resilience", "tough_minded", "recovering",
          "Tar kritik lättare än motgångar, eller tvärtom.",
          "May handle criticism more easily than setbacks, or the reverse."),
    _pair("resilience_optimistic_tough_minded", "resilience", "optimistic", "tough_minded",
          "Ser positivt på utmaningar men kan vara känslig för kritik.",
          "May view challenges positively while remaining sensitive to criticism."),
    _pair("emotional_control_stress_calm", "emotional_control", "controlling_stress", "calm",
          "Håller beteendet under kontroll trots inre oro.",
          "May keep behaviour composed despite feeling inner worry."),
    _pair("emotional_control_calm_composed", "emotional_control", "calm", "composed",
          "Verkar lugn i vardagen men reagerar annorlunda i laddade situationer.",
          "May seem calm day to day but respond differently in emotionally charged situations."),
    _pair("independence_self_reliant_independent_thinking", "independence", "self_reliant", "thinking_independently",
          "Driver arbete utan stöd men kan vilja bolla beslut.",
          "May drive work forward without support while still wanting to discuss decisions."),
    _pair("independence_self_contained_self_reliant", "independence", "self_contained", "self_reliant",
          "Behov av socialt stöd och praktisk vägledning kan skilja sig åt.",
          "The need for social support and practical guidance may differ."),
)


# Veronika's expert approval was confirmed by the user on 2026-10-07.
# The approved trigger is a difference of at least four STEN points in
# either direction. Catalog hypotheses remain distinct; the rule only
# decides when a supplied pair is relevant.
CONTRAST_CATALOG = tuple({
    **entry,
    "approved": True,
    "activation_rule": {
        "mode": "either_direction",
        "minimum_difference": 4,
    },
    "rule_version": "veronika-2026-10-07-v1",
    "approval_source": (
        "Veronika (expert approval confirmed by user, 2026-10-07)"
    ),
    "display_priority": 50,
} for entry in CONTRAST_CATALOG)


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


def _flatten_profile(profile: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], set[str]]:
    dimensions: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    if not isinstance(profile, dict):
        return dimensions, ambiguous

    for section in profile.get("sections") or []:
        for trait in section.get("traits") or []:
            records = [trait, *(trait.get("indicators") or [])]
            for item in records:
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
                    "low_pole": str(item.get("low_pole") or "").strip(),
                    "high_pole": str(item.get("high_pole") or "").strip(),
                }
                previous = dimensions.get(key)
                if previous and previous["sten"] != value:
                    dimensions.pop(key, None)
                    ambiguous.add(key)
                elif key not in ambiguous:
                    dimensions.setdefault(key, record)

    return dimensions, ambiguous


def _rule_matches(rule: dict[str, Any], left: int, right: int) -> bool:
    mode = str(rule.get("mode") or "").strip().lower()
    if mode in {"left_higher_by", "right_higher_by", "either_direction"}:
        try:
            minimum_difference = int(rule.get("minimum_difference"))
        except (TypeError, ValueError):
            return False
        if minimum_difference < 1:
            return False
        difference = left - right
        if mode == "left_higher_by":
            return difference >= minimum_difference
        if mode == "right_higher_by":
            return -difference >= minimum_difference
        return abs(difference) >= minimum_difference

    if mode in {"both_high", "both_low"}:
        try:
            threshold = int(rule.get("threshold"))
        except (TypeError, ValueError):
            return False
        if not 1 <= threshold <= 10:
            return False
        return left >= threshold and right >= threshold if mode == "both_high" else left <= threshold and right <= threshold

    if mode == "opposed_extremes":
        try:
            low_maximum = int(rule.get("low_maximum"))
            high_minimum = int(rule.get("high_minimum"))
        except (TypeError, ValueError):
            return False
        if not (1 <= low_maximum < high_minimum <= 10):
            return False
        return (
            left <= low_maximum and right >= high_minimum
        ) or (
            right <= low_maximum and left >= high_minimum
        )

    return False


def _rule_strength(rule: dict[str, Any], left: int, right: int) -> int:
    """Return the deterministic margin beyond an approved rule threshold."""
    mode = str(rule.get("mode") or "").strip().lower()
    if mode in {"left_higher_by", "right_higher_by", "either_direction"}:
        return abs(left - right) - int(rule["minimum_difference"])
    if mode == "both_high":
        return min(left, right) - int(rule["threshold"])
    if mode == "both_low":
        return int(rule["threshold"]) - max(left, right)
    if mode == "opposed_extremes":
        low, high = sorted((left, right))
        return min(
            int(rule["low_maximum"]) - low,
            high - int(rule["high_minimum"]),
        )
    return 0


def build_profile_contrast_analysis(
    personality_profile: dict[str, Any] | None,
    *,
    language: str = "sv",
    source: str = "sova_assessment",
) -> dict[str, Any]:
    """Return only deterministic, expert-approved contrasts and middle-profile evidence."""
    language = "sv" if str(language or "").lower().startswith("sv") else "en"
    dimensions, ambiguous = _flatten_profile(personality_profile)
    activated = []

    for entry in CONTRAST_CATALOG:
        rule = entry.get("activation_rule")
        if not entry.get("approved") or not isinstance(rule, dict):
            continue
        if not entry.get("rule_version") or not entry.get("approval_source"):
            continue
        try:
            display_priority = int(entry.get("display_priority"))
        except (TypeError, ValueError):
            continue
        left = dimensions.get(entry["left_key"])
        right = dimensions.get(entry["right_key"])
        if not left or not right or not _rule_matches(rule, left["sten"], right["sten"]):
            continue
        pair_dimensions = (left, right)
        left_labels = [
            item["label"] for item in pair_dimensions
            if item["sten"] <= 3
        ]
        right_labels = [
            item["label"] for item in pair_dimensions
            if item["sten"] >= 8
        ]
        context_labels = [
            item["label"] for item in pair_dimensions
            if 4 <= item["sten"] <= 7
        ]
        activated.append({
            "id": entry["id"],
            "trait_key": entry["trait_key"],
            "left_key": entry["left_key"],
            "right_key": entry["right_key"],
            "left_label": left["label"],
            "right_label": right["label"],
            "left_sten": left["sten"],
            "right_sten": right["sten"],
            "left_dimensions": " · ".join(left_labels),
            "right_dimensions": " · ".join(right_labels),
            "context_dimensions": " · ".join(context_labels),
            "hypothesis": entry["hypothesis"].get(language) or entry["hypothesis"]["en"],
            "rule_version": entry["rule_version"],
            "approval_source": entry["approval_source"],
            "display_priority": display_priority,
            "strength": _rule_strength(rule, left["sten"], right["sten"]),
            "catalog_version": CONTRAST_CATALOG_VERSION,
        })

    activated.sort(key=lambda item: (-item["display_priority"], -item["strength"], item["id"]))
    activated = activated[:MAX_PROFILE_CONTRASTS]

    expected_count = expected_profile_dimension_count()
    available_count = len(dimensions)
    middle_count = sum(4 <= item["sten"] <= 7 for item in dimensions.values())
    minimum_coverage = max(
        MIDDLE_PROFILE_MINIMUM_COUNT,
        ceil(expected_count * MIDDLE_PROFILE_MINIMUM_COVERAGE),
    )
    enough_coverage = available_count >= minimum_coverage
    middle_is_many = (
        available_count > 0
        and middle_count >= MIDDLE_PROFILE_MINIMUM_COUNT
        and middle_count / available_count >= MIDDLE_PROFILE_MINIMUM_SHARE
    )
    show_middle_profile = enough_coverage and middle_is_many

    if language == "sv":
        middle_note = (
            "Minst tio av de tillgängliga resultaten ligger i intervallet 4–7. "
            "Det kan tyda på att flera av kandidatens preferenser påverkas mer av situation och sammanhang."
        )
        no_contrasts_message = (
            "Inga granskade profilkontraster är tillgängliga för den här profilen. "
            "Därför visas inga kontrasttolkningar."
        )
        insufficient_data_message = (
            "Underlaget räcker inte för att visa ett mönster i mitten av profilen."
        )
    else:
        middle_note = (
            "At least ten available results fall in the 4–7 range. "
            "This may mean several of the candidate's preferences vary more with the situation and context."
        )
        no_contrasts_message = (
            "No reviewed profile contrasts are available for this profile, "
            "so no contrast interpretations are shown."
        )
        insufficient_data_message = (
            "There is not enough available evidence to show a middle-profile pattern."
        )

    return {
        "catalog_version": CONTRAST_CATALOG_VERSION,
        "middle_rule_version": MIDDLE_PROFILE_RULE_VERSION,
        "source": source,
        "available_dimension_count": available_count,
        "expected_dimension_count": expected_count,
        "ambiguous_dimension_keys": sorted(ambiguous),
        "activated_contrasts": activated,
        "show_middle_profile": show_middle_profile,
        "middle_profile_count": middle_count if show_middle_profile else 0,
        "middle_profile_note": middle_note if show_middle_profile else "",
        "neutral_message": no_contrasts_message,
        "insufficient_data_message": insufficient_data_message,
    }
