import re
from apps.reports.libraries.personality.definitions import PERSONALITY_REPORT_DEFINITIONS

POSSIBLE_MATCH_LOOKUP = {
    "resolving_issues": ["Generates Solutions"],
    "post_sales_servicing": ["Service Focus"],

    "prospecting_and_networking_with_purpose": ["Building Networks"],
    "establishing_connections": ["Connecting"],
    "delivering_on_commitments": ["Keeping Promises"],
    "creating_impactful_messages": ["Persuading"],
    "uncovering_needs_and_expectations": ["Listening"],
    "tailoring_solutions": ["Generates Solutions"],

    "striving_for_success": ["Drive to Achieve"],
    "staying_the_course": ["Resilience"],
    "collaborating_internally": ["Teamwork"],
    "learning_and_developing": ["Learning Mindset"],
    "honesty_humility": ["Honesty, Humility"],
}

def normalize_name(value):
    value = (value or "").strip().lower()
    value = value.replace("&", "and")
    value = re.sub(r"[-/]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def to_canonical_key(value):
    return normalize_name(value).replace(" ", "_")


def build_competency_lookup(competencies):
    lookup = {}
    duplicates = {}

    for item in competencies:
        raw_name = item.get("competency", "")
        normalized = normalize_name(raw_name)

        if normalized in lookup:
            duplicates.setdefault(normalized, [lookup[normalized]])
            duplicates[normalized].append(item)

        lookup[normalized] = item

    return lookup, duplicates


def build_report_table(report_definition, competencies, library_status_lookup=None):
    library_status_lookup = library_status_lookup or {}

    competency_lookup, duplicates = build_competency_lookup(competencies)
    used_keys = set()
    rows = []

    total_expected = 0
    matched_count = 0
    duplicate_count = 0

    for section in report_definition["sections"]:
        section_rows = []

        for trait in section["traits"]:
            trait_name = trait["trait_name"]
            trait_normalized = normalize_name(trait_name)
            trait_match = competency_lookup.get(trait_normalized)

            total_expected += 1
            if trait_match:
                matched_count += 1
                used_keys.add(trait_normalized)
            if trait_normalized in duplicates:
                duplicate_count += 1

            trait_canonical = to_canonical_key(trait_name)
            possible_trait_matches = POSSIBLE_MATCH_LOOKUP.get(trait_canonical, [])

            section_rows.append({
                "row_type": "trait",
                "section_name": section["section_name"],
                "parent_trait": "",
                "expected_name": trait_name,
                "sova_name": trait_match["competency"] if trait_match else "",
                "canonical_key": trait_canonical,
                "sten": trait_match.get("sten_rounded") if trait_match else None,
                "percentile": trait_match.get("percentile") if trait_match else None,
                "mapping_status": "duplicate" if trait_normalized in duplicates else ("matched" if trait_match else "missing"),
                "library_status": library_status_lookup.get(trait_canonical, "not_started"),
                "notes": "Duplicate name in payload" if trait_normalized in duplicates else "",
                "possible_match": ", ".join(possible_trait_matches),
            })

            for indicator in trait["indicators"]:
                indicator_normalized = normalize_name(indicator)
                indicator_match = competency_lookup.get(indicator_normalized)

                total_expected += 1
                if indicator_match:
                    matched_count += 1
                    used_keys.add(indicator_normalized)
                if indicator_normalized in duplicates:
                    duplicate_count += 1

                indicator_canonical = to_canonical_key(indicator)
                possible_indicator_matches = POSSIBLE_MATCH_LOOKUP.get(indicator_canonical, [])

                section_rows.append({
                    "row_type": "indicator",
                    "section_name": section["section_name"],
                    "parent_trait": trait_name,
                    "expected_name": indicator,
                    "sova_name": indicator_match["competency"] if indicator_match else "",
                    "canonical_key": indicator_canonical,
                    "sten": indicator_match.get("sten_rounded") if indicator_match else None,
                    "percentile": indicator_match.get("percentile") if indicator_match else None,
                    "mapping_status": "duplicate" if indicator_normalized in duplicates else ("matched" if indicator_match else "missing"),
                    "library_status": library_status_lookup.get(indicator_canonical, "not_started"),
                    "notes": "Duplicate name in payload" if indicator_normalized in duplicates else "",
                    "possible_match": ", ".join(possible_indicator_matches),
                })

        rows.append({
            "section_name": section["section_name"],
            "rows": section_rows,
        })

    extras = []
    for item in competencies:
        normalized = normalize_name(item.get("competency"))
        if normalized not in used_keys:
            extras.append(item)

    summary = {
        "total_expected": total_expected,
        "matched_count": matched_count,
        "missing_count": total_expected - matched_count,
        "duplicate_count": duplicate_count,
        "extra_count": len(extras),
    }

    return {
        "report_id": report_definition["report_id"],
        "report_name": report_definition["report_name"],
        "description": report_definition.get("description", ""),
        "summary": summary,
        "sections": rows,
        "extras": extras,
    }


def build_personality_reports_for_candidate(sova_activities, library_status_lookup=None):
    library_status_lookup = library_status_lookup or {}
    personality_activity = None

    for activity in sova_activities or []:
        activity_name = normalize_name(activity.get("activity"))
        competencies = activity.get("competencies", []) or []

        if "personality" in activity_name and competencies:
            personality_activity = activity
            break

    competencies = personality_activity.get("competencies", []) if personality_activity else []

    reports = []
    for report_definition in PERSONALITY_REPORT_DEFINITIONS:
        reports.append(
            build_report_table(
                report_definition=report_definition,
                competencies=competencies,
                library_status_lookup=library_status_lookup,
            )
        )

    return reports