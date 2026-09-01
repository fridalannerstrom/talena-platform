from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from apps.core.integrations.sova import SovaClient
from apps.core.utils.auth import is_admin

from apps.processes.models import (
    AIPromptTemplate,
    AIPromptTemplateVersion,
)

from django.db import transaction

from apps.core.ai.prompt_templates import (
    get_ai_prompt_definition,
    get_default_ai_prompt,
    list_ai_prompt_definitions,
)

from apps.core.ai.prompt_playground import (
    get_playground_sample_data,
    is_prompt_playground_available,
)

import inspect

from django.contrib import messages

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.processes.models import Candidate, TestProcess, TestInvitation
from apps.accounts.utils.permissions import filter_by_user_accounts

from apps.accounts.models import CompanyMember

from apps.accounts.utils.permissions import get_user_accessible_orgunits

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation
from django.shortcuts import get_object_or_404, render
from apps.accounts.utils.org_access import get_effective_orgunit_permissions
from django.db.models import Q, Count
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from apps.projects.models import ProjectMeta

from apps.accounts.models import Company, OrgUnit, CompanyMember, UserInvite

from django.core.paginator import Paginator

User = get_user_model()

def tokens_to_q(tokens, fields):
    """
    Bygger en Q där ALLA tokens måste matcha,
    och varje token kan matcha i valfritt av fälten (OR).
    """
    q_obj = Q()
    for t in tokens:
        part = Q()
        for f in fields:
            part |= Q(**{f"{f}__icontains": t})
        q_obj &= part
    return q_obj


def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})


def health(request):
    return JsonResponse({"status": "ok"})

def root_redirect(request):
    return redirect("core:login")


@login_required
def post_login_redirect(request):
    if is_admin(request.user):
        return redirect("core:admin_dashboard")
    return redirect("core:customer_dashboard")


def _get_sova_accounts():
    try:
        return SovaClient().get_accounts_with_projects(), None
    except Exception as e:
        return [], str(e)


@login_required
def customer_dashboard(request):
    # Customer och admin använder samma Talena-workspace.
    # Företag och datatillgång styrs via CompanyMember
    # och användarens OrgUnit-behörigheter.

    # 1) Hämta SOVA-accounts
    accounts, error = _get_sova_accounts()

    # 2) Hämta userns company
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )
    company = get_object_or_404(Company, pk=company_id)

    # 3) Bygg samma accesslogik som process_list()
    perms = get_effective_orgunit_permissions(request.user, company)

    own_ids = [uid for uid, p in perms.items() if p == "own"]
    other_ids = [uid for uid, p in perms.items() if p in ("viewer", "editor")]

    process_q = Q(company=company) & (
        Q(org_unit_id__in=other_ids) |
        Q(org_unit_id__in=own_ids, created_by=request.user)
    )

    accessible_processes = (
        TestProcess.objects
        .filter(process_q)
        .filter(is_archived=False)
        .annotate(candidates_count=Count("invitations", distinct=True))
        .select_related("org_unit")
        .prefetch_related("labels")
        .order_by("-created_at")
    )

    accessible_process_ids = accessible_processes.values_list("id", flat=True)

    activity_events = (
        ActivityEvent.objects
        .filter(
            company=company,
            process_id__in=accessible_process_ids,
        )
        .select_related("actor", "process", "candidate", "invitation")
        .order_by("-created_at")[:10]
    )

    # --- ProjectMeta lookup för testmallarnas metadata ---
    latest_processes = list(accessible_processes[:5])

    keys = {
        (p.account_code, p.project_code)
        for p in latest_processes
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

    # --- Översikt / Stats ---
    total_processes = accessible_processes.count()

    invitations_qs = TestInvitation.objects.filter(process__in=accessible_processes)

    # Dashboard stats som kandidatflöde:
    # Sent/Invited = kandidater som fått tillgång, även self-registration
    sent_count = invitations_qs.filter(
        Q(status__in=["sent", "started", "completed", "expired"]) |
        Q(source="self_registered")
    ).count()

    started_count = invitations_qs.filter(
        status__in=["started", "completed"]
    ).count()

    completed_count = invitations_qs.filter(status="completed").count()

    stats = {
        "processes": total_processes,
        "sent": sent_count,
        "started": started_count,
        "completed": completed_count,
    }

    return render(
        request,
        "customer/core/layouts/customer_dashboard.html",
        {
            "accounts": accounts,
            "error": error,
            "total_processes": total_processes,
            "processes": latest_processes,
            "stats": stats,
            "activity_events": activity_events,
            "meta_by_key": meta_by_key,
        }
    )


@login_required
@login_required
def customer_activity(request):
    """
    Show activity from all test processes the current user
    has permission to access.
    """

    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )

    company = get_object_or_404(
        Company,
        pk=company_id,
    )

    permissions = get_effective_orgunit_permissions(
        request.user,
        company,
    )

    own_org_unit_ids = [
        org_unit_id
        for org_unit_id, permission in permissions.items()
        if permission == "own"
    ]

    accessible_org_unit_ids = [
        org_unit_id
        for org_unit_id, permission in permissions.items()
        if permission in ("viewer", "editor")
    ]

    process_filter = Q(company=company) & (
        Q(org_unit_id__in=accessible_org_unit_ids)
        |
        Q(
            org_unit_id__in=own_org_unit_ids,
            created_by=request.user,
        )
    )

    accessible_process_ids = (
        TestProcess.objects
        .filter(process_filter)
        .values_list("id", flat=True)
    )

    activity_queryset = (
        ActivityEvent.objects
        .filter(
            company=company,
            process_id__in=accessible_process_ids,
        )
        .select_related(
            "actor",
            "process",
            "candidate",
            "invitation",
        )
        .order_by("-created_at")
    )

    paginator = Paginator(
        activity_queryset,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "customer/core/activity_list.html",
        {
            "activity_events": page_obj.object_list,
            "page_obj": page_obj,
        },
    )


@login_required
def admin_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    accounts, error = _get_sova_accounts()

    companies_qs = (
        Company.objects
        .annotate(
            member_count=Count("memberships", distinct=True),
            orgunit_count=Count("org_units", distinct=True),
            process_count=Count("processes", distinct=True),
            pending_members=Count(
                "memberships",
                filter=Q(memberships__user__is_active=False),
                distinct=True,
            ),
        )
        .order_by("-created_at" if hasattr(Company, "created_at") else "name")
    )

    users_qs = User.objects.filter(is_superuser=False, is_staff=False)
    processes_qs = TestProcess.objects.all()
    invitations_qs = TestInvitation.objects.all()

    stats = {
        "companies": companies_qs.count(),
        "users": users_qs.count(),
        "pending_users": users_qs.filter(is_active=False).count(),
        "processes": processes_qs.count(),
        "sent": invitations_qs.filter(
            Q(status__in=["sent", "started", "completed", "expired"]) |
            Q(source="self_registered")
        ).count(),
        "completed": invitations_qs.filter(status="completed").count(),
    }

    latest_companies = list(companies_qs[:5])

    company_created_events = (
        ActivityEvent.objects
        .filter(
            company__in=latest_companies,
            verb=ActivityEvent.Verb.COMPANY_CREATED,
        )
        .select_related("actor", "company")
        .order_by("company_id", "created_at")
    )

    company_created_by = {}

    for event in company_created_events:
        if event.company_id not in company_created_by:
            company_created_by[event.company_id] = event

    admin_activity_verbs = [
        ActivityEvent.Verb.COMPANY_CREATED,
        ActivityEvent.Verb.COMPANY_UPDATED,
        ActivityEvent.Verb.COMPANY_DELETED,
        ActivityEvent.Verb.COMPANY_MEMBER_INVITED,
        ActivityEvent.Verb.COMPANY_MEMBER_ADDED,
        ActivityEvent.Verb.COMPANY_MEMBER_REMOVED,
        ActivityEvent.Verb.COMPANY_MEMBER_ROLE_UPDATED,
        ActivityEvent.Verb.COMPANY_INVITE_ACCEPTED,
        ActivityEvent.Verb.ORGUNIT_CREATED,
        ActivityEvent.Verb.ORGUNIT_UPDATED,
        ActivityEvent.Verb.ORGUNIT_MOVED,
        ActivityEvent.Verb.ORGUNIT_DELETED,
        ActivityEvent.Verb.USER_ACCESS_UPDATED,
        ActivityEvent.Verb.USER_LOGGED_IN,
    ]

    activity_events = (
        ActivityEvent.objects
        .filter(verb__in=admin_activity_verbs)
        .select_related("actor", "company", "process", "candidate", "invitation")
        .order_by("-created_at")[:10]
    )

    latest_processes = (
        TestProcess.objects
        .select_related("company", "org_unit", "created_by")
        .annotate(candidates_count=Count("invitations", distinct=True))
        .order_by("-created_at")[:5]
    )

    latest_user_invites = (
        UserInvite.objects
        .select_related("user", "company", "created_by")
        .order_by("-created_at")[:5]
    )

    return render(request, "admin/core/layouts/admin_dashboard.html", {
        "accounts": accounts,
        "error": error,
        "stats": stats,
        "latest_companies": latest_companies,
        "latest_processes": latest_processes,
        "activity_events": activity_events,
        "company_created_by": company_created_by,
        "latest_user_invites": latest_user_invites,
    })

@login_required
def admin_ai_prompts(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    definitions = list_ai_prompt_definitions()

    prompt_keys = [
        definition["key"]
        for definition in definitions
    ]

    saved_overrides = (
        AIPromptTemplate.objects
        .filter(key__in=prompt_keys)
        .select_related("updated_by")
    )

    override_map = {
        (
            prompt.key,
            prompt.language,
        ): prompt
        for prompt in saved_overrides
    }

    language_config = [
        {
            "code": "sv",
            "label": "Svenska",
            "flag": "🇸🇪",
        },
        {
            "code": "en",
            "label": "English",
            "flag": "🇬🇧",
        },
    ]

    prompt_groups = []

    for definition in definitions:
        language_versions = []

        for language in language_config:
            language_code = language["code"]

            override = override_map.get(
                (
                    definition["key"],
                    language_code,
                )
            )

            default_prompt = get_default_ai_prompt(
                key=definition["key"],
                language=language_code,
            )

            override_text = ""

            if override:
                override_text = (
                    override.prompt_text
                    or ""
                ).strip()

            uses_override = bool(
                override
                and override.is_active
                and override_text
            )

            effective_prompt = (
                override_text
                if uses_override
                else default_prompt
            )

            language_versions.append(
                {
                    "code": language_code,
                    "label": language["label"],
                    "flag": language["flag"],

                    "default_prompt": default_prompt,
                    "effective_prompt": effective_prompt,

                    "override": override,
                    "has_override": override is not None,
                    "uses_override": uses_override,

                    "source": (
                        "override"
                        if uses_override
                        else "default"
                    ),
                }
            )

        prompt_groups.append(
            {
                "key": definition["key"],
                "name": definition["name"],
                "category": definition["category"],
                "description": definition["description"],
                "languages": language_versions,
            }
        )

    return render(
        request,
        "admin/core/ai_prompts/prompt_list.html",
        {
            "prompt_groups": prompt_groups,
        },
    )

def _prune_ai_prompt_versions(prompt, keep=10):
    """
    Keep only the most recent AI prompt versions
    for this specific prompt and language.
    """

    keep_ids = list(
        prompt.versions
        .order_by("-saved_at", "-id")
        .values_list("id", flat=True)[:keep]
    )

    if not keep_ids:
        return

    prompt.versions.exclude(
        id__in=keep_ids
    ).delete()

@login_required
def admin_ai_prompt_edit(
    request,
    key,
    language,
):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    # ---------------------------------------------
    # Validate prompt
    # ---------------------------------------------

    try:
        definition = get_ai_prompt_definition(
            key
        )

    except KeyError:
        raise Http404("Unknown AI prompt.")

    # ---------------------------------------------
    # Validate language
    # ---------------------------------------------

    language_code = (
        str(language or "")
        .strip()
        .lower()
        .replace("_", "-")
        .split("-", 1)[0]
    )

    if language_code not in {
        "sv",
        "en",
    }:
        raise Http404("Unsupported AI prompt language.")

    language_config = {
        "sv": {
            "label": "Svenska",
            "flag": "🇸🇪",
        },
        "en": {
            "label": "English",
            "flag": "🇬🇧",
        },
    }

    language_info = language_config[
        language_code
    ]

    # ---------------------------------------------
    # Protected Talena default
    # ---------------------------------------------

    default_prompt = get_default_ai_prompt(
        key=key,
        language=language_code,
    )

    # ---------------------------------------------
    # Existing global override
    # ---------------------------------------------

    override = (
        AIPromptTemplate.objects
        .filter(
            key=key,
            language=language_code,
        )
        .select_related("updated_by")
        .first()
    )

    playground_result = None
    playground_error = None

    playground_available = (
        is_prompt_playground_available(key)
    )

    playground_sample_data = (
        get_playground_sample_data(key)
        if playground_available
        else None
    )

    playground_purpose = (
        playground_sample_data.get("purpose")
        if playground_sample_data
        else None
    )

    playground_context = (
        playground_sample_data.get("context", "")
        if playground_sample_data
        else ""
    )
    
    # ---------------------------------------------
    # POST
    # ---------------------------------------------

    if request.method == "POST":

        action = (
            request.POST.get("action")
            or "save"
        )

                # -----------------------------------------
        # Restore previous prompt version
        # -----------------------------------------

        if action == "restore":

            version_id = request.POST.get(
                "version_id"
            )

            target_version = (
                AIPromptTemplateVersion.objects
                .select_related(
                    "prompt",
                    "saved_by",
                )
                .filter(
                    id=version_id,
                    prompt__key=key,
                    prompt__language=language_code,
                )
                .first()
            )

            if not target_version:
                messages.error(
                    request,
                    "The selected prompt version could not be found.",
                )

                return redirect(
                    "core:admin_ai_prompt_edit",
                    key=key,
                    language=language_code,
                )

            with transaction.atomic():

                prompt_override = (
                    AIPromptTemplate.objects
                    .select_for_update()
                    .get(
                        pk=target_version.prompt_id
                    )
                )

                prompt_override.name = definition["name"]
                prompt_override.description = (
                    definition["description"]
                )
                prompt_override.prompt_text = (
                    target_version.prompt_text
                )
                prompt_override.is_active = (
                    target_version.is_active
                )
                prompt_override.updated_by = (
                    request.user
                )

                prompt_override.save(
                    update_fields=[
                        "name",
                        "description",
                        "prompt_text",
                        "is_active",
                        "updated_by",
                        "updated_at",
                    ]
                )

                # Restore creates a NEW history entry.
                # Existing later history remains untouched.
                AIPromptTemplateVersion.objects.create(
                    prompt=prompt_override,
                    prompt_text=prompt_override.prompt_text,
                    is_active=prompt_override.is_active,
                    action="restore",
                    saved_by=request.user,
                    restored_from=target_version,
                )

                _prune_ai_prompt_versions(
                    prompt_override,
                    keep=10,
                )

            messages.success(
                request,
                "The previous AI prompt version was restored.",
            )

            return redirect(
                "core:admin_ai_prompt_edit",
                key=key,
                language=language_code,
            )

        if playground_available and action in {
            "test",
            "save",
        }:

            posted_purpose = (
                request.POST.get(
                    "playground_purpose"
                )
                or ""
            ).strip()

            posted_context = request.POST.get(
                "playground_context"
            )

            if (
                playground_sample_data
                and not playground_sample_data.get(
                    "purpose_locked"
                )
                and posted_purpose
            ):
                playground_purpose = posted_purpose

            if posted_context is not None:
                playground_context = posted_context

            playground_sample_data = (
                get_playground_sample_data(
                    key,
                    purpose=playground_purpose,
                    context=playground_context,
                )
            )

            if playground_sample_data:
                playground_purpose = (
                    playground_sample_data[
                        "purpose"
                    ]
                )

                playground_context = (
                    playground_sample_data[
                        "context"
                    ]
                )

        # -----------------------------------------
        # Reset to Talena default
        # -----------------------------------------

        if action == "reset":

            if override:
                override.is_active = False
                override.updated_by = request.user

                override.save(
                    update_fields=[
                        "is_active",
                        "updated_by",
                        "updated_at",
                    ]
                )

                AIPromptTemplateVersion.objects.create(
                    prompt=override,
                    prompt_text=override.prompt_text,
                    is_active=False,
                    action="save",
                    saved_by=request.user,
                )

                _prune_ai_prompt_versions(
                    override,
                    keep=10,
                )

                messages.success(
                    request,
                    (
                        "The custom AI guidance was disabled. "
                        "Talena is now using the built-in default guidance."
                    ),
                )

            else:
                messages.info(
                    request,
                        "Talena is already using the built-in default guidance."
                )

            return redirect(
                "core:admin_ai_prompt_edit",
                key=key,
                language=language_code,
            )

        # -----------------------------------------
        # Save global override
        # -----------------------------------------

        prompt_text = (
            request.POST.get("prompt_text")
            or ""
        ).strip()


        # -----------------------------------------
        # Test unsaved prompt in playground
        # -----------------------------------------

        if action == "test":

            if not prompt_text:
                playground_error = (
                    "Add some AI guidance before testing."
                )

            else:
                try:
                    from apps.core.ai.prompt_playground import (
                        run_prompt_playground,
                    )

                    playground_result = run_prompt_playground(
                        prompt_key=key,
                        prompt_text=prompt_text,
                        language_code=language_code,
                        purpose=playground_purpose,
                        context=playground_context,
                    )

                except Exception as exc:
                    playground_error = str(exc)


        # -----------------------------------------
        # Save global override
        # -----------------------------------------

        elif not prompt_text:
            messages.error(
                request,
                "The global AI prompt cannot be empty.",
            )

        else:
            with transaction.atomic():

                override, created = (
                    AIPromptTemplate.objects.update_or_create(
                        key=key,
                        language=language_code,
                        defaults={
                            "name": definition["name"],
                            "description": definition["description"],
                            "prompt_text": prompt_text,
                            "is_active": True,
                            "updated_by": request.user,
                        },
                    )
                )
                

                AIPromptTemplateVersion.objects.create(
                    prompt=override,
                    prompt_text=override.prompt_text,
                    is_active=override.is_active,
                    action="save",
                    saved_by=request.user,
                )

                _prune_ai_prompt_versions(
                    override,
                    keep=10,
                )

            messages.success(
                request,
                (
                    "AI guidance saved. "
                    "Future generations for all customers "
                    "will use this override."
                ),
            )

            return redirect(
                "core:admin_ai_prompt_edit",
                key=key,
                language=language_code,
            )

    # ---------------------------------------------
    # Determine current state
    # ---------------------------------------------

    has_active_override = bool(
        override
        and override.is_active
        and (
            override.prompt_text
            or ""
        ).strip()
    )

    if has_active_override:
        editing_text = override.prompt_text.strip()

    else:
        editing_text = default_prompt

    # Keep submitted text if validation failed.
    if request.method == "POST":
        editing_text = (
            request.POST.get("prompt_text")
            or ""
        )

    effective_prompt = (
        override.prompt_text.strip()
        if has_active_override
        else default_prompt
    )

    full_prompt_source = ""
    system_prompt_preview = ""

    if key == "motivation_interpretation":
        from apps.core.ai.motivation_interpretation import (
            build_motivation_interpretation_prompt,
            get_motivation_interpretation_system_prompt,
        )

        try:
            full_prompt_source = inspect.getsource(
                build_motivation_interpretation_prompt
            )

        except (OSError, TypeError):
            full_prompt_source = (
                "The prompt source could not be loaded "
                "in this environment."
            )

        system_prompt_preview = (
            get_motivation_interpretation_system_prompt(
                language_code
            )
        )

            # ---------------------------------------------
    # Prompt version history
    # ---------------------------------------------

    prompt_history = []

    if override:

        recent_versions = (
            override.versions
            .select_related(
                "saved_by",
                "restored_from",
            )
            .order_by(
                "-saved_at",
                "-id",
            )[:5]
        )

        current_marked = False

        for version in recent_versions:

            is_current = False

            if (
                not current_marked
                and version.prompt_text
                    == override.prompt_text
                and version.is_active
                    == override.is_active
            ):
                is_current = True
                current_marked = True

            prompt_history.append(
                {
                    "version": version,
                    "is_current": is_current,
                }
            )

    return render(
        request,
        "admin/core/ai_prompts/prompt_edit.html",
        {
            "prompt_definition": definition,
            "key": key,
            "language_code": language_code,
            "language": language_info,
            "prompt_history": prompt_history,

            "default_prompt": default_prompt,
            "editing_text": editing_text,
            "effective_prompt": effective_prompt,

            "override": override,
            "has_active_override": has_active_override,
            "full_prompt_source": full_prompt_source,
            "system_prompt_preview": system_prompt_preview,
            "playground_result": playground_result,
            "playground_error": playground_error,
            "playground_available": playground_available,
            "playground_sample_data": playground_sample_data,
        },
    )


from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation

# tokens_to_q(...) antar jag att du redan har i samma fil
# och att den returnerar ett Q-objekt

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation

User = get_user_model()

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.processes.models import TestProcess, Candidate, TestInvitation

User = get_user_model()

@login_required
@require_GET
def global_search(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    tokens = [t for t in q.split() if t]
    limit_each = 5
    results = []
    admin = is_admin(request.user)

    # -----------------------------
    # ADMIN: Customers
    # -----------------------------
    if admin:
        users_qs = (
            User.objects
            .filter(tokens_to_q(tokens, ["email", "first_name", "last_name"]))
            .order_by("first_name", "last_name")[:limit_each]
        )
        for u in users_qs:
            display = (f"{u.first_name} {u.last_name}").strip() or u.email
            results.append({
                "type": "customer",
                "label": display,
                "url": reverse("accounts:admin_user_detail", kwargs={"pk": u.id}),
            })

    # -----------------------------
    # ADMIN: Companies
    # -----------------------------
    if admin:
        companies_qs = (
            Company.objects
            .filter(tokens_to_q(tokens, ["name", "org_number"]))
            .order_by("name")[:limit_each]
        )
        for co in companies_qs:
            results.append({
                "type": "company",
                "label": co.name,
                "url": reverse("accounts:company_detail", kwargs={"pk": co.id}),
            })

    # -----------------------------
    # ADMIN: OrgUnits
    # -----------------------------
    if admin:
        org_qs = (
            OrgUnit.objects
            .select_related("company", "parent")
            .filter(tokens_to_q(tokens, ["name", "unit_code", "company__name"]))
            .order_by("company__name", "name")[:limit_each]
        )
        for ou in org_qs:
            url = f"{reverse('accounts:company_detail', kwargs={'pk': ou.company_id})}?tab=accounts&org_unit={ou.id}"
            results.append({
                "type": "org_unit",
                "label": f"{ou.name} ({ou.unit_code}) – {ou.company.name}",
                "url": url,
            })

    # -----------------------------
    # PROCESSES (ADMIN = alla, CUSTOMER = created_by=user)
    # -----------------------------
    proc_qs = TestProcess.objects.filter(
        tokens_to_q(tokens, ["name", "project_name_snapshot", "project_code", "account_code", "job_title"])
    )
    if not admin:
        proc_qs = proc_qs.filter(created_by=request.user)

    proc_qs = proc_qs.order_by("-created_at")[:limit_each]

    for p in proc_qs:
        url = (
            reverse("accounts:admin_process_detail", kwargs={"pk": p.id})
            if admin
            else reverse("processes:process_detail", kwargs={"pk": p.id})
        )
        results.append({"type": "process", "label": p.name, "url": url})

    # -----------------------------
    # CANDIDATES (ADMIN = alla, CUSTOMER = candidates i user’s processer)
    # -----------------------------
    cand_qs = Candidate.objects.filter(
        tokens_to_q(tokens, ["first_name", "last_name", "email"])
    )

    if not admin:
        cand_qs = cand_qs.filter(invitations__process__created_by=request.user)

    cand_qs = cand_qs.distinct().order_by("first_name", "last_name")[:limit_each]

    for c in cand_qs:
        full_name = f"{c.first_name} {c.last_name}".strip() or c.email

        inv_qs = TestInvitation.objects.filter(candidate=c).select_related("process").order_by("-created_at")
        if not admin:
            inv_qs = inv_qs.filter(process__created_by=request.user)

        latest_inv = inv_qs.first()

        if latest_inv:
            p = latest_inv.process
            url = (
                reverse("accounts:admin_candidate_detail", kwargs={"process_pk": p.id, "candidate_pk": c.id})
                if admin
                else reverse("processes:process_candidate_detail", kwargs={"process_id": p.id, "candidate_id": c.id})
            )
        else:
            url = "#"

        results.append({"type": "candidate", "label": full_name, "url": url})

    # -----------------------------
    # Sort + limit
    # -----------------------------
    order = {"customer": 0, "company": 1, "org_unit": 2, "process": 3, "candidate": 4}
    results.sort(key=lambda r: order.get(r["type"], 99))
    results = results[:12]

    return JsonResponse({"results": results})

@login_required
@require_POST
def complete_migration_onboarding(request):
    """
    Mark migration onboarding as seen for the
    current user's company membership.
    """

    membership = (
        CompanyMember.objects
        .select_related("company")
        .filter(user=request.user)
        .first()
    )

    if membership:
        company = membership.company

        if (
            company.migration_onboarding_enabled
            and not membership.migration_onboarding_seen_at
        ):
            membership.migration_onboarding_seen_at = (
                timezone.now()
            )

            membership.save(
                update_fields=[
                    "migration_onboarding_seen_at"
                ]
            )

    next_url = (
        request.POST.get("next")
        or ""
    ).strip()

    if (
        next_url
        and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={
                request.get_host()
            },
            require_https=request.is_secure(),
        )
    ):
        return redirect(next_url)

    return redirect(
        "core:customer_dashboard"
    )
