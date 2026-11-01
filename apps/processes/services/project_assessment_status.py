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
LABELS_STATUS = {
    "not_sent": ("Ej skickat", "Not sent", "Utskicket är inte gjort.", "The invitation has not been sent."),
    "not_started": ("Inte påbörjat", "Not started", "Sova rapporterar att testet inte är påbörjat.", "Sova reports that the assessment has not started."),
    "started": ("Påbörjat", "Started", "Sova rapporterar att testet har påbörjats.", "Sova reports that the assessment has started."),
    "completed": ("Genomfört", "Completed", "Sova rapporterar att testet har genomförts.", "Sova reports that the assessment has been completed."),
    "invited": ("Inbjuden", "Invited", "Testet är tilldelat, men individuell startstatus saknas.", "Assigned assessment; individual start status is unavailable."),
    "expired": ("Utgånget", "Expired", "Inbjudan har gått ut; testets individuella status är inte känd.", "Invitation expired; individual assessment status is unknown."),
    "failed": ("Utskick misslyckades", "Delivery failed", "Utskicket misslyckades; testets status är inte känd.", "Invitation delivery failed; individual status is unknown."),
    "activity_failed": ("Misslyckat", "Failed", "Sova har rapporterat att den här aktiviteten misslyckades.", "Sova reported that this activity failed."),
    "not_assigned": ("Ej tilldelat", "Not assigned", "Inget test av denna typ har tilldelats.", "No assessment of this type has been assigned."),
    "unknown": ("Okänt", "Unknown", "Ingen verifierad individuell teststatus finns från Sova.", "No verified individual Sova assessment status is available."),
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
        if key not in states or states[key] in ("completed", "started", "not_started"):
            continue
        state = str(getattr(usage, "status", "")).lower()
        if state == "completed" and not getattr(usage, "completed_at_is_estimated", False):
            states[key] = "completed"
        elif state == "started":
            states[key] = "started"
        elif state == "sent" and states[key] is None:
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
    return [_cell(column["key"], states[column["key"]], language)
            for column in columns]


def attach_test_statuses(invitations, columns, language):
    """Decorate an already scoped invitation collection for Django templates."""
    for invitation in invitations:
        invitation.assessment_status_cells = invitation_test_statuses(
            invitation, columns, language)
    return invitations
