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