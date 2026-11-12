"""Read-only, scoped inventory of candidate-related records for GDPR planning.

This command deliberately NEVER deletes, exports, or prints candidate content.
It is for trusted operators via manage.py, not a customer-facing endpoint.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.accounts.models import Company
from apps.activity.models import ActivityEvent
from apps.candidate_results.models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
    CandidateTestExperienceFeedback,
)
from apps.emails.models import EmailLog
from apps.processes.models import (
    AssessmentUsage,
    Candidate,
    HistoricalAssessmentImport,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
    HistoricalCandidateReport,
    HistoricalProcessCandidate,
    SelfRegistration,
    TestInvitation,
)
from apps.teams.models import TeamAIInsight, TeamMembership


def audit_candidate_data(*, company_id, candidate_id):
    """Return aggregate counts only; queries are SELECTs, with no side effects.

    Every counted relation is restricted to the supplied company. The Candidate
    record itself is global in Talena, so deletion across companies is unsafe.
    """
    if not Company.objects.filter(pk=company_id).exists():
        raise CommandError("Company does not exist.")

    candidate = Candidate.objects.only("id", "email").filter(pk=candidate_id).first()
    if candidate is None:
        raise CommandError("Candidate does not exist.")

    invitation_qs = TestInvitation.objects.filter(
        candidate_id=candidate_id, process__company_id=company_id
    )
    historical_qs = HistoricalProcessCandidate.objects.filter(
        candidate_id=candidate_id, process__company_id=company_id
    )
    usage_qs = AssessmentUsage.objects.filter(
        Q(candidate_id=candidate_id) | Q(invitation__candidate_id=candidate_id),
        company_id=company_id,
    ).distinct()
    snapshot_qs = CandidateResultSnapshot.objects.filter(
        candidate_id=candidate_id, process__company_id=company_id
    )
    team_membership_qs = TeamMembership.objects.filter(
        candidate_id=candidate_id, team__company_id=company_id
    )
    historical_result_qs = HistoricalAssessmentResult.objects.filter(
        candidate_id=candidate_id, process__company_id=company_id
    )
    event_qs = ActivityEvent.objects.filter(company_id=company_id).filter(
        Q(candidate_id=candidate_id)
        | Q(invitation__candidate_id=candidate_id)
    ).distinct()

    # Match by email is a heuristic, not a verified link to Candidate.pk.
    self_registration_qs = SelfRegistration.objects.filter(
        process__company_id=company_id, email__iexact=candidate.email
    )

    # Check ALL company-owned relation paths; do not expose other tenant IDs,
    # names, underlying results, or counts in the output.
    other_company_links = any((
        TestInvitation.objects.filter(candidate_id=candidate_id)
        .exclude(process__company_id=company_id).exists(),
        HistoricalProcessCandidate.objects.filter(candidate_id=candidate_id)
        .exclude(process__company_id=company_id).exists(),
        AssessmentUsage.objects.filter(candidate_id=candidate_id)
        .exclude(company_id=company_id).exists(),
        TeamMembership.objects.filter(candidate_id=candidate_id)
        .exclude(team__company_id=company_id).exists(),
        CandidateResultSnapshot.objects.filter(candidate_id=candidate_id)
        .exclude(process__company_id=company_id).exists(),
        HistoricalAssessmentResult.objects.filter(candidate_id=candidate_id)
        .exclude(process__company_id=company_id).exists(),
        ActivityEvent.objects.filter(candidate_id=candidate_id)
        .exclude(company_id=company_id).exists(),
    ))

    counts = {
        "test_invitations": invitation_qs.count(),
        "historical_process_candidates": historical_qs.count(),
        "assessment_usages": usage_qs.count(),
        "candidate_result_snapshots": snapshot_qs.count(),
        "candidate_result_access_credentials": CandidateResultAccess.objects.filter(
            snapshot__in=snapshot_qs
        ).count(),
        "candidate_result_feedback": CandidateResultFeedback.objects.filter(
            snapshot__in=snapshot_qs
        ).count(),
        "candidate_test_experience_feedback": (
            CandidateTestExperienceFeedback.objects.filter(
                snapshot__in=snapshot_qs
            ).count()
        ),
        "historical_assessment_results": historical_result_qs.count(),
        "historical_assessment_scores": HistoricalAssessmentScore.objects.filter(
            result__in=historical_result_qs
        ).count(),
        # Imports can include multiple candidates: these are references to
        # shared source files and must not be automatically deleted.
        "shared_historical_import_files_referenced": (
            HistoricalAssessmentImport.objects.filter(
                results__in=historical_result_qs
            ).distinct().count()
        ),
        "legacy_historical_pdf_records": HistoricalCandidateReport.objects.filter(
            historical_candidate__in=historical_qs
        ).count(),
        "legacy_pdf_file_fields_on_invitations": (
            invitation_qs.exclude(historical_report_file="")
            .exclude(historical_report_file__isnull=True).count()
        ),
        "email_logs": EmailLog.objects.filter(invitation__in=invitation_qs).count(),
        "activity_events": event_qs.count(),
        "team_memberships": team_membership_qs.count(),
        # Content is shared by the whole team, not candidate-owned.
        "shared_team_ai_insights_to_review": TeamAIInsight.objects.filter(
            team__memberships__in=team_membership_qs
        ).distinct().count(),
        "self_registrations_email_match_unverified": self_registration_qs.count(),
    }

    if not any(counts.values()):
        # Avoid using a global candidate ID to enumerate candidates that
        # have no relationship to the requested customer.
        raise CommandError("No candidate-related records in this company.")

    company_protected = usage_qs.count()
    return {
        "mode": "read_only_dry_run",
        "scope": {"company_id": company_id},
        "candidate_record_shared_outside_scope": other_company_links,
        "counts": counts,
        "blockers": {
            "protected_assessment_usage_rows_in_scope": company_protected,
            "invitation_deletion_may_be_blocked": company_protected > 0,
            "candidate_global_delete_not_authorized": True,
        },
        "limits": [
            "Aggregated counts only: no names, email addresses, or test content.",
            "The global Candidate row can be linked to other companies.",
            "Free-text/JSON references without a candidate foreign key may remain.",
            "Self-registration matches by email are unverified.",
            "Historical source imports and team AI insights can contain shared data.",
            "File storage, logs, Sova, OpenAI, and backups were not inspected.",
            "This audit neither approves nor performs GDPR deletion.",
        ],
    }


class Command(BaseCommand):
    help = (
        "Read-only candidate data inventory for one company. "
        "Requires candidate ID and company ID; outputs counts only."
    )

    def add_arguments(self, parser):
        parser.add_argument("--candidate-id", required=True, type=int)
        parser.add_argument("--company-id", required=True, type=int)

    def handle(self, *args, **options):
        candidate_id = options["candidate_id"]
        company_id = options["company_id"]
        if candidate_id <= 0 or company_id <= 0:
            raise CommandError("IDs must be positive integers.")
        result = audit_candidate_data(
            company_id=company_id, candidate_id=candidate_id
        )
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
