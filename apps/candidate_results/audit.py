from apps.activity.models import ActivityEvent
from apps.activity.services import log_event


CANDIDATE_RESULT_ACTIVITY_VERBS = (
    ActivityEvent.Verb.CANDIDATE_RESULT_SNAPSHOT_CREATED,
    ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_SENT,
    ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_FAILED,
    ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
    ActivityEvent.Verb.CANDIDATE_RESULT_CODE_VERIFIED,
    ActivityEvent.Verb.CANDIDATE_RESULT_CODE_FAILED,
    ActivityEvent.Verb.CANDIDATE_RESULT_FEEDBACK_SUBMITTED,
    ActivityEvent.Verb.CANDIDATE_RESULT_CODE_REPLACED,
    ActivityEvent.Verb.CANDIDATE_RESULT_ACCESS_REVOKED,
    ActivityEvent.Verb.CANDIDATE_RESULT_ACCESS_EXPIRED,
)


def log_candidate_result_event(
    invitation,
    *,
    verb,
    actor=None,
    actor_name="",
    meta=None,
):
    return log_event(
        company=invitation.process.company,
        verb=verb,
        actor=actor,
        actor_name=actor_name or ("Talena" if actor is None else ""),
        process=invitation.process,
        candidate=invitation.candidate,
        invitation=invitation,
        meta=meta or {},
    )


def _access_event_key(access):
    return {
        "access_id": access.pk,
        "access_expires_at": (
            access.expires_at.isoformat() if access.expires_at else ""
        ),
    }


def log_candidate_result_open_once(access):
    from apps.activity.models import ActivityEvent

    meta = _access_event_key(access)
    exists = ActivityEvent.objects.filter(
        invitation=access.snapshot.invitation,
        verb=ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
        meta__access_id=meta["access_id"],
        meta__access_expires_at=meta["access_expires_at"],
    ).exists()
    if not exists:
        return log_candidate_result_event(
            access.snapshot.invitation,
            verb=ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
            meta=meta,
        )
    return None


def log_candidate_result_access_expired(access, *, now=None):
    from django.utils import timezone
    from apps.activity.models import ActivityEvent

    now = now or timezone.now()
    if access.revoked_at or not access.is_expired(now):
        return None

    meta = _access_event_key(access)
    exists = ActivityEvent.objects.filter(
        invitation=access.snapshot.invitation,
        verb=ActivityEvent.Verb.CANDIDATE_RESULT_ACCESS_EXPIRED,
        meta__access_id=meta["access_id"],
        meta__access_expires_at=meta["access_expires_at"],
    ).exists()
    if not exists:
        return log_candidate_result_event(
            access.snapshot.invitation,
            verb=ActivityEvent.Verb.CANDIDATE_RESULT_ACCESS_EXPIRED,
            meta=meta,
        )
    return None
