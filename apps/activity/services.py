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
    ).filter(_removed_project_candidate=False).exclude(verb__in=[
        ActivityEvent.Verb.AI_CALL_SUCCEEDED,
        ActivityEvent.Verb.AI_CALL_FAILED,
        ActivityEvent.Verb.AI_CALL_INCOMPLETE,
    ])


# The candidate card is a journey timeline, not an administrative audit log.
# Keep the full ActivityEvent store unchanged for authorized admin history,
# PDF reports, AI actions, and other project-level activity views.
CANDIDATE_TIMELINE_VERBS = frozenset((
    ActivityEvent.Verb.CANDIDATE_ADDED,
    ActivityEvent.Verb.INVITE_SENT,
    ActivityEvent.Verb.TEST_STARTED,
    ActivityEvent.Verb.TEST_COMPLETED,
    ActivityEvent.Verb.ALL_TESTS_COMPLETED,
    ActivityEvent.Verb.STATUS_CHANGED,
    ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_SENT,
    ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_FAILED,
    ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
    ActivityEvent.Verb.CANDIDATE_RESULT_FEEDBACK_SUBMITTED,
))


def candidate_journey_activity(queryset):
    """Events to show in the candidate-card activity tab.

    Apply this before slicing so multiple PDF exports never displace older
    invitations and assessment milestones from the visible timeline.
    Do not apply this filter to full admin audit history or project activity.
    """
    return queryset.filter(verb__in=CANDIDATE_TIMELINE_VERBS)
