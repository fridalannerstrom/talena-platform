"""Preview retention review dates; never perform GDPR erasure.

This tool is intentionally incapable of persisting a retention decision,
deleting rows or blobs, or making requests to Sova/OpenAI. It ONLY reads counts
through the existing tenant-scoped candidate data audit.
"""
import json
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.processes.management.commands.audit_candidate_data import (
    audit_candidate_data,
)


POLICY_PROPOSAL_ID = "private_hiring_v0.1_NOT_APPROVED"
DEFAULT_GRACE_DAYS = 90


def parse_date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise CommandError(f"{name} must be a valid ISO date (YYYY-MM-DD).")


def preview_retention(
    *,
    company_id,
    candidate_id,
    hypothetical_closed_on,
    as_of,
    grace_days=DEFAULT_GRACE_DAYS,
    legal_hold_scenario=False,
):
    """Read only: a manual hypothetical date is NOT a verified closed_at field.

    Neither 'review_due' nor a missing blocker means deletion is authorized.
    """
    if grace_days < 1 or grace_days > 365:
        raise CommandError("--grace-days must be between 1 and 365.")

    data_audit = audit_candidate_data(
        company_id=company_id, candidate_id=candidate_id
    )
    review_date = hypothetical_closed_on + timedelta(days=grace_days)
    due = as_of >= review_date

    cautions = [
        "Policy is a proposal, not approved or activated.",
        "Closure date is manually supplied for this simulation; it is not a saved process status.",
        "No legal basis, controller instructions or preservation exceptions were verified.",
        "Candidate information can be shared with another company.",
        "Billing PROTECT, shared files and indirect references require separate decisions.",
        "External Sova, OpenAI, Azure Blob, logs and backups were not contacted.",
        "No data will be deleted or anonymised by this command.",
    ]
    if data_audit["candidate_record_shared_outside_scope"]:
        cautions.append("Candidate has links outside the selected company.")
    if data_audit["blockers"]["invitation_deletion_may_be_blocked"]:
        cautions.append("AssessmentUsage PROTECT relation may block deletion.")
    if legal_hold_scenario:
        cautions.append("Hypothetical hold: retain for documented legal review.")

    return {
        "mode": "READ_ONLY_RETENTION_SIMULATION",
        "policy_proposal": POLICY_PROPOSAL_ID,
        "policy_approved": False,
        "automatic_deletion_enabled": False,
        "candidate_global_delete_permitted": False,
        "input_is_hypothetical": True,
        "scenario": {
            "purpose": "hiring",
            "hypothetical_closed_on": hypothetical_closed_on.isoformat(),
            "as_of": as_of.isoformat(),
            "grace_days": grace_days,
            "review_on": review_date.isoformat(),
            "legal_hold_assumed": bool(legal_hold_scenario),
            "review_due_by_date": due,
            "status": (
                "hold_requires_human_review" if legal_hold_scenario
                else "review_due_NOT_delete_authorized" if due
                else "before_review_date"
            ),
        },
        "scoped_data_inventory": data_audit,
        "next_action": "human_policy_and_data_review_required",
        "warnings": cautions,
    }


class Command(BaseCommand):
    help = (
        "Read-only retention date simulation for one candidate in one company. "
        "Requires a hypothetical manually supplied closure date. "
        "Cannot delete or change candidate records."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True)
        parser.add_argument("--candidate-id", type=int, required=True)
        parser.add_argument(
            "--purpose", required=True,
            help="Only 'hiring' is supported by this unapproved draft policy.",
        )
        parser.add_argument(
            "--closed-on", required=True,
            help="Hypothetical closure date YYYY-MM-DD. Never derived from archive status.",
        )
        parser.add_argument(
            "--as-of", help="Simulation reference date YYYY-MM-DD; defaults to today.",
        )
        parser.add_argument(
            "--grace-days", type=int, default=DEFAULT_GRACE_DAYS,
            help="Proposed grace period, 1–365 days. Default: 90.",
        )
        parser.add_argument(
            "--legal-hold-scenario", action="store_true",
            help="Simulate a possible legal hold, NOT a verification of a real hold.",
        )

    def handle(self, *args, **options):
        company_id = options["company_id"]
        candidate_id = options["candidate_id"]
        if company_id <= 0 or candidate_id <= 0:
            raise CommandError("IDs must be positive integers.")
        if options["purpose"] != "hiring":
            raise CommandError("Only --purpose hiring is supported in this preview.")

        closed_on = parse_date(options["closed_on"], "--closed-on")
        as_of = (
            parse_date(options["as_of"], "--as-of")
            if options["as_of"]
            else timezone.localdate()
        )
        try:
            result = preview_retention(
                company_id=company_id,
                candidate_id=candidate_id,
                hypothetical_closed_on=closed_on,
                as_of=as_of,
                grace_days=options["grace_days"],
                legal_hold_scenario=options["legal_hold_scenario"],
            )
        except OverflowError:
            raise CommandError("Date overflow; adjust --closed-on or --grace-days.")
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
