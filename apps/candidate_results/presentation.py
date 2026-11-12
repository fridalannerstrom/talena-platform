from apps.emails.models import EmailLog
from apps.activity.models import ActivityEvent

from .audit import (
    CANDIDATE_RESULT_ACTIVITY_VERBS,
    log_candidate_result_access_expired,
)
from .content import ensure_candidate_result_snapshot_current
from .models import CandidateResultAccess, CandidateResultSnapshot


def _build_candidate_result_reflections(snapshot) -> dict:
    """Build status data from the exact frozen text shown to the candidate."""
    if snapshot is None:
        return {}

    content = snapshot.content if isinstance(snapshot.content, dict) else {}
    feedback_by_area = {
        feedback.result_area: feedback
        for feedback in snapshot.feedback.all()
    }
    area_map = {
        "personality": "personality",
        "motivation": "motivation",
        "cognitive": "skills",
    }
    reflections = {}

    for recruiter_area, candidate_area in area_map.items():
        section = content.get(candidate_area)
        if not isinstance(section, dict):
            continue

        body = str(section.get("body") or "").strip()
        points = [
            str(point).strip()
            for point in section.get("points") or []
            if str(point).strip()
        ]
        groups = []
        for group in section.get("groups") or []:
            if not isinstance(group, dict):
                continue
            items = []
            for item in group.get("items") or []:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                text = str(item.get("text") or "").strip()
                if label or text:
                    items.append({"label": label, "text": text})
            title = str(group.get("title") or "").strip()
            if title or items:
                groups.append({"title": title, "items": items})

        if not body and not points and not groups:
            continue

        feedback = feedback_by_area.get(candidate_area)
        reflections[recruiter_area] = {
            "title": str(section.get("title") or candidate_area.title()).strip(),
            "body": body,
            "points": points,
            "groups": groups,
            "has_feedback": feedback is not None,
            "submitted_at": feedback.created_at if feedback else None,
            "response": feedback.response if feedback else "",
            "comment": (feedback.comment or "").strip() if feedback else "",
            "locale": snapshot.locale,
        }

    return reflections


def build_candidate_result_panel_context(process, invitation) -> dict:
    """Return the shared candidate-report snapshot, feedback and status data."""
    snapshot = (
        CandidateResultSnapshot.objects
        .filter(invitation=invitation)
        .prefetch_related("feedback")
        .first()
    )
    if snapshot:
        snapshot, _upgraded = ensure_candidate_result_snapshot_current(snapshot)

    sharing_enabled = bool(getattr(process, "candidate_results_enabled", False))
    reflections = (
        _build_candidate_result_reflections(snapshot)
        if sharing_enabled
        else {}
    )
    feedback_count = sum(
        1 for reflection in reflections.values() if reflection["has_feedback"]
    )
    feedback_total = len(reflections)
    if feedback_count == 0:
        feedback_status = "not_started"
    elif feedback_count == feedback_total:
        feedback_status = "submitted"
    else:
        feedback_status = "in_progress"
    last_feedback_at = max(
        (
            reflection["submitted_at"]
            for reflection in reflections.values()
            if reflection["submitted_at"]
        ),
        default=None,
    )

    access = None
    latest_email = None
    if snapshot:
        access = CandidateResultAccess.objects.filter(snapshot=snapshot).first()
        if access:
            log_candidate_result_access_expired(access)
        latest_email = (
            EmailLog.objects
            .filter(invitation=invitation, template_type="candidate_result")
            .order_by("-created_at", "-id")
            .first()
        )

    if access is None:
        access_state = "not_created"
    elif access.revoked_at:
        access_state = "revoked"
    elif access.is_expired():
        access_state = "expired"
    else:
        access_state = "active"

    status = {
        "sharing_enabled": sharing_enabled,
        "snapshot_ready": snapshot is not None,
        "email_status": latest_email.status if latest_email else "not_sent",
        "email_sent_at": latest_email.sent_at if latest_email else None,
        "email_created_at": latest_email.created_at if latest_email else None,
        "opened_at": access.last_accessed_at if access else None,
        "expires_at": access.expires_at if access else None,
        "revoked_at": access.revoked_at if access else None,
        "access_state": access_state,
        "feedback_count": feedback_count,
        "feedback_total": feedback_total,
        "feedback_status": feedback_status,
        "last_feedback_at": last_feedback_at,
    }
    activity_events = list(
        ActivityEvent.objects
        .filter(
            invitation=invitation,
            verb__in=CANDIDATE_RESULT_ACTIVITY_VERBS,
        )
        .select_related("actor", "candidate", "process", "company")
        .order_by("-created_at")[:20]
    )

    return {
        "candidate_result_snapshot": snapshot,
        "candidate_result_reflections": reflections,
        "candidate_result_reflections_enabled": bool(
            sharing_enabled and snapshot and reflections
        ),
        "candidate_result_status": status,
        "candidate_result_activity": activity_events,
    }
