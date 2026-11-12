"""Process locking rules that account for persisted SOVA orders.

A SOVA assessment can exist even when invitation email delivery failed. In
that case TestInvitation.status may be ``failed`` while ``assessment_url`` is
already persisted. The process must still behave as started: its assessment
package must not change and the process must not be deleted.
"""


def has_ordered_assessments(process) -> bool:
    """True for persisted Sova orders, including failed deliveries without URLs."""
    if not process or not getattr(process, "pk", None):
        return False

    from django.db.models import Q

    if (
        process.invitations
        .exclude(assessment_url__isnull=True)
        .exclude(assessment_url="")
        .exists()
    ):
        return True

    # A failed email/order can still have a real Sova reference but no URL.
    # Keep this protection even after the project membership was soft-removed.
    return process.invitations.filter(
        (Q(request_id__isnull=False) & ~Q(request_id=""))
        | (Q(sova_request_id__isnull=False) & ~Q(sova_request_id=""))
        | (Q(sova_invitation_id__isnull=False) & ~Q(sova_invitation_id=""))
        | (Q(sova_payload__isnull=False) & ~Q(sova_payload={}))
        | Q(assessment_usages__isnull=False)
    ).exists()


def is_test_package_locked(process) -> bool:
    """Keep the assessment package immutable after any real assessment order."""
    if not process or not getattr(process, "pk", None):
        return False

    return bool(
        process.is_template_locked()
        or has_ordered_assessments(process)
    )


def can_delete_process_safely(process) -> bool:
    """A process with a persisted SOVA assessment must never be deleted."""
    if not process or not getattr(process, "pk", None):
        return False

    return bool(
        process.can_delete()
        and not has_ordered_assessments(process)
    )
