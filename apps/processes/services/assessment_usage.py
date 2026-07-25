from django.utils import timezone

from apps.processes.models import AssessmentUsage


VALID_ASSESSMENT_TYPES = {
    "personality",
    "motivation",
    "verbal",
    "logical",
    "numerical",
}


COMPLETED_ACTIVITY_STATUSES = {
    "completed",
    "complete",
    "finished",
    "done",
    "result available",
    "result_available",
    "pass",
    "fail",
    "refer",
}


STARTED_ACTIVITY_STATUSES = {
    "started",
    "in progress",
    "in_progress",
}


def _normalise_text(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def _normalise_assessment_type(value):
    assessment_type = _normalise_text(value)

    if assessment_type in VALID_ASSESSMENT_TYPES:
        return assessment_type

    return None


def classify_sova_activity(activity_name):
    """
    Convert a Sova activity name into Talena's canonical
    assessment type.
    """

    name = _normalise_text(activity_name)

    if "personality" in name:
        return AssessmentUsage.AssessmentType.PERSONALITY

    if "motivation" in name:
        return AssessmentUsage.AssessmentType.MOTIVATION

    if "verbal" in name:
        return AssessmentUsage.AssessmentType.VERBAL

    if "logical" in name:
        return AssessmentUsage.AssessmentType.LOGICAL

    if "numerical" in name:
        return AssessmentUsage.AssessmentType.NUMERICAL

    # Do not create billing rows for unrelated Sova activities.
    return None


def classify_activity_status(status):
    """
    Convert a Sova activity status into Talena's lifecycle status.
    """

    normalised_status = _normalise_text(status)

    if normalised_status in COMPLETED_ACTIVITY_STATUSES:
        return AssessmentUsage.Status.COMPLETED

    if normalised_status in STARTED_ACTIVITY_STATUSES:
        return AssessmentUsage.Status.STARTED

    return None


def _candidate_name(candidate):
    name = (
        f"{candidate.first_name or ''} "
        f"{candidate.last_name or ''}"
    ).strip()

    return name or candidate.email or ""


def _project_name(process):
    return (
        process.project_name_snapshot
        or process.project_code
        or process.name
        or ""
    )


def _build_usage_defaults(
    *,
    invitation,
    assessment_type,
    sent_by=None,
    sent_at=None,
    sova_request_id="",
    sova_activity_id="",
    sova_activity_name="",
):
    process = invitation.process
    candidate = invitation.candidate

    effective_sent_at = (
        sent_at
        or invitation.invited_at
        or timezone.now()
    )

    return {
        "company": process.company,
        "org_unit": process.org_unit,
        "process": process,
        "candidate": candidate,

        "status": AssessmentUsage.Status.SENT,

        "sent_at": effective_sent_at,
        "sent_by": sent_by,

        "sova_request_id": (
            sova_request_id
            or invitation.request_id
            or ""
        ),

        "sova_activity_id": (
            str(sova_activity_id)
            if sova_activity_id
            else ""
        ),

        "sova_activity_name": (
            sova_activity_name or ""
        ),

        "company_name_snapshot": (
            process.company.name
            if process.company
            else ""
        ),

        "org_unit_name_snapshot": (
            process.org_unit.name
            if process.org_unit
            else ""
        ),

        "process_name_snapshot": (
            process.name or ""
        ),

        "project_name_snapshot": (
            _project_name(process)
        ),

        "candidate_name_snapshot": (
            _candidate_name(candidate)
        ),

        "candidate_email_snapshot": (
            candidate.email or ""
        ),
    }


def register_sent_assessments(
    *,
    invitation,
    sent_by,
    sent_at,
    sova_request_id="",
):
    """
    Register one AssessmentUsage row per assessment included
    in the process.

    Calling this function repeatedly does not create duplicates.
    """

    process = invitation.process

    if not process.company_id:
        return []

    assessment_types = []

    for raw_assessment_type in process.selected_tests or []:
        assessment_type = _normalise_assessment_type(
            raw_assessment_type
        )

        if not assessment_type:
            continue

        if assessment_type not in assessment_types:
            assessment_types.append(
                assessment_type
            )

    usages = []

    for assessment_type in assessment_types:
        usage, created = (
            AssessmentUsage.objects.get_or_create(
                invitation=invitation,
                assessment_type=assessment_type,
                defaults=_build_usage_defaults(
                    invitation=invitation,
                    assessment_type=assessment_type,
                    sent_by=sent_by,
                    sent_at=sent_at,
                    sova_request_id=sova_request_id,
                ),
            )
        )

        if not created:
            update_fields = []

            if usage.sent_at is None:
                usage.sent_at = sent_at
                update_fields.append("sent_at")

            if usage.sent_by_id is None and sent_by:
                usage.sent_by = sent_by
                update_fields.append("sent_by")

            if (
                not usage.sova_request_id
                and sova_request_id
            ):
                usage.sova_request_id = (
                    sova_request_id
                )
                update_fields.append(
                    "sova_request_id"
                )

            # Never move a started or completed test backwards.
            if usage.status not in {
                AssessmentUsage.Status.STARTED,
                AssessmentUsage.Status.COMPLETED,
            }:
                usage.status = (
                    AssessmentUsage.Status.SENT
                )
                update_fields.append("status")

            if update_fields:
                usage.save(
                    update_fields=list(
                        dict.fromkeys(update_fields)
                    )
                )

        usages.append(usage)

    return usages


def sync_assessment_usage_from_activities(
    *,
    invitation,
    activities,
    observed_at=None,
):
    """
    Update the individual AssessmentUsage rows using the latest
    activity statuses received from Sova.

    Sova does not currently provide an individual timestamp for
    each status change in the payloads we receive. Talena therefore
    records the first time the status is observed by the webhook.

    Completed rows are never downgraded.
    Existing timestamps are never overwritten.
    """

    observed_at = observed_at or timezone.now()

    process = invitation.process

    if not process.company_id:
        return []

    # Ensure the normal sent rows exist first.
    register_sent_assessments(
        invitation=invitation,
        sent_by=invitation.invited_by,
        sent_at=(
            invitation.invited_at
            or observed_at
        ),
        sova_request_id=(
            invitation.request_id
            or ""
        ),
    )

    synced_usages = []

    for activity in activities or []:
        if not isinstance(activity, dict):
            continue

        activity_name = (
            activity.get("activity")
            or activity.get("name")
            or ""
        )

        assessment_type = classify_sova_activity(
            activity_name
        )

        if not assessment_type:
            continue

        lifecycle_status = classify_activity_status(
            activity.get("status")
        )

        activity_id = (
            activity.get("activity_id")
            or activity.get("activityId")
            or activity.get("id")
            or ""
        )

        usage, created = (
            AssessmentUsage.objects.get_or_create(
                invitation=invitation,
                assessment_type=assessment_type,
                defaults=_build_usage_defaults(
                    invitation=invitation,
                    assessment_type=assessment_type,
                    sent_by=invitation.invited_by,
                    sent_at=(
                        invitation.invited_at
                        or observed_at
                    ),
                    sova_request_id=(
                        invitation.request_id
                        or ""
                    ),
                    sova_activity_id=activity_id,
                    sova_activity_name=activity_name,
                ),
            )
        )

        update_fields = []

        if (
            activity_name
            and usage.sova_activity_name != activity_name
        ):
            usage.sova_activity_name = activity_name
            update_fields.append(
                "sova_activity_name"
            )

        if (
            activity_id
            and not usage.sova_activity_id
        ):
            usage.sova_activity_id = str(
                activity_id
            )
            update_fields.append(
                "sova_activity_id"
            )

        if (
            not usage.sova_request_id
            and invitation.request_id
        ):
            usage.sova_request_id = (
                invitation.request_id
            )
            update_fields.append(
                "sova_request_id"
            )

        if (
            lifecycle_status
            == AssessmentUsage.Status.COMPLETED
        ):
            if usage.started_at is None:
                usage.started_at = observed_at
                update_fields.append(
                    "started_at"
                )

            if usage.completed_at is None:
                usage.completed_at = observed_at
                usage.completed_at_is_estimated = False

                update_fields.extend(
                    [
                        "completed_at",
                        "completed_at_is_estimated",
                    ]
                )

            if (
                usage.status
                != AssessmentUsage.Status.COMPLETED
            ):
                usage.status = (
                    AssessmentUsage.Status.COMPLETED
                )
                update_fields.append("status")

        elif (
            lifecycle_status
            == AssessmentUsage.Status.STARTED
        ):
            # A later webhook must never move completed
            # usage back to started.
            if (
                usage.status
                != AssessmentUsage.Status.COMPLETED
            ):
                if usage.started_at is None:
                    usage.started_at = observed_at
                    update_fields.append(
                        "started_at"
                    )

                if (
                    usage.status
                    != AssessmentUsage.Status.STARTED
                ):
                    usage.status = (
                        AssessmentUsage.Status.STARTED
                    )
                    update_fields.append("status")

        if update_fields:
            usage.save(
                update_fields=list(
                    dict.fromkeys(update_fields)
                )
            )

        synced_usages.append(usage)

    return synced_usages