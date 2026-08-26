"""Process locking rules that account for persisted SOVA orders.

A SOVA assessment can exist even when invitation email delivery failed. In
that case TestInvitation.status may be ``failed`` while ``assessment_url`` is
already persisted. The process must still behave as started: its assessment
package must not change and the process must not be deleted.
"""


def has_ordered_assessments(process) -> bool:
    """Return True once at least one SOVA assessment URL has been persisted."""
    if not process or not getattr(process, "pk", None):
        return False

    return (
        process.invitations
        .exclude(assessment_url__isnull=True)
        .exclude(assessment_url="")
        .exists()
    )


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
