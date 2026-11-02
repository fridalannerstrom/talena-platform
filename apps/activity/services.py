from .models import ActivityEvent

def log_event(*, company, verb, actor=None, actor_name="", process=None, candidate=None, invitation=None, meta=None):
    ActivityEvent.objects.create(
        company=company,
        verb=verb,
        actor=actor,
        actor_name=actor_name or "",
        process=process,
        candidate=candidate,
        invitation=invitation,
        meta=meta or {},
    )

def customer_visible_activity(queryset):
    """Keep removed project candidates out of customer activity surfaces.

    Their ActivityEvent records remain intact for Talena admin auditing.
    Check process+candidate (not just invitation) because some events,
    including CANDIDATE_REMOVED, do not store an invitation foreign key.
    """
    from django.db.models import Exists, OuterRef
    from apps.processes.models import TestInvitation

    removed_membership = TestInvitation.objects.filter(
        process_id=OuterRef("process_id"),
        candidate_id=OuterRef("candidate_id"),
        removed_from_process_at__isnull=False,
    )
    return queryset.alias(
        _removed_project_candidate=Exists(removed_membership),
    ).filter(_removed_project_candidate=False)
