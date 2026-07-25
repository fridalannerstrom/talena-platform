from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.processes.models import (
    AssessmentUsage,
    TestInvitation,
)
from apps.processes.services.assessment_usage import (
    classify_activity_status,
    classify_sova_activity,
    register_sent_assessments,
)


class Command(BaseCommand):
    help = (
        "Create AssessmentUsage records for existing "
        "Sova test invitations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Run the backfill and display the result "
                "without saving any database changes."
            ),
        )

        parser.add_argument(
            "--invitation-id",
            type=int,
            help=(
                "Only backfill one TestInvitation. "
                "Useful when testing the command."
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            help=(
                "Limit the number of invitations processed."
            ),
        )

        parser.add_argument(
            "--include-completed-fallback",
            action="store_true",
            help=(
                "Use the invitation-level completed_at value "
                "for completed assessment activities. "
                "This may be less precise than individual "
                "assessment completion timestamps."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        invitation_id = options.get(
            "invitation_id"
        )

        limit = options.get("limit")

        include_completed_fallback = options[
            "include_completed_fallback"
        ]

        invitations = (
            TestInvitation.objects
            .select_related(
                "process",
                "process__company",
                "process__org_unit",
                "candidate",
                "invited_by",
            )
            .exclude(source="historical")
            .exclude(process__is_historical=True)
            .filter(process__company__isnull=False)
            .filter(
                Q(invited_at__isnull=False)
                | Q(
                    status__in=[
                        "sent",
                        "started",
                        "completed",
                    ]
                )
            )
            .order_by("id")
        )

        if invitation_id:
            invitations = invitations.filter(
                id=invitation_id
            )

        if limit:
            invitations = invitations[:limit]

        invitation_count = 0
        created_usage_count = 0
        updated_usage_count = 0
        skipped_invitation_count = 0
        unmatched_activity_count = 0
        uncertain_completion_count = 0

        with transaction.atomic():
            for invitation in invitations:
                process = invitation.process

                selected_tests = (
                    process.selected_tests
                    or []
                )

                activities = (
                    invitation.sova_activities
                    or []
                )

                if (
                    not selected_tests
                    and not activities
                ):
                    skipped_invitation_count += 1
                    continue

                invitation_count += 1

                existing_count = (
                    invitation
                    .assessment_usages
                    .count()
                )

                sent_at = (
                    invitation.invited_at
                    or invitation.created_at
                )

                register_sent_assessments(
                    invitation=invitation,
                    sent_by=invitation.invited_by,
                    sent_at=sent_at,
                    sova_request_id=(
                        invitation.request_id
                        or ""
                    ),
                )

                new_count = (
                    invitation
                    .assessment_usages
                    .count()
                )

                created_usage_count += max(
                    new_count - existing_count,
                    0,
                )

                for activity in activities:
                    if not isinstance(
                        activity,
                        dict,
                    ):
                        continue

                    activity_name = (
                        activity.get("activity")
                        or activity.get("name")
                        or ""
                    )

                    assessment_type = (
                        classify_sova_activity(
                            activity_name
                        )
                    )

                    if not assessment_type:
                        continue

                    lifecycle_status = (
                        classify_activity_status(
                            activity.get("status")
                        )
                    )

                    activity_id = (
                        activity.get("activity_id")
                        or activity.get("activityId")
                        or activity.get("id")
                        or ""
                    )

                    candidate = invitation.candidate

                    candidate_name = (
                        f"{candidate.first_name or ''} "
                        f"{candidate.last_name or ''}"
                    ).strip()

                    if not candidate_name:
                        candidate_name = (
                            candidate.email or ""
                        )

                    project_name = (
                        process.project_name_snapshot
                        or process.project_code
                        or process.name
                        or ""
                    )

                    usage, usage_created = (
                        AssessmentUsage.objects.get_or_create(
                            invitation=invitation,
                            assessment_type=assessment_type,
                            defaults={
                                "company": process.company,
                                "org_unit": process.org_unit,
                                "process": process,
                                "candidate": candidate,

                                "status": (
                                    AssessmentUsage
                                    .Status
                                    .SENT
                                ),

                                "sent_at": sent_at,
                                "sent_by": (
                                    invitation.invited_by
                                ),

                                "sova_request_id": (
                                    invitation.request_id
                                    or ""
                                ),

                                "sova_activity_id": (
                                    str(activity_id)
                                    if activity_id
                                    else ""
                                ),

                                "sova_activity_name": (
                                    activity_name or ""
                                ),

                                "company_name_snapshot": (
                                    process.company.name
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
                                    project_name
                                ),

                                "candidate_name_snapshot": (
                                    candidate_name
                                ),

                                "candidate_email_snapshot": (
                                    candidate.email or ""
                                ),
                            },
                        )
                    )

                    if usage_created:
                        created_usage_count += 1

                    update_fields = []

                    if (
                        activity_name
                        and (
                            usage.sova_activity_name
                            != activity_name
                        )
                    ):
                        usage.sova_activity_name = (
                            activity_name
                        )
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
                        lifecycle_status
                        == AssessmentUsage.Status.STARTED
                    ):
                        if usage.status not in {
                            AssessmentUsage.Status.STARTED,
                            AssessmentUsage.Status.COMPLETED,
                        }:
                            usage.status = (
                                AssessmentUsage.Status.STARTED
                            )
                            update_fields.append("status")

                        if (
                            usage.started_at is None
                            and (
                                invitation.started_at
                                is not None
                            )
                        ):
                            usage.started_at = (
                                invitation.started_at
                            )
                            update_fields.append(
                                "started_at"
                            )

                    elif (
                        lifecycle_status
                        == (
                            AssessmentUsage
                            .Status
                            .COMPLETED
                        )
                    ):
                        if (
                            include_completed_fallback
                            and (
                                invitation.completed_at
                                is not None
                            )
                        ):
                            if (
                                usage.status
                                != (
                                    AssessmentUsage
                                    .Status
                                    .COMPLETED
                                )
                            ):
                                usage.status = (
                                    AssessmentUsage
                                    .Status
                                    .COMPLETED
                                )
                                update_fields.append(
                                    "status"
                                )

                            if usage.started_at is None:
                                usage.started_at = (
                                    invitation.started_at
                                    or invitation.completed_at
                                )
                                update_fields.append(
                                    "started_at"
                                )

                            if usage.completed_at is None:
                                usage.completed_at = (
                                    invitation.completed_at
                                )

                                usage.completed_at_is_estimated = (
                                    True
                                )

                                update_fields.extend(
                                    [
                                        "completed_at",
                                        (
                                            "completed_at_"
                                            "is_estimated"
                                        ),
                                    ]
                                )

                        else:
                            uncertain_completion_count += 1

                            # Preserve the known started state
                            # without inventing a completion date.
                            if usage.status not in {
                                AssessmentUsage.Status.STARTED,
                                AssessmentUsage.Status.COMPLETED,
                            }:
                                usage.status = (
                                    AssessmentUsage
                                    .Status
                                    .STARTED
                                )
                                update_fields.append(
                                    "status"
                                )

                            if (
                                usage.started_at is None
                                and (
                                    invitation.started_at
                                    is not None
                                )
                            ):
                                usage.started_at = (
                                    invitation.started_at
                                )
                                update_fields.append(
                                    "started_at"
                                )

                    if update_fields:
                        usage.save(
                            update_fields=list(
                                dict.fromkeys(
                                    update_fields
                                )
                            )
                        )

                        updated_usage_count += 1

            if dry_run:
                transaction.set_rollback(True)

        mode_label = (
            "DRY RUN"
            if dry_run
            else "SAVED"
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"AssessmentUsage backfill: "
                f"{mode_label}"
            )
        )

        self.stdout.write(
            f"Invitations processed: "
            f"{invitation_count}"
        )

        self.stdout.write(
            f"Usage rows created: "
            f"{created_usage_count}"
        )

        self.stdout.write(
            f"Usage rows updated: "
            f"{updated_usage_count}"
        )

        self.stdout.write(
            f"Invitations skipped: "
            f"{skipped_invitation_count}"
        )

        self.stdout.write(
            f"Activities without a matching usage row: "
            f"{unmatched_activity_count}"
        )

        self.stdout.write(
            f"Completed activities without an exact "
            f"individual completion date: "
            f"{uncertain_completion_count}"
        )

        if uncertain_completion_count:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Those completed activities were not "
                    "made billable during this backfill."
                )
            )

            self.stdout.write(
                self.style.WARNING(
                    "Do not use "
                    "--include-completed-fallback "
                    "until the invitation-level timestamp "
                    "is considered acceptable for historic "
                    "billing."
                )
            )