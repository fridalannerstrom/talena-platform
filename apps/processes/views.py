from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from .forms import TestProcessCreateForm, CandidateCreateForm
from .models import TestProcess, Candidate, TestInvitation, SelfRegistration, ProcessLabel
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

from urllib.parse import urlparse
from django.http import HttpResponseRedirect
from django.db.models import Count, Q

from django.http import HttpResponse
from apps.accounts.utils.permissions import filter_by_user_accounts, user_can_access_account
from apps.accounts.utils.org_access import get_effective_orgunit_permissions, user_can_view_process, user_can_edit_process, get_company_for_user
from django.http import HttpResponseForbidden

from apps.processes.services.send_tests import send_assessments_and_emails

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

def build_candidate_detail_context(process, invitation):
    candidate = invitation.candidate
    activities = invitation.sova_activities or []

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

    activity_count = len(activities)

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

    sorted_mq_desc = sorted(
        mq_competencies,
        key=safe_motivation_score,
        reverse=True,
    )

    sorted_personality_desc = sorted(
        personality_competencies,
        key=safe_personality_score,
        reverse=True,
    )

    top_motivations = sorted_mq_desc[:3]
    top_personality_traits = sorted_personality_desc[:3]

    sorted_mq_asc = sorted(
        mq_competencies,
        key=safe_motivation_score,
    )

    sorted_personality_asc = sorted(
        personality_competencies,
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

    return {
        "company": process.company,
        "process": process,
        "invitation": invitation,
        "inv": invitation,
        "candidate": candidate,
        "activity_events": activity_events,

        "activities": activities,
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

    # ✅ Tab: Aktiva / Arkiverade
    show_archived = request.GET.get("archived") == "1"

    processes = (
        TestProcess.objects
        .filter(process_q)
        .filter(is_archived=show_archived)
        .annotate(candidates_count=Count("invitations", distinct=True))
        .order_by("-created_at")
        .prefetch_related("labels")
    )

    # ✅ Bygg edit-permissions EFTER att processes finns
    can_edit_by_process_id = {}
    for p in processes:
        perm = perms.get(p.org_unit_id)
        can_edit = (perm == "editor") or (perm == "own" and p.created_by_id == request.user.id)
        can_edit_by_process_id[p.id] = can_edit

    # ---- ProjectMeta lookup (tests) ----
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
        meta_by_key = {f"{m.account_code}::{m.project_code}": m for m in metas}

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

            icon = (getattr(meta, "icon", None) or "").strip() if meta else ""
            if not icon:
                icon = "layers"
            template_cards.append({
                "value": value,
                "title": title,
                "description": description,
                "tests": tests,
                "languages": languages,
                "icon": icon,
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
                form.add_error(None, "Du är inte kopplad till något företag.")
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
                    form.add_error(None, "Du har ingen enhet (OrgUnit) tilldelad, kan inte skapa process.")
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
                form.add_error(None, "Du saknar primär enhet (OrgUnit). Kontakta admin.")
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

        messages.error(request, "Kunde inte skapa processen. Kontrollera fälten.")
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


def process_update(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)

    company = get_company_for_user(request.user)
    if not company or obj.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, obj):
        return HttpResponseForbidden("Du har inte behörighet att redigera denna process.")

    # ✅ Säkerhetskontroll
    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    old_acc = (obj.account_code or "").strip()
    old_proj = (obj.project_code or "").strip()
    locked = obj.is_template_locked()

    client = SovaClient()
    error = None

    # 1) Hämta accounts + projects från SOVA
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # 2) Hämta meta för intern_name
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    # 3) Bygg choices + template_cards
    choices = []
    template_cards = []

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

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
            "account_code": acc,
            "project_code": proj_code,
            "sova_name": sova_name,
            "sova_project_id": p.get("id"),
        })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST, instance=obj)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            updated = form.save(commit=False)

            value = form.cleaned_data["sova_template"]  # "ACC|PROJ"
            acc, proj = value.split("|", 1)
            acc = acc.strip()
            proj = proj.strip()

            # 🔒 template lock check
            if locked and ((acc != old_acc) or (proj != old_proj)):
                form.add_error(
                    None,
                    "Du kan inte ändra testpaket efter att tester har skickats i processen."
                )
                # Rendera tillbaka så användaren inte tappar ändringar
                return render(request, "customer/processes/process_edit.html", {
                    "form": form,
                    "process": obj,
                    "error": error,
                    "choices_count": len(choices),
                    "template_cards": template_cards,
                    "template_locked": locked,
                })

            updated.provider = "sova"
            updated.account_code = acc
            updated.project_code = proj

            # Snapshot: intern_name om finns, annars sova_name
            meta = meta_map.get((acc, proj))
            if meta and getattr(meta, "intern_name", None):
                updated.project_name_snapshot = meta.intern_name
            else:
                match = next((t for t in template_cards if t["value"] == value), None)
                updated.project_name_snapshot = (match["sova_name"] if match else proj)

            updated.save()

            # ✅ Spara labels (M2M) här, efter save()
            label_names = form.cleaned_data.get("labels_text", [])
            label_objs = []
            for name in label_names:
                lab, _ = ProcessLabel.objects.get_or_create(
                    company_id=updated.company_id,
                    name=name,
                )
                label_objs.append(lab)

            updated.labels.set(label_objs)

            messages.success(request, "Processen uppdaterades.")
            return redirect("processes:process_list")

        messages.error(request, "Kunde inte spara. Kontrollera fälten.")

    else:
        form = TestProcessCreateForm(instance=obj)
        form.fields["sova_template"].choices = choices
        form.initial["sova_template"] = f"{obj.account_code}|{obj.project_code}"

    return render(request, "customer/processes/process_edit.html", {
        "form": form,
        "process": obj,
        "error": error,
        "choices_count": len(choices),
        "template_cards": template_cards,
        "template_locked": locked,
    })


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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

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
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    # ✅ måste tillhöra samma company
    if process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    # ✅ nya, riktiga regeln (inkl own-only)
    if not user_can_view_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

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

    sent_count = status_counts.get("sent", 0)
    started_count = status_counts.get("started", 0)
    completed_count = status_counts.get("completed", 0)
    expired_count = status_counts.get("expired", 0)

    can_edit = user_can_edit_process(request.user, company, process)

    total_sent = sent_count + started_count + completed_count
    not_started = sent_count

    activity_events = (
        ActivityEvent.objects
        .filter(company=company, process=process)
        .select_related("actor", "candidate", "invitation")
        [:50]
    )

    context = {
        "process": process,
        "invitations": invitations,
        "meta": meta,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        "status_counts": status_counts,
        "can_edit": can_edit,
        "activity_events": activity_events,
        "kpis": {
            "total_sent": total_sent,
            "started": started_count,
            "completed": completed_count,
            "not_started": not_started,
            "expired": expired_count,
            "total_candidates": invitations.count(),
        },
    }

    return render(request, "customer/processes/process_detail.html", context)



@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")
    
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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")
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

    company = get_company_for_user(request.user)
    if not company or process.company_id != company.id:
        return HttpResponseForbidden("No access.")

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden("Du har inte behörighet att skicka tester i denna process.")

    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    invitation = get_object_or_404(
        TestInvitation.objects.select_related("candidate"),
        process=process,
        candidate_id=candidate_id,
    )

    ctx = build_candidate_detail_context(
        process=process,
        invitation=invitation,
    )

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

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
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    obj.unarchive()
    messages.success(request, "Processen återställdes.")
    return redirect("processes:process_list")


@login_required
def process_candidate_summary_stream(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id)

    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    invitation = get_object_or_404(
        TestInvitation.objects.select_related("candidate"),
        process=process,
        candidate_id=candidate_id
    )

    # Bara generera summary för färdiga tester
    if invitation.status != "completed":
        return JsonResponse({"error": "Candidate is not completed yet."}, status=400)

    # Om summary redan finns, streama tillbaka den direkt
    if invitation.ai_summary:
        def existing_generator():
            yield invitation.ai_summary

        resp = StreamingHttpResponse(existing_generator(), content_type="text/plain; charset=utf-8")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp

    # Om någon annan generering redan pågår
    if invitation.ai_summary_status == "generating":
        return JsonResponse({"error": "Summary is already being generated."}, status=409)

    invitation.ai_summary_status = "generating"
    invitation.save(update_fields=["ai_summary_status"])

    def generator():
        full_text = ""

        try:
            for chunk in stream_candidate_summary(invitation):
                full_text += chunk
                yield chunk

            save_candidate_summary(invitation, full_text)

        except Exception as e:
            invitation.ai_summary_status = "failed"
            invitation.save(update_fields=["ai_summary_status"])
            yield f"\n\n[Error: {str(e)}]"

    resp = StreamingHttpResponse(generator(), content_type="text/plain; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp