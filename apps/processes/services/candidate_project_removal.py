"""Remove a candidate from one project without erasing ordered Sova data.

A removed invitation remains available to internal retention/billing and Sova
callbacks, but is no longer part of the customer's active project workflow.
This never claims that a provider-side test link was cancelled.
"""
from django.db import transaction
from django.utils import timezone

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event
from apps.candidate_results.models import CandidateResultAccess
from apps.processes.models import TestInvitation


def has_assessment_history(invitation):
    """Conservative: an order can exist even after email delivery failed."""
    return bool(
        invitation.assessment_url
        or invitation.sova_request_id
        or invitation.request_id
        or invitation.sova_candidate_id
        or invitation.sova_project_id
        or invitation.sova_invitation_id
        or invitation.sova_payload
        or invitation.project_results
        or invitation.result_payload
        or invitation.sova_reports
        or invitation.sova_activities
        or invitation.sova_phases
        or invitation.status in ("sent", "started", "completed", "expired")
        or invitation.assessment_usages.exists()
    )


@transaction.atomic
def remove_candidate_from_project(*, invitation, actor):
    """Remove only this project membership, retain protected order/history.

    Returns 'removed_unsent', 'hidden', or 'already_removed'. Provider cancellation
    is deliberately NOT attempted without a verified, authorised Sova API.
    """
    inv = (
        TestInvitation.objects.select_for_update()
        .select_related("process__company", "candidate")
        .get(pk=invitation.pk, process_id=invitation.process_id)
    )
    if inv.removed_from_process_at:
        return "already_removed"

    company = inv.process.company
    candidate = inv.candidate
    ordered = has_assessment_history(inv)
    inv.removed_from_process_at = timezone.now()
    inv.sova_revocation_state = "manual_pending" if ordered else "not_required"
    inv.save(update_fields=["removed_from_process_at", "sova_revocation_state"])
    # Candidate-facing report URLs and verification codes must stop working.
    CandidateResultAccess.objects.filter(
        snapshot__inv, revoked_at__isnull=True
    ).update(revoked_at=inv.removed_from_process_at)
    outcome = "hidden" if ordered else "removed_unsent"

    log_event(
        company=company,
        verb=ActivityEvent.Verb.CANDIDATE_REMOVED,
        actor=actor,
        process=inv.process,
        candidate=candidate,
        meta={
            "project_removal": outcome,
            "sova_access_revocation": (
                "manual_pending" if outcome == "hidden" else "not_required"
            ),
        },
    )
    return outcome
