"""Trusted, minimal browser-PDF/ZIP export receipts (#435).

Reports are rendered in the browser; this POST confirms *client reported*
generation after the export code has produced a non-empty file. It cannot
guarantee a local download. Never transmit report content, filenames, subject
names, prompts or assessment values.
"""
import json
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from apps.activity.models import ActivityEvent
from apps.core.utils.auth import is_admin
from apps.processes.access_control import process_view_access_required
from apps.processes.interview_question_notes import get_candidate_question_owner
from apps.processes.models import TestProcess, TestInvitation
from apps.processes.services.access import get_accessible_processes_for_user
from apps.teams.views import _team_visibility_queryset
from apps.teams.models import Team

CANDIDATE_REPORT_TYPES = frozenset({
    "overview", "candidate-static-report",
    "personality-results", "personality-interpretation",
    "personality-questions", "personality-candidate-reflection",
    "personality-response-styles", "combined-interview-questions",
    "motivation-results", "motivation-interpretation",
    "motivation-questions", "motivation-candidate-reflection",
    "cognitive-results", "cognitive-interpretation",
    "cognitive-questions", "cognitive-candidate-reflection",
    "team-report", "leadership-report", "derailment-report",
    "prepare-interview", "after-overview", "after-interview",
    "candidate-package-pdf", "candidate-package-zip",
})
TEAM_REPORT_TYPES = frozenset({
    "team-overview", "team-profile", "team-profiles-zip",
    "team-package-pdf", "team-package-zip",
})
REPORT_TYPES = CANDIDATE_REPORT_TYPES | TEAM_REPORT_TYPES


def _payload(request, allowed):
    if len(request.body) > 512:
        return None
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    code = data.get("report_type")
    evidence = data.get("export_id")
    if type(code) is not str or code not in allowed or type(evidence) is not str:
        return None
    try:
        uid = UUID(evidence)
    except (ValueError, AttributeError):
        return None
    if uid.version != 4 or str(uid) != evidence:
        return None
    return code, evidence


def _log_receipt(*, user, company, code, export_id, process=None,
                 candidate=None, invitation=None):
    # Serialise per-company confirmations so concurrent retries with the same
    # export_id do not double-count. Company row exists for both contexts.
    from apps.accounts.models import Company
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=company.pk)
        event = ActivityEvent.objects.filter(
            company=company, verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
            meta__export_id=export_id,
        ).first()
        if event is not None and (
            event.actor_id != user.pk
            or event.process_id != (process.pk if process else None)
            or event.candidate_id != (candidate.pk if candidate else None)
            or (event.meta or {}).get("report_type") != code
        ):
            # A replayed receipt must not silently become a receipt for a
            # different report, candidate or authenticated actor.
            return JsonResponse({"error": "Export receipt already belongs to another report."},
                                status=409)
        if event is None:
            event = ActivityEvent.objects.create(
                company=company, process=process, candidate=candidate,
                invitation=invitation, actor=user,
                verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
                meta={
                    "schema": 1,
                    "report_type": code,
                    "format": "zip" if code.endswith("-zip") else "pdf",
                    "status": "client_reported_generated",
                    "export_id": export_id,
                },
            )
    response = JsonResponse({"ok": True, "status": "client_reported_generated"})
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@process_view_access_required
@require_POST
def confirm_candidate_report_export(request, process_id, candidate_id):
    data = _payload(request, CANDIDATE_REPORT_TYPES)
    if data is None:
        return JsonResponse({"error": "Invalid report export receipt."}, status=400)
    process = get_object_or_404(TestProcess, pk=process_id)
    owner = get_candidate_question_owner(process, candidate_id)
    code, export_id = data
    return _log_receipt(
        user=request.user, company=process.company, process=process,
        candidate=owner.candidate,
        invitation=owner if isinstance(owner, TestInvitation) else None,
        code=code, export_id=export_id,
    )


@login_required
@require_POST
def confirm_team_report_export(request, pk):
    data = _payload(request, TEAM_REPORT_TYPES)
    if data is None:
        return JsonResponse({"error": "Invalid report export receipt."}, status=400)
    if is_admin(request.user):
        # Platform admins have global Talena access even without membership
        # in the customer's own organisational units.
        team = get_object_or_404(Team, pk=pk)
    else:
        _processes, company = get_accessible_processes_for_user(
            request.user, include_archived=True,
        )
        team = get_object_or_404(_team_visibility_queryset(request.user, company), pk=pk)
    code, export_id = data
    return _log_receipt(
        user=request.user, company=team.company, code=code, export_id=export_id,
    )
