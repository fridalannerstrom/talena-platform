from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from .forms import TestProcessCreateForm, CandidateCreateForm
from .models import (
    TestProcess,
    Candidate,
    TestInvitation,
    SelfRegistration,
    ProcessLabel,
    HistoricalProcessCandidate,
)
from .purpose_utils import normalize_purpose_key
from apps.reports.services.candidate_insights import (
    build_general_insight_input,
    generate_general_candidate_insights,
)

from apps.processes.services.candidate_insights import (
    build_candidate_insights,
)

from apps.processes.services.candidate_profile import (
    build_historical_candidate_profile,
)

from apps.processes.models import (
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)

from apps.processes.services.historical_candidate_summary import (
    stream_historical_candidate_summary,
)

from apps.core.ai.purpose_fit import (
    purpose_supports_fit,
    create_empty_purpose_fit,
    apply_purpose_fit_event,
    stream_candidate_purpose_fit,
    save_candidate_purpose_fit,
)

from apps.processes.services.historical_assessment_import import import_historical_assessment_file
from django.db.models import Count, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from apps.processes.models import HistoricalProcessCandidate
from django.contrib import messages
from django.db import transaction
from .forms import SelfRegisterForm
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import EmailMultiAlternatives
from apps.emails.models import EmailTemplate, EmailLog
from apps.emails.utils import render_placeholders
from django.core.mail import send_mail
from django.http import StreamingHttpResponse, JsonResponse
from apps.accounts.utils.org_access import get_accessible_orgunit_ids
from .purpose_context_config import get_purpose_context_config

from urllib.parse import urlparse
from django.http import HttpResponseRedirect
from django.db.models import Count, Q
from datetime import datetime, date, time

from django.http import HttpResponse
from apps.accounts.utils.permissions import filter_by_user_accounts, user_can_access_account
from apps.accounts.utils.org_access import get_effective_orgunit_permissions, user_can_view_process, user_can_edit_process, get_company_for_user
from django.http import HttpResponseForbidden

from apps.processes.services.send_tests import send_assessments_and_emails
from .purpose_context_config import get_purpose_context_config

import json
import uuid
import requests

from django.conf import settings

from apps.accounts.models import Company, CompanyMember
from apps.projects.models import ProjectMeta

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from apps.reports.libraries.motivation.builder import (
    build_scores_by_competency,
    build_practitioner_report,
    build_motivation_report,
    build_motivation_coaching_report,
    build_manager_report,
    build_candidate_report
)

from apps.core.ai.candidate_summary import (
    stream_candidate_summary,
    save_candidate_summary,
)

from apps.reports.libraries.personality.resolver import build_personality_reports_for_candidate
from apps.reports.libraries.cognitive.builder import build_cognitive_reports_for_test

from .forms import TestProcessWizardCreateForm

from apps.reports.libraries.purpose.content import get_report_mode_content

from apps.processes.services.process_recommendations import (
    PROCESS_PURPOSES,
    AVAILABLE_TESTS,
    PURPOSE_RECOMMENDED_TESTS,
    resolve_dev_sova_template,
    build_default_process_name,
)

from apps.processes.services.process_recommendations import PROCESS_PURPOSES

from .models import ProcessRoleContext
from .forms import ProcessRoleContextForm



def build_candidate_detail_context(process, invitation):
    candidate = invitation.candidate
    activities = invitation.sova_activities or []

    def get_assessment_key(name):
        """
        Converts both ProjectMeta test names and Sova activity names
        into the same internal key, so we can avoid duplicates.
        """
        text = (name or "").strip().lower()

        if "personality" in text or text in {"pq", "personlighet"}:
            return "personality"

        if "motivation" in text or text in {"mq", "motivation questionnaire"}:
            return "motivation"

        if "numerical" in text or "numeric" in text or "numerisk" in text:
            return "numerical"

        if "logical" in text or "logisk" in text:
            return "logical"

        if "verbal" in text:
            return "verbal"

        if "one-question" in text or "one question" in text:
            return "one_question"

        return text


    def get_base_status_for_missing_activity(invitation):
        """
        Status for assessments that are part of the Sova project,
        but do not yet exist in invitation.sova_activities.
        """
        status = (invitation.status or "").strip().lower()

        if status == "completed":
            return "completed"

        if status == "started":
            return "not_started"

        if status == "sent":
            return "sent"

        if status == "created":
            return "created"

        return status or "created"


    def get_display_status(raw_status):
        status = (raw_status or "").strip().lower()

        if status in {
            "completed",
            "complete",
            "finished",
            "done",
            "result available",
            "result_available",
        }:
            return "completed"

        if status in {
            "started",
            "in progress",
            "in_progress",
        }:
            return "started"

        if status in {
            "sent",
            "invited",
        }:
            return "sent"

        if status in {
            "created",
            "not_sent",
            "not sent",
        }:
            return "created"

        if status in {
            "added",
            "not_started",
            "not started",
        }:
            return "not_started"

        # Sova can return pass/fail for small scored assessments.
        return status or "created"


    def build_sent_assessments(process, invitation, activities):
        """
        Shows the actual assessments included in the Sova project.

        Base source:
        - ProjectMeta.tests, based on process.account_code + process.project_code

        Status source:
        - invitation.sova_activities, when available

        Matching:
        - Uses internal assessment keys instead of exact display names.
        """

        meta = ProjectMeta.objects.filter(
            provider="sova",
            account_code=process.account_code,
            project_code=process.project_code,
        ).first()

        tests_raw = (getattr(meta, "tests", "") or "").strip() if meta else ""

        project_tests = [
            test_name.strip()
            for test_name in tests_raw.split(",")
            if test_name.strip()
        ]

        activity_by_key = {}

        for item in activities:
            activity_name = item.get("activity") or ""
            activity_key = get_assessment_key(activity_name)

            if activity_key:
                activity_by_key[activity_key] = item

        base_status = get_base_status_for_missing_activity(invitation)
        sent_assessments = []
        used_keys = set()

        # 1. Start with the actual tests in ProjectMeta.
        for test_name in project_tests:
            test_key = get_assessment_key(test_name)
            matching_activity = activity_by_key.get(test_key)

            if matching_activity:
                display_name = matching_activity.get("activity") or test_name
                status = get_display_status(matching_activity.get("status"))
                source = "sova_activity"
            else:
                display_name = test_name
                status = base_status
                source = "project_meta"

            sent_assessments.append({
                "activity": display_name,
                "status": status,
                "source": source,
                "key": test_key,
            })

            used_keys.add(test_key)

        # 2. Safety net: add Sova activities only if their key was not already shown.
        for item in activities:
            activity_name = item.get("activity") or ""
            activity_key = get_assessment_key(activity_name)

            if activity_key and activity_key not in used_keys:
                sent_assessments.append({
                    "activity": activity_name,
                    "status": get_display_status(item.get("status")),
                    "source": "sova_activity_extra",
                    "key": activity_key,
                })

                used_keys.add(activity_key)

        return sent_assessments


    sent_assessments = build_sent_assessments(
        process=process,
        invitation=invitation,
        activities=activities,
    )

    activity_events = (
        ActivityEvent.objects
        .filter(company=process.company, process=process, candidate=candidate)
        .select_related("actor", "candidate", "invitation")[:50]
    )

    from apps.emails.models import EmailLog

    email_log_ids = [
        (event.meta or {}).get("email_log_id")
        for event in activity_events
        if (event.meta or {}).get("email_log_id")
    ]

    email_logs_by_id = {
        log.id: log
        for log in EmailLog.objects.filter(id__in=email_log_ids)
    }

    for event in activity_events:
        email_log_id = (event.meta or {}).get("email_log_id")
        event.email_log = email_logs_by_id.get(email_log_id)

    def has_real_result(competencies):
        return any(
            comp.get("score") is not None
            or comp.get("stive") is not None
            or comp.get("stive_rounded") is not None
            or comp.get("sten") is not None
            or comp.get("sten_rounded") is not None
            or comp.get("percentile") is not None
            for comp in competencies
        )

    activity_count = len(sent_assessments)

    completed_statuses = {
        "completed",
        "complete",
        "finished",
        "done",
        "result available",
        "result_available",
    }

    tests_completed_count = sum(
        1
        for activity in activities
        if (activity.get("status") or "").strip().lower() in completed_statuses
    )

    has_any_completed_assessment = tests_completed_count > 0

    all_assessments_completed = (
        activity_count > 0
        and tests_completed_count >= activity_count
    )

    mq_competencies = []
    personality_competencies = []
    has_motivation_results = False
    has_personality_results = False

    for item in activities:
        activity_name = (item.get("activity") or "").strip().lower()
        competencies = item.get("competencies", []) or []

        is_motivation_activity = (
            activity_name == "motivation questionnaire"
            or activity_name == "sova motivation questionnaire"
            or "motivation" in activity_name
        )

        if is_motivation_activity:
            if has_real_result(competencies):
                has_motivation_results = True

            for comp in competencies:
                mq_competencies.append({
                    "competency": comp.get("competency"),
                    "score": comp.get("stive_rounded"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "stive": comp.get("stive"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "sten": comp.get("sten"),
                    "percentile": comp.get("percentile"),
                })

        is_personality_activity = (
            activity_name == "personality assessment"
            or activity_name == "sova personality questionnaire"
            or "personality" in activity_name
        )

        if is_personality_activity:
            if has_real_result(competencies):
                has_personality_results = True

            for comp in competencies:
                personality_competencies.append({
                    "competency": comp.get("competency"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "sten": comp.get("sten"),
                    "percentile": comp.get("percentile"),
                })

    personality_competencies = sorted(
        personality_competencies,
        key=lambda x: (x.get("competency") or "").lower()
    )

    motivation_scores = build_scores_by_competency(mq_competencies)

    practitioner_report = build_practitioner_report(
        competencies=mq_competencies,
    )

    manager_report = build_manager_report(
        competencies=mq_competencies,
    )

    candidate_report = build_candidate_report(
        competencies=mq_competencies,
    )

    coaching_report = build_motivation_coaching_report(
        competencies=mq_competencies,
    )

    motivation_reports_for_ui = [
        practitioner_report,
        manager_report,
        coaching_report,
        candidate_report,
    ]

    def safe_motivation_score(item):
        return item.get("score") if item.get("score") is not None else -1

    def safe_personality_score(item):
        return item.get("sten_rounded") if item.get("sten_rounded") is not None else -1

    valid_mq_competencies = [
        comp for comp in mq_competencies
        if comp.get("score") is not None
    ]

    valid_personality_competencies = [
        comp for comp in personality_competencies
        if comp.get("sten_rounded") is not None
    ]

    sorted_mq_desc = sorted(
        valid_mq_competencies,
        key=safe_motivation_score,
        reverse=True,
    )

    sorted_personality_desc = sorted(
        valid_personality_competencies,
        key=safe_personality_score,
        reverse=True,
    )

    top_motivations = sorted_mq_desc[:3]
    top_personality_traits = sorted_personality_desc[:3]

    sorted_mq_asc = sorted(
        valid_mq_competencies,
        key=safe_motivation_score,
    )

    sorted_personality_asc = sorted(
        valid_personality_competencies,
        key=safe_personality_score,
    )

    motivation_development_areas = sorted_mq_asc[:2]
    personality_development_areas = sorted_personality_asc[:2]

    numerical_percentile = None
    logical_percentile = None
    verbal_percentile = None

    has_verbal_results = False
    has_logical_results = False
    has_numerical_results = False

    for item in activities:
        activity_name = item.get("activity", "")
        competencies = item.get("competencies", []) or []
        first_comp = competencies[0] if competencies else {}

        percentile = first_comp.get("percentile")

        if activity_name == "Sova Numerical Reasoning Assessment":
            numerical_percentile = percentile
            if percentile is not None:
                has_numerical_results = True

        elif activity_name == "Sova Logical Reasoning Assessment":
            logical_percentile = percentile
            if percentile is not None:
                has_logical_results = True

        elif activity_name == "Sova Verbal Reasoning Assessment":
            verbal_percentile = percentile
            if percentile is not None:
                has_verbal_results = True

    has_ability_results = (
        has_verbal_results
        or has_logical_results
        or has_numerical_results
    )

    general_insight_input = build_general_insight_input(
        personality_competencies=personality_competencies,
        motivation_competencies=mq_competencies,
        verbal_percentile=verbal_percentile,
        logical_percentile=logical_percentile,
        numerical_percentile=numerical_percentile,
    )

    print("=== GENERAL INSIGHT INPUT ===")
    print(json.dumps(
        general_insight_input,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))
    print("=== /GENERAL INSIGHT INPUT ===")

    ability_reports_for_ui = {
        "overview": [],
        "verbal": build_cognitive_reports_for_test(
            test_key="verbal",
            percentile=verbal_percentile,
        ) if verbal_percentile is not None else None,

        "logical": build_cognitive_reports_for_test(
            test_key="logical",
            percentile=logical_percentile,
        ) if logical_percentile is not None else None,

        "numerical": build_cognitive_reports_for_test(
            test_key="numerical",
            percentile=numerical_percentile,
        ) if numerical_percentile is not None else None,
    }

    if ability_reports_for_ui["verbal"]:
        ability_reports_for_ui["overview"].append({
            "key": "verbal",
            "label": "Verbal",
            "percentile": verbal_percentile,
        })

    if ability_reports_for_ui["logical"]:
        ability_reports_for_ui["overview"].append({
            "key": "logical",
            "label": "Logical",
            "percentile": logical_percentile,
        })

    if ability_reports_for_ui["numerical"]:
        ability_reports_for_ui["overview"].append({
            "key": "numerical",
            "label": "Numerical",
            "percentile": numerical_percentile,
        })

    project_results = invitation.project_results or {}
    reports = invitation.sova_reports or []

    project_scores = (
        project_results.get("project_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    competency_scores = (
        project_results.get("competency_scores", [])
        if isinstance(project_results, dict)
        else []
    )

    overall_score = (
        project_results.get("overall_score")
        if isinstance(project_results, dict)
        and project_results.get("overall_score") is not None
        else invitation.overall_score
    )

    ability_results = []
    motivation_results = []
    all_competencies = []

    for item in activities:
        activity_name = item.get("activity", "") or ""
        item_status = item.get("status", "") or ""
        item_score = item.get("score")
        item_competencies = item.get("competencies", []) or []

        for comp in item_competencies:
            all_competencies.append({
                "activity": activity_name,
                "status": item_status,
                "competency": comp.get("competency"),
                "stive": comp.get("stive"),
                "stive_rounded": comp.get("stive_rounded"),
                "sten": comp.get("sten"),
                "sten_rounded": comp.get("sten_rounded"),
                "percentile": comp.get("percentile"),
                "assessment_centre": comp.get("assessment_centre"),
            })

        if activity_name in {
            "Sova Logical Reasoning Assessment",
            "Sova Numerical Reasoning Assessment",
            "Sova Verbal Reasoning Assessment",
        }:
            first_comp = item_competencies[0] if item_competencies else {}

            label_map = {
                "Sova Logical Reasoning Assessment": "Logical",
                "Sova Numerical Reasoning Assessment": "Numerical",
                "Sova Verbal Reasoning Assessment": "Verbal",
            }

            ability_results.append({
                "activity": activity_name,
                "label": label_map.get(activity_name, activity_name),
                "status": item_status,
                "score": item_score,
                "competency": first_comp.get("competency"),
                "stive": first_comp.get("stive"),
                "stive_rounded": first_comp.get("stive_rounded"),
                "sten": first_comp.get("sten"),
                "sten_rounded": first_comp.get("sten_rounded"),
                "percentile": first_comp.get("percentile"),
            })

        elif activity_name == "Motivation Questionnaire":
            for comp in item_competencies:
                motivation_results.append({
                    "activity": activity_name,
                    "competency": comp.get("competency"),
                    "stive": comp.get("stive"),
                    "stive_rounded": comp.get("stive_rounded"),
                    "sten": comp.get("sten"),
                    "sten_rounded": comp.get("sten_rounded"),
                    "percentile": comp.get("percentile"),
                    "assessment_centre": comp.get("assessment_centre"),
                })

    ability_order = {"Verbal": 1, "Logical": 2, "Numerical": 3}
    ability_results.sort(key=lambda x: ability_order.get(x["label"], 99))

    motivation_results.sort(
        key=lambda x: (x.get("competency") or "").lower()
    )

    library_status_lookup = {
        "cooperative": "not_started",
        "sensitivity": "not_started",
        "teamwork": "not_started",
        "agreeableness": "not_started",
        "empathy": "not_started",
        "tolerance": "not_started",
        "listening": "not_started",
        "warmth": "not_started",
        "supporting": "not_started",
        "developing_others": "not_started",
        "helpfulness": "not_started",
        "considerate": "not_started",
        "connecting": "not_started",
        "open_communication": "not_started",
        "building_networks": "not_started",
        "initiating_contact": "not_started",
        "dynamic": "not_started",
        "energetic": "not_started",
        "enthusiastic": "not_started",
        "risk_appetite": "not_started",
        "influential": "not_started",
        "persuading": "not_started",
        "desire_to_lead": "not_started",
        "assertive": "not_started",
        "goal_focused": "not_started",
        "competitive": "not_started",
        "challenge": "not_started",
        "self_discipline": "not_started",
        "structured": "not_started",
        "planning_and_organising": "not_started",
        "attention_to_detail": "not_started",
        "keeping_promises": "not_started",
        "analytical": "not_started",
        "data_focus": "not_started",
        "evaluating": "not_started",
        "analysing_problems": "not_started",
        "complex_thinking": "not_started",
        "strategic_thinking": "not_started",
        "conceptual": "not_started",
        "curiosity": "not_started",
        "creativity": "not_started",
        "innovating": "not_started",
        "generating_ideas": "not_started",
        "experimenting": "not_started",
        "adaptability": "not_started",
        "adapting_to_change": "not_started",
        "flexible": "not_started",
        "variety": "not_started",
        "straightforward": "not_started",
        "adhering_to_rules": "not_started",
        "candid": "not_started",
        "earnest": "not_started",
        "status_avoidance": "not_started",
        "egalitarian": "not_started",
        "collective": "not_started",
        "avoiding_status": "not_started",
        "modesty": "not_started",
        "humble": "not_started",
        "modest": "not_started",
        "avoiding_attention": "not_started",
        "resilience": "not_started",
        "tough_minded": "not_started",
        "recovering": "not_started",
        "optimistic": "not_started",
        "emotional_control": "not_started",
        "controlling_stress": "not_started",
        "calm": "not_started",
        "composed": "not_started",
        "independence": "not_started",
        "self_reliant": "not_started",
        "self_contained": "not_started",
        "thinking_independently": "not_started",
    }

    personality_reports = build_personality_reports_for_candidate(
        sova_activities=activities,
        library_status_lookup=library_status_lookup,
    )

    available_reports_count = 0

    if has_verbal_results:
        available_reports_count += 2

    if has_numerical_results:
        available_reports_count += 2

    if has_logical_results:
        available_reports_count += 2

    if has_motivation_results:
        available_reports_count += 4

    if has_personality_results:
        available_reports_count += 11

    has_any_results = (
        has_ability_results
        or has_motivation_results
        or has_personality_results
    )

    purpose_report = get_report_mode_content(process.purpose)

    print("=== PURPOSE REPORT DEBUG ===")
    print("PROCESS PURPOSE:", repr(process.purpose))
    print("PURPOSE REPORT:", purpose_report)
    print("=== /PURPOSE REPORT DEBUG ===")

    # ------------------------------------------------------------
    # Purpose context / report mode
    # ------------------------------------------------------------
    # For now we still use the existing ProcessRoleContext model,
    # but expose it to templates as both role_context and purpose_context.
    # This lets us move towards a more general "purpose context" setup
    # without renaming models or breaking old templates.
    purpose_context_obj = getattr(process, "role_context", None)
    role_context_obj = purpose_context_obj

    has_purpose_context = (
        purpose_context_obj.has_content()
        if purpose_context_obj
        else False
    )

    context_title = ""

    if has_purpose_context:
        context_title = (
            purpose_context_obj.role_title
            or purpose_context_obj.job_advertisement[:80]
            or "this process context"
        )

    # Backwards-compatible name for existing templates
    has_role_context = has_purpose_context

    context_config = get_purpose_context_config(process.purpose)

    # New report mode:
    # - "general" = no added context, only test-based insights
    # - "context" = test data + purpose + added context
    candidate_insights_mode = (
        "context"
        if has_purpose_context
        else "general"
    )

    # Keep the old purpose/report key available separately.
    # Do not use this as the general/context mode.
    purpose_report_key = purpose_report.get("key")

    show_role_context_prompt = not has_purpose_context
    show_context_prompt = show_role_context_prompt

    show_context_prompt = show_role_context_prompt

    critical_competencies_active = has_purpose_context
    competency_overview_active = not has_purpose_context

    report_mode = "context" if has_purpose_context else "general"

    # ------------------------------------------------------------
    # Temporary dummy data for Candidate Insights
    # Later this can be replaced by structured AI JSON output.
    # ------------------------------------------------------------

    candidate_insights = build_candidate_insights(
        mode=candidate_insights_mode,
        general_insight_input=general_insight_input,
    )

    candidate_insights = build_candidate_insights(
        mode="general",
        general_insight_input=general_insight_input,
    )

    print("=== FLEXIBLE AI CONDITION DEBUG ===")
    print("PROCESS PURPOSE:", repr(process.purpose))
    print("PURPOSE IS FLEXIBLE:", process.purpose == "flexible")
    print("HAS ANY RESULTS:", has_any_results)
    print("HAS PERSONALITY RESULTS:", has_personality_results)
    print("HAS MOTIVATION RESULTS:", has_motivation_results)
    print("HAS ABILITY RESULTS:", has_ability_results)
    print("=== /FLEXIBLE AI CONDITION DEBUG ===")

    return {
        "company": process.company,
        "process": process,
        "invitation": invitation,
        "inv": invitation,
        "candidate": candidate,
        "activity_events": activity_events,

        "activities": activities,
        "sent_assessments": sent_assessments,
        "project_results": project_results,
        "project_scores": project_scores,
        "competency_scores": competency_scores,
        "overall_score": overall_score,
        "reports": reports,

        "ability_results": ability_results,
        "motivation_results": motivation_results,
        "all_competencies": all_competencies,

        "numerical_percentile": numerical_percentile,
        "logical_percentile": logical_percentile,
        "verbal_percentile": verbal_percentile,
        "has_ability_results": has_ability_results,

        "mq_competencies": mq_competencies,
        "personality_competencies": personality_competencies,

        "tests_sent_count": activity_count,
        "tests_completed_count": tests_completed_count,
        "available_reports_count": available_reports_count,
        "email_logs_by_id": email_logs_by_id,

        "has_any_results": has_any_results,
        "has_any_completed_assessment": has_any_completed_assessment,
        "all_assessments_completed": all_assessments_completed,

        "top_motivations": top_motivations,
        "top_personality_traits": top_personality_traits,
        "motivation_development_areas": motivation_development_areas,
        "personality_development_areas": personality_development_areas,

        "motivation_scores": motivation_scores,
        "motivation_reports_for_ui": motivation_reports_for_ui,
        "ability_reports_for_ui": ability_reports_for_ui,
        "personality_reports": personality_reports,
        "has_motivation_results": has_motivation_results,
        "has_personality_results": has_personality_results,

        # Existing report/purpose content
        "purpose_report": purpose_report,
        "purpose_report_key": purpose_report_key,

        # Candidate insights
        "candidate_insights": candidate_insights,
        "candidate_insights_mode": candidate_insights_mode,
        "report_mode": report_mode,
        "general_insight_input": general_insight_input,

        # Purpose context
        "purpose_context": purpose_context_obj,
        "has_purpose_context": has_purpose_context,
        "context_config": context_config,
        "show_context_prompt": show_context_prompt,

        # Backwards-compatible names
        "role_context": role_context_obj,
        "has_role_context": has_role_context,
        "show_role_context_prompt": show_role_context_prompt,

        "summary_owner": invitation,

    }

def get_dashboard_activity_for_user(user, limit=10):
    company = get_company_for_user(user)

    if not company:
        return ActivityEvent.objects.none()

    perms = get_effective_orgunit_permissions(user, company)

    own_ids = [uid for uid, p in perms.items() if p == "own"]
    visible_ids = [uid for uid, p in perms.items() if p in ("viewer", "editor")]

    process_q = Q(company=company, is_archived=False) & (
        Q(org_unit_id__in=visible_ids) |
        Q(org_unit_id__in=own_ids, created_by=user)
    )

    accessible_process_ids = (
        TestProcess.objects
        .filter(process_q)
        .values_list("id", flat=True)
    )

    return (
        ActivityEvent.objects
        .filter(
            company=company,
            process_id__in=accessible_process_ids,
        )
        .select_related(
            "actor",
            "candidate",
            "process",
            "invitation",
        )
        .order_by("-created_at")[:limit]
    )

def _get_active_company_for_user(user):
    # om du bara har 1 company per user just nu: ta första
    m = CompanyMember.objects.select_related("company").filter(user=user).first()
    return m.company if m else None


def user_can_access_process(user, process) -> bool:
    company_id = (
        CompanyMember.objects
        .filter(user=user)
        .values_list("company_id", flat=True)
        .first()
    )
    return bool(company_id and process.company_id == company_id)




@login_required
def process_list(request):
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    perms = get_effective_orgunit_permissions(request.user, company)

    own_ids = [uid for uid, p in perms.items() if p == "own"]
    other_ids = [uid for uid, p in perms.items() if p in ("viewer", "editor")]

    process_q = Q(company=company) & (
        Q(org_unit_id__in=other_ids) |
        Q(org_unit_id__in=own_ids, created_by=request.user)
    )

    # Tab: Active / Archived
    show_archived = request.GET.get("archived") == "1"

    historical_candidate_count_subquery = (
        HistoricalProcessCandidate.objects
        .filter(process=OuterRef("pk"))
        .values("process")
        .annotate(count=Count("id"))
        .values("count")
    )

    processes = (
        TestProcess.objects
        .filter(process_q)
        .filter(is_archived=show_archived)
        .annotate(
            live_candidates_count=Count("invitations", distinct=True),
            historical_candidates_count=Coalesce(
                Subquery(
                    historical_candidate_count_subquery,
                    output_field=IntegerField(),
                ),
                0,
            ),
        )
        .order_by("-created_at")
        .prefetch_related("labels")
    )

    # Build edit permissions after processes exists
    can_edit_by_process_id = {}
    for p in processes:
        perm = perms.get(p.org_unit_id)
        can_edit = (
            perm == "editor"
            or (perm == "own" and p.created_by_id == request.user.id)
        )
        can_edit_by_process_id[p.id] = can_edit

    # ProjectMeta lookup
    keys = {
        (p.account_code, p.project_code)
        for p in processes
        if p.account_code and p.project_code
    }

    meta_by_key = {}
    if keys:
        q = Q()
        for acc, proj in keys:
            q |= Q(account_code=acc, project_code=proj)

        metas = ProjectMeta.objects.filter(q)
        meta_by_key = {
            f"{m.account_code}::{m.project_code}": m
            for m in metas
        }

    return render(
        request,
        "customer/processes/process_list.html",
        {
            "company": company,
            "processes": processes,
            "meta_by_key": meta_by_key,
            "perms": perms,
            "show_archived": show_archived,
            "can_edit_by_process_id": can_edit_by_process_id,
        }
    )

def get_template_icon_class(tests, title=""):
    """
    Returns a FontAwesome icon class based on the test types/title.
    """
    text = " ".join(tests).lower()
    title = (title or "").lower()

    if "360" in text or "360" in title:
        return "fa-solid fa-arrows-rotate"

    if (
        "numerical" in text
        or "numerisk" in text
        or "färdighet" in text
        or "fardighet" in text
        or "ability" in text
        or "skills" in text
    ):
        return "fa-solid fa-chart-simple"

    if (
        "personality" in text
        or "personlighet" in text
        or "pq" in title
    ):
        return "fa-solid fa-user-check"

    if (
        "motivation" in text
        or "motivationstest" in text
    ):
        return "fa-solid fa-bullseye"

    if "leadership" in text or "ledarskap" in text:
        return "fa-solid fa-award"

    if "sales" in text or "sälj" in title or "salj" in title:
        return "fa-solid fa-handshake"

    if "admin" in text or "interim" in text or "interim" in title:
        return "fa-solid fa-briefcase"

    if "modern" in title:
        return "fa-solid fa-wand-magic-sparkles"

    if "linear" in title:
        return "fa-solid fa-wave-square"

    if "ihp" in title:
        return "fa-solid fa-layer-group"

    return "fa-solid fa-layer-group"


@login_required
def process_create(request):
    client = SovaClient()
    error = None

    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    choices = []
    template_cards = []
    project_id_map = {}

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = p.get("id")

            meta = meta_map.get((acc, proj_code))

            title = (getattr(meta, "intern_name", None) or sova_name)

            description = ""
            tests = []
            languages = []

            if meta:
                description = (getattr(meta, "notes", None) or "").strip()

                tests_raw = (getattr(meta, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            choices.append((value, title))
            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": p.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            # ✅ sätt company (kundens “konto”)
            company_id = (
                CompanyMember.objects
                .filter(user=request.user)
                .values_list("company_id", flat=True)
                .first()
            )
            if not company_id:
                form.add_error(None, "You are not linked to a company.")
                return render(request, "customer/processes/process_create.html", {
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            obj.company_id = company_id

            
            # ✅ sätt org_unit från session (active org unit)
            active_unit_id = request.session.get("active_org_unit_id")

            company = Company.objects.get(pk=company_id)
            accessible_ids = get_accessible_orgunit_ids(request.user, company)

            if not active_unit_id or int(active_unit_id) not in accessible_ids:
                # fallback: välj en direkt/åtkomlig unit automatiskt
                fallback_id = next(iter(accessible_ids), None)
                if not fallback_id:
                    form.add_error(None, "You do not have an assigned org unit, so a process cannot be created.")
                    return render(request, "customer/processes/process_create.html", {
                        "form": form,
                        "error": error,
                        "template_cards": template_cards,
                        "templates_count": len(template_cards),
                        "accounts_count": len(accounts),
                    })
                active_unit_id = fallback_id
                request.session["active_org_unit_id"] = active_unit_id

            obj.org_unit_id = int(active_unit_id)

            # ✅ endast SOVA-referenser
            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj
            obj.sova_project_id = project_id_map.get(value)

            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            if not obj.project_name_snapshot:
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            obj.created_by = request.user

            membership = (
                CompanyMember.objects
                .filter(user=request.user, company_id=company_id)
                .select_related("primary_org_unit")
                .first()
            )

            if not membership or not membership.primary_org_unit_id:
                form.add_error(None, "You do not have a primary org unit. Please contact an administrator.")
                return render(request, "customer/processes/process_create.html", {
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            obj.org_unit_id = membership.primary_org_unit_id

            obj.save()

            log_event(
                company=company, 
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=obj,
                meta={"process_name": obj.name},
            )

            # ✅ LABELS: skapa/återanvänd labels per company och koppla
            label_names = form.cleaned_data.get("labels_text", [])
            if label_names:
                label_objs = []
                for name in label_names:
                    lab, _ = ProcessLabel.objects.get_or_create(
                        company_id=company_id,
                        name=name,
                    )
                    label_objs.append(lab)
                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            return redirect("processes:process_detail", pk=obj.pk)

        messages.error(request, "The process could not be created. Please check the fields.")
    else:
        form = TestProcessCreateForm()
        form.fields["sova_template"].choices = choices

    return render(request, "customer/processes/process_create.html", {
        "form": form,
        "error": error,
        "template_cards": template_cards,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })

def mark_candidate_ai_content_outdated(process):
    """
    Keep existing AI content, but mark it as needing regeneration.
    """

    invitations = TestInvitation.objects.filter(
        process=process,
    )

    summary_count = (
        invitations
        .exclude(ai_summary="")
        .update(ai_summary_status="outdated")
    )

    purpose_fit_count = (
        invitations
        .exclude(ai_purpose_fit={})
        .update(ai_purpose_fit_status="outdated")
    )

    return {
        "summaries": summary_count,
        "purpose_fits": purpose_fit_count,
    }


def process_update(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if obj.is_historical:
        return HttpResponseForbidden("Historical processes are read-only.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("You do not have permission to edit this process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    old_acc = (obj.account_code or "").strip()
    old_proj = (obj.project_code or "").strip()
    locked = obj.is_template_locked()
    old_purpose = obj.purpose

    client = SovaClient()
    error = None

    # --------------------------------------------------
    # 1. Hämta Sova-projekt från API
    # --------------------------------------------------
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # --------------------------------------------------
    # 2. Hämta ProjectMeta så vi kan hitta namn, tester osv
    # --------------------------------------------------
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    template_cards = []

    for account in accounts:
        acc = (account.get("code") or "").strip()

        for project in (account.get("projects") or []):
            proj_code = (project.get("code") or "").strip()
            sova_name = (project.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"

            meta_item = meta_map.get((acc, proj_code))
            title = getattr(meta_item, "intern_name", None) or sova_name

            description = ""
            tests = []
            languages = []

            if meta_item:
                description = (getattr(meta_item, "notes", None) or "").strip()

                tests_raw = (getattr(meta_item, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta_item, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": project.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # --------------------------------------------------
    # 3. Hjälpvariabler till header/tabs
    # --------------------------------------------------
    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(obj.purpose)

    meta = ProjectMeta.objects.filter(
        account_code=obj.account_code,
        project_code=obj.project_code,
    ).first()

    can_edit = user_can_edit_process(request.user, company, obj)

    def render_edit(form):
        return render(request, "customer/processes/process_edit.html", {
            "form": form,
            "process": obj,
            "error": error,
            "template_locked": locked,

            # Header/base template stuff
            "active": "settings",
            "meta": meta,
            "can_edit": can_edit,
            "process_purpose": process_purpose,
            "context_config": get_purpose_context_config(obj.purpose),
            "self_reg_url": request.build_absolute_uri(obj.get_self_registration_url()),

            # Edit page stuff
            "process_purposes": PROCESS_PURPOSES,
            "available_tests": AVAILABLE_TESTS,
            "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
            "template_cards": template_cards,
            "templates_count": len(template_cards),
            "accounts_count": len(accounts),
        })

    # --------------------------------------------------
    # 4. POST: uppdatera processen
    # --------------------------------------------------
    if request.method == "POST":
        form = TestProcessWizardCreateForm(request.POST)

        if form.is_valid():
            name = (form.cleaned_data.get("name") or "").strip()
            purpose = form.cleaned_data.get("purpose")
            selected_tests = form.cleaned_data.get("selected_tests") or []
            label_names = form.cleaned_data.get("labels_text") or []

            if isinstance(label_names, str):
                label_names = [
                    item.strip()
                    for item in label_names.split(",")
                    if item.strip()
                ]

            # Namn får alltid ändras
            obj.name = name or obj.name

            # Labels får alltid ändras
            label_objs = []
            for label_name in label_names:
                lab, _ = ProcessLabel.objects.get_or_create(
                    company=company,
                    name=label_name,
                )
                label_objs.append(lab)

            # Preserve the currently active context under the old purpose
            # before switching the process to a new purpose.
            if old_purpose != purpose:
                existing_context = getattr(obj, "role_context", None)

                if existing_context and existing_context.has_content():
                    existing_context.save_context_for_purpose(
                        old_purpose,
                        existing_context.get_current_context_data(),
                    )

                    existing_context.save(update_fields=[
                        "purpose_data",
                        "updated_at",
                    ])

            # --------------------------------------------------
            # Purpose får alltid ändras.
            # Tester och Sova-projekt låses efter första utskicket.
            # --------------------------------------------------
            obj.purpose = purpose

            if locked:
                # Behåll befintliga tester och befintlig Sova-koppling.
                # Ignorera manipulerade testvärden från POST.
                obj.provider = "sova"
                obj.account_code = old_acc
                obj.project_code = old_proj
                obj.selected_tests = obj.selected_tests or []

            else:
                # Innan tester har skickats får testpaketet fortfarande ändras.
                obj.selected_tests = selected_tests

                resolved_template = resolve_dev_sova_template(selected_tests)

                if not resolved_template:
                    form.add_error(
                        "selected_tests",
                        "Please select at least Personality or Motivation in the current development environment."
                    )
                    return render_edit(form)

                acc = (resolved_template["account_code"] or "").strip()
                proj = (resolved_template["project_code"] or "").strip()
                value = f"{acc}|{proj}"

                obj.provider = "sova"
                obj.account_code = acc
                obj.project_code = proj

                meta_match = meta_map.get((acc, proj))

                if meta_match and getattr(meta_match, "intern_name", None):
                    obj.project_name_snapshot = meta_match.intern_name
                else:
                    match = next(
                        (t for t in template_cards if t["value"] == value),
                        None
                    )

                    obj.project_name_snapshot = (
                        match["sova_name"] if match else proj
                    )

            # --------------------------------------------------
            # Spara ändringarna
            # --------------------------------------------------
            obj.save()
            obj.labels.set(label_objs)

            if old_purpose != obj.purpose:
                result = mark_candidate_ai_content_outdated(obj)

                print(
                    "AI CONTENT MARKED OUTDATED:",
                    result,
                )

            messages.success(
                request,
                "The process was updated."
            )

            return redirect(
                "processes:process_update",
                pk=obj.pk,
            )

    # --------------------------------------------------
    # 5. GET: fyll edit-formuläret med befintliga värden
    # --------------------------------------------------
    else:
        form = TestProcessWizardCreateForm(initial={
            "name": obj.name,
            "labels_text": ", ".join(obj.labels.values_list("name", flat=True)),
            "purpose": obj.purpose,
            "selected_tests": obj.selected_tests or [],
        })

    return render_edit(form)


@login_required
def process_delete(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    # ✅ kräver POST (viktigt)
    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att radera denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

        # ✅ B + C: delete om möjligt, annars arkivera
    if obj.can_delete():
        log_event(
            company=company,
            verb=ActivityEvent.Verb.PROCESS_DELETED,
            actor=request.user,
            process=obj,
        )
        obj.delete()
    else:
        log_event(
            company=company,
            verb=ActivityEvent.Verb.PROCESS_ARCHIVED,
            actor=request.user,
            process=obj,
            meta={"reason": "could_not_delete"},
        )
        obj.archive()
        messages.info(request, "Processen kunde inte raderas eftersom tester har skickats. Den arkiverades istället.")

    return redirect("processes:process_list")



@login_required
def process_role_context(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical:
        return HttpResponseForbidden(
            "Historical processes are read-only."
        )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    context_config = get_purpose_context_config(process.purpose)
    purpose_key = normalize_purpose_key(process.purpose)

    role_context, created = ProcessRoleContext.objects.get_or_create(
        process=process
    )

    if request.method == "POST":
        # IMPORTANT:
        # Capture the saved database values before ModelForm validation,
        # because form.is_valid() may update the model instance in memory.
        previous_context_data = {
            field_name: getattr(role_context, field_name, "") or ""
            for field_name in ProcessRoleContext.CONTEXT_FIELDS
        }

        form = ProcessRoleContextForm(
            request.POST,
            instance=role_context,
            context_config=context_config,
        )

        if form.is_valid():
            submitted_data = {
                field_name: form.cleaned_data.get(field_name, "") or ""
                for field_name in ProcessRoleContext.CONTEXT_FIELDS
            }

            context_changed = previous_context_data != submitted_data

            role_context = form.save(commit=False)

            role_context.save_context_for_purpose(
                purpose=purpose_key,
                context_data=submitted_data,
            )

            role_context.apply_context_data(submitted_data)
            role_context.save()

            if context_changed:
                result = mark_candidate_ai_content_outdated(
                    process
                )

                print("=== CONTEXT CHANGED ===")
                print("PROCESS:", process.id)
                print("AI CONTENT MARKED OUTDATED:", result)

            messages.success(
                request,
                "The process context was saved."
            )

            return redirect(
                "processes:process_detail",
                pk=process.pk,
            )

    else:
        saved_purpose_context = role_context.get_context_for_purpose(
            purpose_key
        )

        if saved_purpose_context is not None:
            initial_data = saved_purpose_context
            using_previous_purpose_as_start = False
        else:
            # No saved version for this purpose yet.
            # Reuse the active context as a helpful starting point.
            initial_data = role_context.get_current_context_data()
            using_previous_purpose_as_start = role_context.has_content()

        form = ProcessRoleContextForm(
            instance=role_context,
            initial=initial_data,
            context_config=context_config,
        )

    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(process.purpose)

    company = process.company
    can_edit = user_can_edit_process(
        request.user,
        company,
        process,
    )

    return render(
        request,
        "customer/processes/process_role_context.html",
        {
            "process": process,
            "form": form,
            "role_context": role_context,
            "purpose_context": role_context,
            "context_config": context_config,
            "purpose_key": purpose_key,

            "using_previous_purpose_as_start": (
                using_previous_purpose_as_start
                if request.method != "POST"
                else False
            ),

            # Header/base template
            "meta": meta,
            "process_purpose": process_purpose,
            "can_edit": can_edit,

            # Active tab
            "active": "context",
        },
    )


@login_required
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    context_config = get_purpose_context_config(process.purpose)

    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    # Must belong to the same company
    if process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    # Access rule, including own-only logic
    if not user_can_view_process(request.user, company, process):
        return HttpResponseForbidden("You do not have access to this process.")

    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    can_edit = user_can_edit_process(request.user, company, process)

    if process.is_historical:
        invitations = TestInvitation.objects.none()

        historical_candidates = (
            HistoricalProcessCandidate.objects
            .filter(process=process)
            .select_related("candidate", "created_by")
            .prefetch_related("reports")
            .order_by("-created_at")
        )

        status_counts = dict(
            historical_candidates.values("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        total_candidates = historical_candidates.count()
        invited_count = 0

        started_count = historical_candidates.filter(
            status__in=["started", "completed"]
        ).count()

        completed_count = historical_candidates.filter(
            status="completed"
        ).count()

        expired_count = 0
        not_invited_count = 0

        not_started_count = historical_candidates.exclude(
            status__in=["started", "completed"]
        ).count()

    else:
        historical_candidates = HistoricalProcessCandidate.objects.none()

        invitations = (
            process.invitations
            .select_related("candidate")
            .order_by("-created_at")
        )

        status_counts = dict(
            invitations.values("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        total_candidates = invitations.count()

        invited_qs = invitations.filter(
            Q(status__in=["sent", "started", "completed", "expired"]) |
            Q(source="self_registered")
        )

        invited_count = invited_qs.count()

        started_count = invitations.filter(
            status__in=["started", "completed"]
        ).count()

        completed_count = invitations.filter(
            status="completed"
        ).count()

        expired_count = invitations.filter(
            status="expired"
        ).count()

        # Candidates added but not yet given access to the assessment
        not_invited_count = total_candidates - invited_count

        # Candidates who have access but have not started or completed
        not_started_count = invited_qs.exclude(
            status__in=["started", "completed", "expired"]
        ).count()

    activity_events = (
        ActivityEvent.objects
        .filter(company=company, process=process)
        .select_related("actor", "candidate", "invitation")
        [:50]
    )

    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(process.purpose)

    context = {
        "process": process,
        "invitations": invitations,
        "historical_candidates": historical_candidates,
        "is_historical": process.is_historical,
        "meta": meta,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        "status_counts": status_counts,
        "can_edit": can_edit,
        "activity_events": activity_events,
        "process_purpose": process_purpose,
        "active": "overview",
        "context_config": context_config,
        "kpis": {
            "total_candidates": total_candidates,
            "invited": invited_count,
            "started": started_count,
            "completed": completed_count,
            "expired": expired_count,
            "not_started": not_started_count,
            "not_invited": not_invited_count,
        },
    }

    return render(request, "customer/processes/process_detail.html", context)



@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical:
        return HttpResponseForbidden("Historical processes are read-only.")

    company = get_company_for_user(request.user)
    if not company or process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att ändra i denna process.")

    # ✅ Säkerhetskontroll
    if not company or not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att skicka tester i denna process.")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        form = CandidateCreateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()

            candidate, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                }
            )

            invitation, inv_created = TestInvitation.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )

            if inv_created:
                log_event(
                    company=company,  # du har company i funktionen
                    verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                    actor=request.user,
                    process=process,
                    candidate=candidate,
                    invitation=invitation,
                    meta={"source": "invited"},
                )

            if inv_created:
                msg = f"{candidate.email} har lagts till i processen."
                messages.success(request, msg)
            else:
                msg = f"{candidate.email} är redan i processen."
                messages.info(request, msg)

            # ✅ Modal/AJAX: return JSON istället för redirect
            if is_ajax:
                return JsonResponse({
                    "ok": True,
                    "message": msg,
                    "redirect_url": reverse("processes:process_detail", kwargs={"pk": process.pk})
                })

            return redirect("processes:process_detail", pk=process.pk)

        # ❌ Ogiltigt form
        if is_ajax:
            # returnera form-HTML med errors så modalen kan visa dem
            return render(
                request,
                "customer/processes/_add_candidate_form.html",
                {"process": process, "form": form},
                status=400
            )

    else:
        form = CandidateCreateForm()

    # ✅ GET: om AJAX -> partial, annars full page
    if is_ajax:
        return render(request, "customer/processes/_add_candidate_form.html", {
            "process": process,
            "form": form,
        })

    return render(request, "customer/processes/process_add_candidate.html", {
        "process": process,
        "form": form,
    })



@login_required
def invite_candidate(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")
    
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    invitation = get_object_or_404(TestInvitation, process=process, candidate=candidate)

    # Här kopplar vi in SOVA i steg 3.
    # Tills vidare: fejka så att du ser flödet funka i UI:
    invitation.status = "sent"
    invitation.invited_at = invitation.invited_at or __import__("django.utils.timezone").utils.timezone.now()
    invitation.save(update_fields=["status", "invited_at"])

    messages.success(request, f"Invite triggered for {candidate.email} (stub).")
    return redirect("processes:process_detail", pk=process.pk)


@login_required
def sova_order_assessment_smoke_test(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")
    candidate = get_object_or_404(Candidate, pk=candidate_id)

    client = SovaClient()

    # ✅ From SOVA UI: account TQ_SWEDEN_ACCOUNT, project code tqs-simple-test
    project_code = "tqs-simple-test"

    request_id = f"talena-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

    # ✅ Minimal valid payload (snake_case, matches docs)
    payload = {
        "request_id": request_id,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "language": "sv",  # test "sv" first; if needed change to "sv-SE"
        "job_title": "Smoke Test",
        "job_number": f"talena-{process.id}",
        "meta_data": {
            "talena_process_id": str(process.id),
            "talena_candidate_id": str(candidate.id),
            "talena_user_id": str(request.user.id),
        },
    }

    try:
        print("\n=== SOVA ORDER-ASSESSMENT SMOKE TEST ===")
        print("ACCOUNT:", "TQ_SWEDEN_ACCOUNT")
        print("PROJECT CODE:", project_code)
        print("BASE URL:", client.base_url)
        print("PAYLOAD:", payload)

        resp = client.order_assessment(project_code, payload)

        print("RESPONSE JSON:", resp)
        print("=== /SOVA ORDER-ASSESSMENT SMOKE TEST ===\n")

        assessment_url = resp.get("url")
        if assessment_url:
            return HttpResponse(
                f"✅ OK\nProject: {project_code}\nRequest: {request_id}\n\nTest URL:\n{assessment_url}",
                content_type="text/plain"
            )

        return HttpResponse(
            f"✅ OK but no 'url' returned\nProject: {project_code}\nRequest: {request_id}\n\nResponse:\n{resp}",
            content_type="text/plain"
        )

    except Exception as e:
        print("\n=== SOVA ORDER-ASSESSMENT SMOKE TEST FAILED ===")
        print("ERROR:", str(e))
        print("BASE URL:", client.base_url)
        print("PROJECT CODE:", project_code)
        print("PAYLOAD:", payload)
        print("=== /FAILED ===\n")

        return HttpResponse(f"❌ FAILED: {e}", content_type="text/plain", status=500)

def _is_safe_external_url(url: str) -> bool:
    try:
        p = urlparse(url or "")
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def self_register(request, token):
    process = get_object_or_404(TestProcess, self_registration_token=token)

    if request.method != "POST":
        form = SelfRegisterForm()
        return render(request, "customer/processes/self_register_form.html", {
            "process": process,
            "form": form,
        })

    form = SelfRegisterForm(request.POST)
    if not form.is_valid():
        return render(request, "customer/processes/self_register_form.html", {
            "process": process,
            "form": form,
        })

    first_name = form.cleaned_data["first_name"].strip()
    last_name = form.cleaned_data["last_name"].strip()
    email = form.cleaned_data["email"].strip().lower()

    client = SovaClient()

    with transaction.atomic():
        candidate, _ = Candidate.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        invitation, created = TestInvitation.objects.get_or_create(
            process=process,
            candidate=candidate,
            defaults={
                "status": "created",
                "source": "self_registered",
            },
        )

        if created:
            log_event(
                company=process.company,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                actor=None,
                actor_name="Self-registration",
                process=process,
                candidate=candidate,
                invitation=invitation,
                meta={"source": "self_registered"},
            )

        if not created and invitation.source != "self_registered":
            invitation.source = "self_registered"
            invitation.save(update_fields=["source"])

    existing_url = invitation.assessment_url
    if not existing_url:
        try:
            existing_url = (invitation.sova_payload or {}).get("url")
        except Exception:
            existing_url = None

    if (
        invitation.status in ("sent", "started", "completed")
        and existing_url
        and _is_safe_external_url(existing_url)
    ):
        return HttpResponseRedirect(existing_url)

    request_id = f"talena-selfreg-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

    payload = {
        "request_id": request_id,
        "candidate_id": str(candidate.id),
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "email": candidate.email,
        "language": "sv",
        "job_title": process.job_title or process.name,
        "job_number": f"talena-{process.id}",
        "meta_data": {
            "talena_process_id": str(process.id),
            "talena_candidate_id": str(candidate.id),
            "talena_request_id": request_id,
        },
    }

    try:
        resp = client.order_assessment(process.project_code, payload)
        test_url = (resp or {}).get("url")

        invitation.status = "sent"
        invitation.invited_at = timezone.now()
        invitation.sova_payload = resp
        invitation.request_id = request_id
        invitation.assessment_url = test_url
        invitation.save(update_fields=[
            "status",
            "invited_at",
            "sova_payload",
            "request_id",
            "assessment_url",
        ])

        # Hämta mall
        lang = "sv"
        template = (
            EmailTemplate.objects
            .filter(
                process=process,
                template_type="invitation",
                language=lang,
                is_active=True,
            )
            .first()
        )

        subject_tpl = template.subject if template else "{process_name}: Ditt test"
        body_tpl = template.body if template else (
            "Hej {first_name}!\n\n"
            "Klicka på länken för att starta testet:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "Talena"
        )

        ctx = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "process_name": process.name,
            "job_title": process.job_title,
            "job_location": process.job_location,
            "assessment_url": test_url,
        }

        subject = render_placeholders(subject_tpl, ctx)
        body = render_placeholders(body_tpl, ctx)

        email_log = EmailLog.objects.create(
            invitation=invitation,
            template_type="invitation",
            to_email=candidate.email,
            subject=subject,
            body_snapshot=body,
            status="queued",
        )

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@talena.se",
                to=[candidate.email],
            )
            msg.send()
            email_log.mark_sent()
        except Exception as e:
            email_log.mark_failed(str(e))
            # fallback-mejlet får faila utan att stoppa redirect till testet

        log_event(
            company=process.company,
            verb=ActivityEvent.Verb.INVITE_SENT,
            actor=None,
            actor_name="Self-registration",
            process=process,
            candidate=candidate,
            invitation=invitation,
            meta={
                "context": "self_register",
                "email_log_id": email_log.id,
            },
        )

        if test_url and _is_safe_external_url(test_url):
            return HttpResponseRedirect(test_url)

        return render(request, "customer/processes/self_register_success.html", {
            "process": process,
            "message": "Registrering klar. Vi skickar ett mejl när testlänken är redo.",
        })

    except Exception as e:
        print("❌ SELF REGISTER order_assessment failed:", str(e))
        return render(request, "customer/processes/self_register_success.html", {
            "process": process,
            "message": "Registrering klar, men vi kunde inte starta testet direkt. Du får ett mejl så snart det är redo.",
        })


@login_required
@require_POST
def remove_candidate_from_process(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id, created_by=request.user)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    log_event(
        company=process.company,
        verb=ActivityEvent.Verb.CANDIDATE_REMOVED,
        actor=request.user,
        process=process,
        candidate=invitation.candidate,
        invitation=invitation,
    )


    invitation.delete()
    messages.success(request, "Candidate removed from process.")
    return redirect("processes:process_detail", pk=process.id)



@login_required
def process_send_tests(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if process.is_historical or not process.sova_sync_enabled:
        messages.error(request, "This is a historical process and cannot send SOVA invitations.")
        return redirect("processes:process_detail", pk=process.pk)

    company = get_company_for_user(request.user)
    if not company or process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att skicka tester i denna process.")

    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    invitation_ids = request.POST.getlist("invitation_ids")
    if not invitation_ids:
        messages.warning(request, "Välj minst en kandidat.")
        return redirect("processes:process_detail", pk=process.pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process, id__in=invitation_ids)
        .select_related("candidate")
    )

    result = send_assessments_and_emails(
        process=process,
        invitations=invitations,
        actor_user=request.user,
        context="customer",
    )

    if result["sent_count"]:
        messages.success(request, f"Skickade test till {result['sent_count']} kandidat(er).")

    if result["errors"]:
        for err in result["errors"]:
            messages.error(request, f"Kunde inte skicka till {err['email']}: {err['error']}")

    if result["sent_count"] == 0:
        if result["skipped_count"]:
            messages.info(request, "Inget skickades (alla markerade var redan skickade/igång/klara).")
        else:
            messages.warning(request, "Inget skickades. Kolla felmeddelanden ovan.")

    return redirect("processes:process_detail", pk=process.pk)

@login_required
def process_candidate_detail(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if process.is_historical:
        historical_candidate = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related(
                "candidate",
                "process",
                "created_by",
            )
            .prefetch_related(
                "reports",
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        ctx = build_historical_candidate_detail_context(
            process=process,
            historical_candidate=historical_candidate,
        )

        return render(
            request,
            "customer/processes/_candidate_detail_sheet.html",
            ctx,
        )

        ctx = {
            "company": process.company,
            "process": process,
            "candidate": historical_candidate.candidate,
            "historical_candidate": historical_candidate,
            "historical_reports": historical_candidate.reports.all(),
            "is_historical": True,
            "assessment_results": assessment_results,
        }

    else:
        invitation = get_object_or_404(
            TestInvitation.objects.select_related("candidate"),
            process=process,
            candidate_id=candidate_id,
        )

        ctx = build_candidate_detail_context(
            process=process,
            invitation=invitation,
        )

        ctx["is_historical"] = False

    if is_ajax:
        return render(
            request,
            "customer/processes/_candidate_detail_sheet.html",
            ctx,
        )

    return render(
        request,
        "customer/processes/process_candidate_detail.html",
        ctx,
    )


@login_required
def process_invitation_statuses(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("You do not have access to this process.")

    qs = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("created_at")
    )

    return JsonResponse({
        "invitations": [
            {
                "id": inv.id,
                "status": inv.status,
                "completed_at": inv.completed_at.isoformat() if inv.completed_at else None,
                "sova_overall_status": getattr(inv, "sova_overall_status", "") or "",
            }
            for inv in qs
        ]
    })


@login_required
def process_archive(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att arkivera denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    obj.archive()

    log_event(
        company=company,
        verb=ActivityEvent.Verb.PROCESS_ARCHIVED,
        actor=request.user,
        process=obj,
    )

    messages.success(request, "Processen arkiverades.")
    return redirect("processes:process_list")


@login_required
def process_unarchive(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    if request.method != "POST":
        return HttpResponseForbidden("POST required.")

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att återställa denna process.")

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("You do not have access to this process.")

    obj.unarchive()
    messages.success(request, "Processen återställdes.")
    return redirect("processes:process_list")


@login_required
def process_candidate_summary_stream(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    # ---------------------------------------------------------
    # HISTORICAL CANDIDATE
    # ---------------------------------------------------------
    if process.is_historical:
        summary_owner = get_object_or_404(
            HistoricalProcessCandidate.objects
            .select_related("candidate", "process")
            .prefetch_related(
                "assessment_results__scores",
                "assessment_results__import_file",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        is_historical = True

    # ---------------------------------------------------------
    # ACTIVE CANDIDATE
    # ---------------------------------------------------------
    else:
        summary_owner = get_object_or_404(
            TestInvitation.objects.select_related(
                "candidate",
                "process",
            ),
            process=process,
            candidate_id=candidate_id,
        )

        is_historical = False

        # Active candidates must have completed all assessments.
        if summary_owner.status != "completed":
            return JsonResponse(
                {
                    "error": (
                        "Candidate has not completed "
                        "the assessments yet."
                    )
                },
                status=400,
            )

    # ---------------------------------------------------------
    # RETURN EXISTING SUMMARY
    # ---------------------------------------------------------
    if summary_owner.ai_summary:
        def existing_generator():
            yield summary_owner.ai_summary

        response = StreamingHttpResponse(
            existing_generator(),
            content_type="text/plain; charset=utf-8",
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    # ---------------------------------------------------------
    # PREVENT DUPLICATE GENERATION
    # ---------------------------------------------------------
    if summary_owner.ai_summary_status == "generating":
        return JsonResponse(
            {
                "error": (
                    "Summary is already being generated."
                )
            },
            status=409,
        )

    summary_owner.ai_summary_status = "generating"
    summary_owner.save(
        update_fields=["ai_summary_status"]
    )

    # ---------------------------------------------------------
    # STREAM GENERATION
    # ---------------------------------------------------------
    def generator():
        full_text = ""

        try:
            if is_historical:
                stream = stream_historical_candidate_summary(
                    process=process,
                    historical_candidate=summary_owner,
                )
            else:
                stream = stream_candidate_summary(
                    summary_owner
                )

            for chunk in stream:
                full_text += chunk
                yield chunk

            if is_historical:
                summary_owner.ai_summary = full_text
                summary_owner.ai_summary_status = "completed"
                summary_owner.ai_summary_generated_at = timezone.now()

                summary_owner.save(
                    update_fields=[
                        "ai_summary",
                        "ai_summary_status",
                        "ai_summary_generated_at",
                    ]
                )

            else:
                save_candidate_summary(
                    summary_owner,
                    full_text,
                )

        except Exception as error:
            summary_owner.ai_summary_status = "failed"

            summary_owner.save(
                update_fields=[
                    "ai_summary_status",
                ]
            )

            yield f"\n\n[Error: {str(error)}]"

    response = StreamingHttpResponse(
        generator(),
        content_type="text/plain; charset=utf-8",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response

@login_required
def process_candidate_purpose_fit_stream(
    request,
    process_id,
    candidate_id,
):
    print(
        f"[PURPOSE FIT] Stream requested "
        f"process={process_id}, candidate={candidate_id}",
        flush=True,
    )

    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    print(
        f"[PURPOSE FIT] Process found: "
        f"{process.id}, purpose={process.purpose}",
        flush=True,
    )

    if not user_can_access_process(request.user, process):
        print(
            "[PURPOSE FIT] Access denied",
            flush=True,
        )

        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    if not purpose_supports_fit(process):
        print(
            "[PURPOSE FIT] Purpose does not support fit",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Flexible processes do not support "
                    "purpose-fit analysis."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process",
        ),
        process=process,
        candidate_id=candidate_id,
    )

    print(
        f"[PURPOSE FIT] Invitation found: "
        f"id={invitation.id}, "
        f"status={invitation.status}, "
        f"fit_status={invitation.ai_purpose_fit_status}, "
        f"has_saved_fit={bool(invitation.ai_purpose_fit)}",
        flush=True,
    )

    if invitation.status != "completed":
        print(
            "[PURPOSE FIT] Candidate not completed",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Candidate assessments are not completed yet."
                )
            },
            status=400,
        )

    if invitation.ai_purpose_fit:
        print(
            "[PURPOSE FIT] Returning saved result",
            flush=True,
        )

        def existing_generator():
            yield json.dumps({
                "type": "saved_result",
                "data": invitation.ai_purpose_fit,
                "status": invitation.ai_purpose_fit_status,
            }) + "\n"

        response = StreamingHttpResponse(
            existing_generator(),
            content_type="application/x-ndjson; charset=utf-8",
        )

        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"

        return response

    if invitation.ai_purpose_fit_status == "generating":
        print(
            "[PURPOSE FIT] Already marked as generating",
            flush=True,
        )

        return JsonResponse(
            {
                "error": (
                    "Purpose-fit analysis is already being generated."
                )
            },
            status=409,
        )

    invitation.ai_purpose_fit_status = "generating"
    invitation.save(update_fields=[
        "ai_purpose_fit_status",
    ])

    print(
        "[PURPOSE FIT] Status changed to generating",
        flush=True,
    )

    def generator():
        purpose_fit = create_empty_purpose_fit(
            invitation
        )

        received_done_event = False

        try:
            print(
                "[PURPOSE FIT] Starting OpenAI stream",
                flush=True,
            )

            for event in stream_candidate_purpose_fit(
                invitation
            ):
                print(
                    "[PURPOSE FIT] Event received:",
                    event,
                    flush=True,
                )

                purpose_fit = apply_purpose_fit_event(
                    purpose_fit,
                    event,
                )

                if event.get("type") == "done":
                    received_done_event = True

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

            print(
                "[PURPOSE FIT] OpenAI stream finished",
                flush=True,
            )

            if not received_done_event:
                print(
                    "[PURPOSE FIT] Adding missing done event",
                    flush=True,
                )

                yield json.dumps({
                    "type": "done",
                }) + "\n"

            save_candidate_purpose_fit(
                invitation,
                purpose_fit,
            )

            print(
                "[PURPOSE FIT] Result saved successfully",
                flush=True,
            )

        except Exception as exc:
            print(
                "[PURPOSE FIT] ERROR:",
                repr(exc),
                flush=True,
            )

            invitation.ai_purpose_fit_status = "failed"
            invitation.save(update_fields=[
                "ai_purpose_fit_status",
            ])

            yield json.dumps({
                "type": "error",
                "message": str(exc),
            }, ensure_ascii=False) + "\n"

    response = StreamingHttpResponse(
        generator(),
        content_type="application/x-ndjson; charset=utf-8",
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    print(
        "[PURPOSE FIT] Streaming response created",
        flush=True,
    )

    return response


@login_required
@require_POST
def process_candidate_purpose_fit_regenerate(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    if not purpose_supports_fit(process):
        return JsonResponse(
            {
                "error": (
                    "Flexible processes do not support "
                    "purpose-fit analysis."
                )
            },
            status=400,
        )

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id,
    )

    invitation.ai_purpose_fit = {}
    invitation.ai_purpose_fit_status = "not_started"
    invitation.ai_purpose_fit_generated_at = None
    invitation.ai_purpose_fit_purpose = ""

    invitation.save(
        update_fields=[
            "ai_purpose_fit",
            "ai_purpose_fit_status",
            "ai_purpose_fit_generated_at",
            "ai_purpose_fit_purpose",
        ]
    )

    return JsonResponse(
        {
            "ok": True,
            "stream_url": reverse(
                "processes:process_candidate_purpose_fit_stream",
                kwargs={
                    "process_id": process.id,
                    "candidate_id": candidate_id,
                },
            ),
        }
    )

@login_required
def process_create_v2(request):
    client = SovaClient()
    error = None

    # --------------------------------------------------
    # 1. Hämta Sova-projekt från API
    # --------------------------------------------------
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # --------------------------------------------------
    # 2. Hämta ProjectMeta så vi kan hitta namn, tester osv
    # --------------------------------------------------
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    project_id_map = {}
    template_cards = []

    for account in accounts:
        acc = (account.get("code") or "").strip()

        for project in (account.get("projects") or []):
            proj_code = (project.get("code") or "").strip()
            sova_name = (project.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = project.get("id")

            meta = meta_map.get((acc, proj_code))
            title = getattr(meta, "intern_name", None) or sova_name

            description = ""
            tests = []
            languages = []

            if meta:
                description = (getattr(meta, "notes", None) or "").strip()

                tests_raw = (getattr(meta, "tests", None) or "").strip()
                if tests_raw:
                    tests = [t.strip() for t in tests_raw.split(",") if t.strip()]

                languages_raw = (getattr(meta, "languages", None) or "").strip()
                if languages_raw:
                    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon_class": get_template_icon_class(tests, title),
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": project.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # --------------------------------------------------
    # 3. Hämta company
    # --------------------------------------------------
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )

    if not company_id:
        messages.error(request, "You are not linked to a company.")
        return redirect("processes:process_list")

    company = get_object_or_404(Company, pk=company_id)

    # --------------------------------------------------
    # 4. POST: skapa processen
    # --------------------------------------------------
    if request.method == "POST":
        form = TestProcessWizardCreateForm(request.POST)

        if form.is_valid():
            purpose = form.cleaned_data.get("purpose")
            selected_tests = form.cleaned_data.get("selected_tests") or []
            name = (form.cleaned_data.get("name") or "").strip()

            # Om användaren inte skrev namn, skapa ett automatiskt
            if not name:
                name = build_default_process_name(
                    purpose=purpose,
                    selected_tests=selected_tests,
                )

            # --------------------------------------------------
            # 5. Tillfällig dev-mapping:
            # selected_tests -> Sova account/project
            # --------------------------------------------------
            resolved_template = resolve_dev_sova_template(selected_tests)

            if not resolved_template:
                form.add_error(
                    "selected_tests",
                    "Please select at least Personality or Motivation in the current development environment."
                )

                return render(request, "customer/processes/process_create_v2.html", {
                    "form": form,
                    "error": error,
                    "process_purposes": PROCESS_PURPOSES,
                    "available_tests": AVAILABLE_TESTS,
                    "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
                    "template_cards": template_cards,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            acc = resolved_template["account_code"]
            proj = resolved_template["project_code"]
            value = f"{acc}|{proj}"

            # --------------------------------------------------
            # 6. Hämta org unit
            # --------------------------------------------------
            active_unit_id = request.session.get("active_org_unit_id")
            accessible_ids = get_accessible_orgunit_ids(request.user, company)

            if not active_unit_id or int(active_unit_id) not in accessible_ids:
                fallback_id = next(iter(accessible_ids), None)

                if not fallback_id:
                    form.add_error(
                        None,
                        "You do not have an assigned org unit, so a process cannot be created."
                    )

                    return render(request, "customer/processes/process_create_v2.html", {
                        "form": form,
                        "error": error,
                        "process_purposes": PROCESS_PURPOSES,
                        "available_tests": AVAILABLE_TESTS,
                        "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
                        "template_cards": template_cards,
                        "templates_count": len(template_cards),
                        "accounts_count": len(accounts),
                    })

                active_unit_id = fallback_id
                request.session["active_org_unit_id"] = active_unit_id

            # --------------------------------------------------
            # 7. Skapa TestProcess
            # --------------------------------------------------
            obj = TestProcess(
                name=name,
                company=company,
                org_unit_id=int(active_unit_id),
                provider="sova",
                account_code=acc,
                project_code=proj,
                created_by=request.user,
                purpose=purpose,
                selected_tests=selected_tests,
            )

            # --------------------------------------------------
            # 8. Sätt project_name_snapshot
            # --------------------------------------------------
            meta = meta_map.get((acc, proj))

            if meta and getattr(meta, "intern_name", None):
                obj.project_name_snapshot = meta.intern_name
            else:
                match = next(
                    (t for t in template_cards if t["value"] == value),
                    None
                )
                obj.project_name_snapshot = (
                    match["sova_name"] if match else proj
                )

            obj.save()

            # --------------------------------------------------
            # 9. Spara labels
            # --------------------------------------------------
            label_names = form.cleaned_data.get("labels_text") or []

            # Om labels_text råkar komma in som string istället för lista
            if isinstance(label_names, str):
                label_names = [
                    item.strip()
                    for item in label_names.split(",")
                    if item.strip()
                ]

            if label_names:
                label_objs = []

                for label_name in label_names:
                    lab, _ = ProcessLabel.objects.get_or_create(
                        company=company,
                        name=label_name,
                    )
                    label_objs.append(lab)

                obj.labels.set(label_objs)
            else:
                obj.labels.clear()

            # --------------------------------------------------
            # 10. Logga activity
            # --------------------------------------------------
            log_event(
                company=company,
                verb=ActivityEvent.Verb.PROCESS_CREATED,
                actor=request.user,
                process=obj,
                meta={
                    "process_name": obj.name,
                    "purpose": obj.purpose,
                    "selected_tests": obj.selected_tests,
                    "resolved_sova_template": value,
                    "sova_project_id": project_id_map.get(value),
                },
            )

            messages.success(request, "Testprocessen skapades.")
            return redirect("processes:process_detail", pk=obj.pk)

        messages.error(request, "The process could not be created. Please check the fields.")

    # --------------------------------------------------
    # 11. GET: visa tom form
    # --------------------------------------------------
    else:
        form = TestProcessWizardCreateForm()

    return render(request, "customer/processes/process_create_v2.html", {
        "form": form,
        "error": error,
        "process_purposes": PROCESS_PURPOSES,
        "available_tests": AVAILABLE_TESTS,
        "purpose_recommended_tests": PURPOSE_RECOMMENDED_TESTS,
        "template_cards": template_cards,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })


def build_historical_candidate_detail_context(
    process,
    historical_candidate,
):
    """
    Build candidate sheet context for a historical candidate.

    Historical assessment data is normalised through
    build_historical_candidate_profile() and then exposed using the same
    context keys as the regular candidate sheet.

    Historical candidates always use general insight mode because no
    original process purpose or context is available.
    """
    candidate = historical_candidate.candidate

    profile = build_historical_candidate_profile(
        historical_candidate
    )

    assessment_results = profile["assessment_results"]

    motivation_competencies = profile["motivation_competencies"]
    personality_competencies = profile["personality_competencies"]
    team_style_scores = profile["team_style_scores"]
    ability_results = profile["ability_results"]

    has_motivation_results = profile["has_motivation_results"]
    has_personality_results = profile["has_personality_results"]
    has_ability_results = profile["has_ability_results"]
    has_any_results = profile["has_any_results"]

    # Historical extracts contain completed result data.
    all_assessments_completed = has_any_results

    verbal_result = ability_results.get("verbal")
    logical_result = ability_results.get("logical")
    numerical_result = ability_results.get("numerical")

    verbal_percentile = (
        verbal_result.get("value")
        if verbal_result
        else None
    )

    logical_percentile = (
        logical_result.get("value")
        if logical_result
        else None
    )

    numerical_percentile = (
        numerical_result.get("value")
        if numerical_result
        else None
    )

    has_verbal_results = verbal_result is not None
    has_logical_results = logical_result is not None
    has_numerical_results = numerical_result is not None

    # -------------------------------------------------------------------------
    # Convert the common profile into structures already used by the template
    # -------------------------------------------------------------------------

    motivation_results = []
    mq_competencies = []

    for item in motivation_competencies:
        score_value = item.get("score")

        motivation_results.append({
            "activity": "Motivation Questionnaire",
            "competency": item.get("competency") or item.get("name"),
            "score": score_value,
            "stive": item.get("stive", score_value),
            "stive_rounded": item.get(
                "stive_rounded",
                round(score_value) if score_value is not None else None,
            ),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "assessment_centre": None,
            "source": "historical_import",
        })

        mq_competencies.append({
            "competency": item.get("competency") or item.get("name"),
            "score": score_value,
            "stive": item.get("stive", score_value),
            "stive_rounded": item.get(
                "stive_rounded",
                round(score_value) if score_value is not None else None,
            ),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "source": "historical_import",
        })

    normalised_personality_competencies = []

    for item in personality_competencies:
        normalised_personality_competencies.append({
            "competency": item.get("competency") or item.get("name"),
            "score": item.get("score"),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "category": item.get("category"),
            "source": "historical_import",
        })

    normalised_team_style_scores = []

    for item in team_style_scores:
        normalised_team_style_scores.append({
            "competency": item.get("competency") or item.get("name"),
            "score": item.get("score"),
            "sten": item.get("sten"),
            "sten_rounded": item.get("sten_rounded"),
            "percentile": item.get("percentile"),
            "category": "team_style",
            "source": "historical_import",
        })

    motivation_results = sorted(
        motivation_results,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    mq_competencies = sorted(
        mq_competencies,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    normalised_personality_competencies = sorted(
        normalised_personality_competencies,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    normalised_team_style_scores = sorted(
        normalised_team_style_scores,
        key=lambda item: (
            item.get("competency") or ""
        ).lower(),
    )

    # -------------------------------------------------------------------------
    # Shared score helpers
    # -------------------------------------------------------------------------

    def safe_score(item):
        """
        Return the first available numeric value.

        Explicit None checks are used so a legitimate value of 0 is not lost.
        """
        for key in (
            "score",
            "sten_rounded",
            "stive_rounded",
            "percentile",
        ):
            value = item.get(key)

            if value is not None:
                return value

        return -1

    top_motivations = sorted(
        mq_competencies,
        key=safe_score,
        reverse=True,
    )[:3]

    combined_personality_scores = (
        normalised_personality_competencies
        + normalised_team_style_scores
    )

    top_personality_traits = sorted(
        combined_personality_scores,
        key=safe_score,
        reverse=True,
    )[:3]

    motivation_development_areas = sorted(
        mq_competencies,
        key=safe_score,
    )[:2]

    personality_development_areas = sorted(
        combined_personality_scores,
        key=safe_score,
    )[:2]

    # -------------------------------------------------------------------------
    # Data supplied to the general insight engine
    # -------------------------------------------------------------------------

    general_insight_input = build_general_insight_input(
        personality_competencies=normalised_personality_competencies,
        motivation_competencies=mq_competencies,
        verbal_percentile=verbal_percentile,
        logical_percentile=logical_percentile,
        numerical_percentile=numerical_percentile,
    )

    # Temporary development logging.
    # Remove these prints once imported profiles have been verified.
    print("=== HISTORICAL GENERAL INSIGHT INPUT ===")
    print(json.dumps(
        general_insight_input,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))
    print("=== /HISTORICAL GENERAL INSIGHT INPUT ===")

    # -------------------------------------------------------------------------
    # Ability reports
    # -------------------------------------------------------------------------

    ability_reports_for_ui = {
        "overview": [],
        "verbal": (
            build_cognitive_reports_for_test(
                test_key="verbal",
                percentile=verbal_percentile,
            )
            if verbal_percentile is not None
            else None
        ),
        "logical": (
            build_cognitive_reports_for_test(
                test_key="logical",
                percentile=logical_percentile,
            )
            if logical_percentile is not None
            else None
        ),
        "numerical": (
            build_cognitive_reports_for_test(
                test_key="numerical",
                percentile=numerical_percentile,
            )
            if numerical_percentile is not None
            else None
        ),
    }

    if ability_reports_for_ui["verbal"]:
        ability_reports_for_ui["overview"].append({
            "key": "verbal",
            "label": "Verbal",
            "percentile": verbal_percentile,
        })

    if ability_reports_for_ui["logical"]:
        ability_reports_for_ui["overview"].append({
            "key": "logical",
            "label": "Logical",
            "percentile": logical_percentile,
        })

    if ability_reports_for_ui["numerical"]:
        ability_reports_for_ui["overview"].append({
            "key": "numerical",
            "label": "Numerical",
            "percentile": numerical_percentile,
        })

    # -------------------------------------------------------------------------
    # Motivation reports
    # -------------------------------------------------------------------------

    motivation_scores = build_scores_by_competency(
        mq_competencies
    )

    motivation_reports_for_ui = []

    if has_motivation_results:
        motivation_reports_for_ui = [
            build_practitioner_report(
                competencies=mq_competencies,
            ),
            build_manager_report(
                competencies=mq_competencies,
            ),
            build_motivation_coaching_report(
                competencies=mq_competencies,
            ),
            build_candidate_report(
                competencies=mq_competencies,
            ),
        ]

    # -------------------------------------------------------------------------
    # Personality report placeholders
    # -------------------------------------------------------------------------

    personality_reports = []

    if has_personality_results:
        personality_reports = [
            {
                "report_name": "Personality overview",
                "description": (
                    "Generated from imported historical personality scores."
                ),
            },
            {
                "report_name": "Team style overview",
                "description": (
                    "Generated from imported historical team style scores."
                ),
            },
        ]

    available_reports_count = 0

    if has_verbal_results:
        available_reports_count += 2

    if has_logical_results:
        available_reports_count += 2

    if has_numerical_results:
        available_reports_count += 2

    if has_motivation_results:
        available_reports_count += len(
            motivation_reports_for_ui
        )

    if has_personality_results:
        available_reports_count += len(
            personality_reports
        )

    # -------------------------------------------------------------------------
    # General candidate insights
    #
    # This is the temporary deterministic fallback. Later, replace this block
    # with the exact same insight generator used by active general-mode profiles.
    # -------------------------------------------------------------------------

    candidate_insights = {
        "summary": None,
        "key_strengths": [],
        "areas_to_explore": [],
        "questions": [],
        "fit": None,
    }

    if has_any_results:
        candidate_insights["summary"] = {
            "body": (
                "This candidate profile is based on structured historical "
                "SOVA assessment data. The insights are presented in general "
                "mode because no original process purpose or role context is "
                "available."
            )
        }

    for item in top_personality_traits[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["key_strengths"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's higher imported personality "
                "or team style scores."
            ),
            "how_it_may_show": (
                "This may appear as a recurring behavioural preference in "
                "relevant work situations."
            ),
            "why_it_matters": (
                "This theme may be useful when considering the candidate's "
                "general work style and contribution."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in top_motivations[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["key_strengths"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's higher imported motivation "
                "scores."
            ),
            "how_it_may_show": (
                "This may indicate the conditions or activities that tend "
                "to energise and engage the candidate."
            ),
            "why_it_matters": (
                "Motivational drivers can affect engagement, satisfaction "
                "and longer-term retention."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in personality_development_areas[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["areas_to_explore"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's lower imported personality "
                "or team style scores."
            ),
            "explore_through": (
                "Ask for examples of situations where this behaviour is more "
                "or less natural for the candidate."
            ),
            "what_to_listen_for": (
                "Listen for context, self-awareness and strategies the "
                "candidate uses to adapt."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    for item in motivation_development_areas[:2]:
        competency = item.get("competency")
        value = safe_score(item)

        candidate_insights["areas_to_explore"].append({
            "title": competency,
            "body": (
                "This is one of the candidate's lower imported motivation "
                "scores."
            ),
            "explore_through": (
                "Ask which types of work situations tend to reduce energy, "
                "interest or engagement."
            ),
            "what_to_listen_for": (
                "Listen for what the candidate needs from the role, manager "
                "and working environment."
            ),
            "evidence": [
                f"{competency}: {value}"
            ],
        })

    if has_any_results:
        candidate_insights["questions"] = [
            {
                "category": "strengths",
                "category_label": "Strength",
                "question": (
                    "Which parts of your work tend to bring out your "
                    "strongest qualities?"
                ),
                "why": (
                    "This helps validate whether the imported assessment "
                    "profile matches the candidate's own experience."
                ),
                "listen_for": (
                    "Concrete examples and consistency with the strongest "
                    "assessment themes."
                ),
            },
            {
                "category": "explore",
                "category_label": "Explore",
                "question": (
                    "Are there situations where your usual working style "
                    "becomes less effective?"
                ),
                "why": (
                    "This helps add context to lower or less preferred scores "
                    "without treating them automatically as weaknesses."
                ),
                "listen_for": (
                    "Self-awareness, nuance and practical adaptation "
                    "strategies."
                ),
            },
            {
                "category": "motivation",
                "category_label": "Motivation",
                "question": (
                    "What type of working environment gives you the most "
                    "energy over time?"
                ),
                "why": (
                    "This helps connect imported motivation scores to actual "
                    "working conditions."
                ),
                "listen_for": (
                    "Drivers, demotivators and environmental preferences."
                ),
            },
        ]

    # -------------------------------------------------------------------------
    # Header assessment/activity information
    # -------------------------------------------------------------------------

    sent_assessments = []

    for result in assessment_results:
        sent_assessments.append({
            "activity": result.assessment_type.title(),
            "status": (
                (result.status or "completed")
                .strip()
                .lower()
            ),
        })

    all_competencies = (
        mq_competencies
        + normalised_personality_competencies
        + normalised_team_style_scores
    )

    return {
        "company": process.company,
        "process": process,
        "candidate": candidate,

        "historical_candidate": historical_candidate,
        "historical_reports": historical_candidate.reports.all(),
        "assessment_results": assessment_results,

        "is_historical": True,

        # Historical candidates have no live invitation.
        "invitation": None,
        "inv": None,
        "assessment_url": None,
        "activity_events": [],
        "email_logs_by_id": {},

        # Header information.
        "sent_assessments": sent_assessments,
        "tests_sent_count": assessment_results.count(),
        "tests_completed_count": assessment_results.count(),

        # Shared result flags.
        "has_motivation_results": has_motivation_results,
        "has_personality_results": has_personality_results,
        "has_ability_results": has_ability_results,
        "has_verbal_results": has_verbal_results,
        "has_logical_results": has_logical_results,
        "has_numerical_results": has_numerical_results,
        "has_any_results": has_any_results,
        "all_assessments_completed": all_assessments_completed,

        # Normalised assessment data.
        "motivation_results": motivation_results,
        "mq_competencies": mq_competencies,
        "personality_competencies": (
            normalised_personality_competencies
        ),
        "team_style_scores": normalised_team_style_scores,
        "all_competencies": all_competencies,
        "ability_results": ability_results,

        "verbal_percentile": verbal_percentile,
        "logical_percentile": logical_percentile,
        "numerical_percentile": numerical_percentile,

        # Existing report builders.
        "motivation_scores": motivation_scores,
        "motivation_reports_for_ui": motivation_reports_for_ui,
        "ability_reports_for_ui": ability_reports_for_ui,
        "personality_reports": personality_reports,
        "available_reports_count": available_reports_count,

        # General insight data.
        "candidate_insights": candidate_insights,
        "general_insight_input": general_insight_input,

        "top_motivations": top_motivations,
        "top_personality_traits": top_personality_traits,
        "motivation_development_areas": (
            motivation_development_areas
        ),
        "personality_development_areas": (
            personality_development_areas
        ),

        # Historical candidates always use general mode.
        "purpose_report": None,
        "report_mode": "general",
        "context_config": {},
        "show_context_prompt": False,
        "summary_owner": historical_candidate,

        # Compatibility keys expected elsewhere in the template.
        "activities": [],
        "project_results": {},
        "project_scores": [],
        "competency_scores": [],
        "overall_score": None,
        "reports": [],
    }


@login_required
@require_POST
def process_candidate_summary_regenerate(
    request,
    process_id,
    candidate_id,
):
    process = get_object_or_404(
        TestProcess,
        pk=process_id,
    )

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden(
            "You do not have access to this process."
        )

    if process.is_historical:
        summary_owner = get_object_or_404(
            HistoricalProcessCandidate.objects,
            process=process,
            candidate_id=candidate_id,
        )

    else:
        summary_owner = get_object_or_404(
            TestInvitation.objects,
            process=process,
            candidate_id=candidate_id,
        )

    summary_owner.ai_summary = ""
    summary_owner.ai_summary_status = "not_started"
    summary_owner.ai_summary_generated_at = None

    summary_owner.save(
        update_fields=[
            "ai_summary",
            "ai_summary_status",
            "ai_summary_generated_at",
        ]
    )

    return JsonResponse({
        "ok": True,
        "stream_url": reverse(
            "processes:process_candidate_summary_stream",
            kwargs={
                "process_id": process.id,
                "candidate_id": candidate_id,
            },
        ),
    })