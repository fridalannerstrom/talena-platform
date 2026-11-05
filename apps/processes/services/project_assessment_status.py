"""Per-assessment project status display, based on Sova evidence (#367).

Never infer a specific test's completion from the invitation's overall status.
Each status is scoped to one project's invitation and (where available)
independently recorded Sova activity or AssessmentUsage record.
"""
import re

from apps.processes.services.process_recommendations import (
    TEST_ORDER, extract_tests_from_project_name,
)

LABELS = {
    "personality": ("Personlighet", "Personality"),
    "motivation": ("Motivation", "Motivation"),
    "logical": ("Logiskt", "Logical"),
    "numerical": ("Numeriskt", "Numerical"),
    "verbal": ("Verbalt", "Verbal"),
}
# User-facing explanations are intentionally short and avoid internal Sova
# terminology. Status distinctions are preserved in the machine-readable state.
LABELS_STATUS = {
    "not_sent": ("Ej skickat", "Not sent", "Testet har inte skickats.", "The test has not been sent."),
    "not_started": ("Inte påbörjat", "Not started", "Kandidaten har inte påbörjat testet.", "The candidate has not started the test."),
    "started": ("Påbörjat", "Started", "Kandidaten har påbörjat testet.", "The candidate has started the test."),
    "completed": ("Genomfört", "Completed", "Kandidaten har genomfört testet.", "The candidate has completed the test."),
    "invited": ("Skickat", "Sent", "Testet är skickat till kandidaten.", "The test has been sent to the candidate."),
    "expired": ("Utgånget", "Expired", "Inbjudan har gått ut.", "The invitation has expired."),
    "failed": ("Kunde inte skickas", "Could not be sent", "Inbjudan kunde inte skickas.", "The invitation could not be sent."),
    "activity_failed": ("Fel vid testet", "Test error", "Ett fel har rapporterats för testet.", "An error was reported for the test."),
    "not_assigned": ("Ej tilldelat", "Not assigned", "Testet har inte tilldelats kandidaten.", "The candidate has not been assigned this test."),
    "unknown": ("Status saknas", "Status unavailable", "Vi saknar information om testets status.", "No status information is available for this test."),
}

# Presentation-only, stroke-based SVG paths for compact status indicators.
# These are fixed server-owned icons, never derived from Sova payloads.
ICON_PATHS = {
    # An envelope with a small clock: the invitation is awaiting dispatch.
    # Unlike a paper plane, this must not suggest that it was already sent.
    "not_sent": (
        "M18 9V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7 "
        "M2 7l9 6 7-5 "
        "M20 17a4 4 0 1 1-8 0 4 4 0 0 1 8 0 "
        "M16 15v2l1.5 1"
    ),
    "not_started": "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20 M12 7v5l3 2",
    "started": "M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20 M10 8l6 4-6 4Z",
    "completed": "M5 12l5 5L20 7",
    "invited": "M4 5h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z M2 7l10 7 10-7",
    "expired": "M6 3h12 M6 21h12 M8 3c0 5 4 6 4 9s-4 4-4 9 M16 3c0 5-4 6-4 9s4 4 4 9",
    "failed": "M12 3 2 21h20L12 3Z M12 9v4 M12 17h.01",
    "activity_failed": "M5 5l14 14 M19 5 5 19",
    "not_assigned": "M5 12h14",
    "unknown": "M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2.5-2.5 5 M12 18h.01",
}

ORDER = tuple(key for key in TEST_ORDER if key in LABELS)
RANK = {"unknown": 0, "not_started": 1, "started": 2, "completed": 3}
STATUSES = {
    "not started": "not_started", "not_started": "not_started",
    "not begun": "not_started", "pending": "not_started", "invited": "not_started",
    "sent": "not_started", "created": "not_started", "ready": "not_started",
    "in progress": "started", "in_progress": "started", "started": "started",
    "ongoing": "started", "inprogress": "started",
    "complete": "completed", "completed": "completed", "finished": "completed",
    "done": "completed", "result available": "completed", "result_available": "completed",
    "pass": "completed", "passed": "completed", "fail": "completed", "refer": "completed",
    "expired": "expired", "cancelled": "expired", "canceled": "expired",
    "not assigned": "not_assigned", "not_assigned": "not_assigned",
    "not applicable": "not_assigned",
    "error": "activity_failed", "failed": "activity_failed",
}


def test_key(value):
    """Conservative Sova/Talena aliases, including Modern Projects codes."""
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    text = re.sub(r"[_\-/+|]+", " ", raw)
    text = " ".join(text.split())
    for name, aliases in {
        "personality": ("personality", "personlighet", "pq"),
        "motivation": ("motivation", "mq"),
        "logical": ("logical", "logiskt", "logisk", "logic", "l"),
        "numerical": ("numerical", "numeric", "numerisk", "numeriskt", "n"),
        "verbal": ("verbal", "verbalt", "v"),
    }.items():
        for alias in aliases:
            if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text):
                return name
    return None


def project_test_columns(process, meta=None):
    selected = getattr(process, "selected_tests", None) or []
    if isinstance(selected, str):
        selected = re.split(r"[,;+|/]", selected)
    keys = {key for raw in selected if (key := test_key(raw))}
    if not keys and meta is not None:
        keys = {key for raw in (getattr(meta, "tests", "") or "").split(",")
                if (key := test_key(raw))}
    if not keys:
        keys = set(extract_tests_from_project_name(
            getattr(process, "project_name_snapshot", "") or
            getattr(process, "sova_project_name", "") or ""
        ))
    return [{"key": key, "sv": LABELS[key][0], "en": LABELS[key][1]}
            for key in ORDER if key in keys]


def _activity_rows(invitation):
    """Use persisted callback activities, then raw saved Sova payloads."""
    activities = getattr(invitation, "sova_activities", None) or []
    if activities:
        return [a for a in activities if isinstance(a, dict)]
    payload = getattr(invitation, "sova_payload", None) or {}
    if not isinstance(payload, dict):
        payload = {}
    rows = payload.get("activities") or []
    if rows:
        return [a for a in rows if isinstance(a, dict)]
    phases = getattr(invitation, "sova_phases", None) or payload.get("phases") or []
    return [a for phase in phases if isinstance(phase, dict)
            for a in (phase.get("activities") or []) if isinstance(a, dict)]


def _normalized_status(value):
    raw = str(value or "").strip().lower().replace("-", " ")
    return STATUSES.get(raw, "unknown")


def _cell(key, state, language):
    sv = str(language or "").lower().startswith("sv")
    label_sv, label_en, help_sv, help_en = LABELS_STATUS[state]
    return {
        "key": key, "state": state,
        "label": label_sv if sv else label_en,
        "title": help_sv if sv else help_en,
        "tone": ("success" if state == "completed" else
                 "info" if state == "started" else
                 "warning" if state in ("expired", "failed", "activity_failed") else
                 "muted"),
        "icon_path": ICON_PATHS[state],
        "icon": ("✓" if state == "completed" else
                 "◷" if state == "started" else
                 "!" if state in ("expired", "failed", "activity_failed") else "•"),
    }


def invitation_test_statuses(invitation, columns, language="sv"):
    """Statuses for exactly the current invitation/project, never other projects."""
    states = {column["key"]: None for column in columns}
    # Raw Sova per-activity evidence has priority over invitation lifecycle.
    for activity in _activity_rows(invitation):
        key = test_key(
            activity.get("activity") or activity.get("name")
            or activity.get("activity_name") or activity.get("activityName")
            or activity.get("code")
        )
        if key not in states:
            continue
        status = _normalized_status(
            activity.get("status") or activity.get("activity_status")
            or activity.get("currentStatus") or activity.get("current_status")
        )
        previous = states[key]
        if status in RANK and (previous not in RANK or RANK[status] > RANK[previous]):
            states[key] = status
        elif status in ("expired", "activity_failed", "not_assigned") and previous is None:
            states[key] = status
        elif previous is None:
            states[key] = "unknown"

    usages = getattr(invitation, "_prefetched_objects_cache", {}).get("assessment_usages")
    if usages is None:
        # The caller prefetches usages for N+1 safety. Unsaved unit-test
        # invitations may pass a related list directly.
        usages = getattr(invitation, "status_usages", []) or []
    for usage in usages:
        key = test_key(getattr(usage, "assessment_type", ""))
        if key not in states:
            continue
        state = str(getattr(usage, "status", "")).lower()
        current = states[key]

        # A recorded AssessmentUsage is evidence about THIS test, not the
        # invitation's global status. Sova callbacks can be partial and can
        # include placeholders ("unknown"/"not started") for other activities.
        # These must not erase an independently confirmed sent test.
        # Keep explicit failures, expiration and "not assigned" as-is.
        if current in ("expired", "activity_failed", "not_assigned"):
            continue
        if state == "completed" and not getattr(usage, "completed_at_is_estimated", False):
            states[key] = "completed"
        elif state == "started" and current != "completed":
            states[key] = "started"
        elif state == "sent" and current in (None, "unknown", "not_started"):
            states[key] = "invited"

    invitation_status = (getattr(invitation, "status", "") or "").lower()
    assigned = invitation_status not in ("created", "") or bool(
        getattr(invitation, "invited_at", None))
    for key, state in states.items():
        if state is None:
            if invitation_status == "expired":
                state = "expired"
            elif invitation_status == "failed":
                state = "failed"
            elif not assigned:
                state = "not_sent"
            else:
                state = "unknown"
        states[key] = state
    cells = [_cell(column["key"], states[column["key"]], language)
             for column in columns]

    # #447: Use exactly the same persisted Sova percentile extraction as the
    # candidate's Skills > Results view. Never infer values from overall status
    # and never display a number for a test not independently completed.
    completed_cognitive = {
        cell["key"] for cell in cells
        if cell["state"] == "completed"
        and cell["key"] in {"logical", "numerical", "verbal"}
    }
    percentiles = {}
    if completed_cognitive:
        from apps.core.ai.cognitive_interpretation import extract_cognitive_results
        for result in extract_cognitive_results(invitation):
            key = result.get("key")
            if key in completed_cognitive and key not in percentiles:
                percentiles[key] = result["percentile"]

    is_swedish = str(language or "").lower().startswith("sv")
    for cell in cells:
        percentile = percentiles.get(cell["key"])
        cell["percentile"] = percentile
        cell["has_percentile"] = percentile is not None
        if percentile is not None:
            if is_swedish:
                ordinal = "a" if percentile % 10 in (1, 2) and percentile % 100 not in (11, 12) else "e"
                cell["title"] = f"{percentile}:{ordinal} percentilen. Visa resultat."
            else:
                ordinal = "th" if 10 <= percentile % 100 <= 20 else {
                    1: "st", 2: "nd", 3: "rd",
                }.get(percentile % 10, "th")
                cell["title"] = f"{percentile}{ordinal} percentile. View results."
    return cells


def attach_test_statuses(invitations, columns, language):
    """Decorate an already scoped invitation collection for Django templates."""
    for invitation in invitations:
        invitation.assessment_status_cells = invitation_test_statuses(
            invitation, columns, language)
    return invitations
