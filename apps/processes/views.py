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
from django.http import JsonResponse

from urllib.parse import urlparse
from django.http import HttpResponseRedirect
from django.db.models import Count, Q

from django.http import HttpResponse
from apps.accounts.utils.permissions import filter_by_user_accounts, user_can_access_account
from django.http import HttpResponseForbidden

from apps.accounts.models import CompanyMember
from apps.processes.services.send_tests import send_assessments_and_emails

import json
import uuid
import requests

from django.conf import settings

def render_placeholders(text: str, ctx: dict) -> str:
    text = text or ""
    for key, val in ctx.items():
        text = text.replace("{" + key + "}", str(val or ""))
    return text


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

    processes = (
        TestProcess.objects
        .filter(company_id=company_id)
        .annotate(candidates_count=Count("invitations", distinct=True))
        .order_by("-created_at")
        .prefetch_related("labels")
    )

    return render(request, "customer/processes/process_list.html", {"processes": processes})


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

            choices.append((value, title))
            template_cards.append({
                "value": value,
                "title": title,
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
            obj.save()

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

            return redirect("processes:process_list")

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

            value = f"{acc}|{proj_code}"
            choices.append((value, title))

            template_cards.append({
                "value": value,
                "title": title,
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
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

    if not user_can_access_process(request.user, obj):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    obj.delete()
    messages.success(request, "Processen raderades.")
    return redirect("processes:process_list")


@login_required
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    if not user_can_access_process(request.user, process):
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

    # Counts by status
    status_counts = dict(
        invitations.values("status")
        .annotate(c=Count("id"))
        .values_list("status", "c")
    )

    sent_count = status_counts.get("sent", 0)
    started_count = status_counts.get("started", 0)
    completed_count = status_counts.get("completed", 0)
    expired_count = status_counts.get("expired", 0)

    # "Totalt skickade" = sent + started + completed (inte created)
    total_sent = sent_count + started_count + completed_count

    # "Ej påbörjade" (bland skickade) = sent
    not_started = sent_count

    context = {
        "process": process,
        "invitations": invitations,
        "meta": meta,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        "status_counts": status_counts,
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



from django.http import JsonResponse
from django.urls import reverse

@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

    # ✅ Säkerhetskontroll
    if not user_can_access_process(request.user, process):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

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

    if request.method == "POST":
        form = SelfRegisterForm(request.POST)
        if form.is_valid():
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
                        "invited_at": timezone.now(),
                    }
                )

                if not created and invitation.source != "self_registered":
                    invitation.source = "self_registered"
                    invitation.save(update_fields=["source"])

            # ✅ Om den redan är skickad/igång/klart och vi har en url sparad: redirecta direkt
            existing_url = None
            try:
                existing_url = (invitation.sova_payload or {}).get("url")
            except Exception:
                existing_url = None

            if invitation.status in ("sent", "started", "completed") and existing_url and _is_safe_external_url(existing_url):
                return HttpResponseRedirect(existing_url)

            # 3) Beställ test i SOVA direkt
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

                # Spara status + payload på invitation
                invitation.status = "sent"
                invitation.invited_at = timezone.now()
                invitation.sova_payload = resp
                invitation.request_id = request_id
                invitation.assessment_url = test_url

                update_fields = ["status", "invited_at", "sova_payload", "request_id", "assessment_url"]
                invitation.save(update_fields=update_fields)

                # 4) Skicka mejl som fallback (samma logik som i process_send_tests)
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

                print("\n===== SELF-REG EMAIL PREVIEW =====")
                print("TO:", candidate.email)
                print("SUBJECT:", subject)
                print("BODY:\n", body)
                print("=================================\n")

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
                    # vi låter redirect ändå funka, mejlet är bara fallback

                # 5) Redirect direkt till testet
                if test_url and _is_safe_external_url(test_url):
                    return HttpResponseRedirect(test_url)

                # Om SOVA inte gav url: visa success-sida
                return render(request, "customer/processes/self_register_success.html", {
                    "process": process,
                    "message": "Registrering klar. Vi skickar ett mejl när testlänken är redo.",
                })

            except Exception as e:
                print("❌ SELF REGISTER order_assessment failed:", str(e))
                # Visa vänlig sida istället för att krascha
                return render(request, "customer/processes/self_register_success.html", {
                    "process": process,
                    "message": "Registrering klar, men vi kunde inte starta testet direkt. Du får ett mejl så snart det är redo.",
                })

    else:
        form = SelfRegisterForm()

    return render(request, "customer/processes/self_register_form.html", {
        "process": process,
        "form": form
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

    invitation.delete()
    messages.success(request, "Candidate removed from process.")
    return redirect("processes:process_detail", pk=process.id)



@login_required
def process_send_tests(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)

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
    process = get_object_or_404(TestProcess, pk=process_id, created_by=request.user)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate_id=candidate_id
    )

    candidate = invitation.candidate

    dummy_profile = {
        "labels": ["Struktur", "Samarbete", "Driv", "Stresstålighet", "Analys"],
        "values": [7, 6, 8, 5, 7],
    }

    dummy_abilities = {
        "labels": ["Verbal", "Numerisk", "Logisk"],
        "values": [62, 54, 71],
    }

    ctx = {
        "process": process,
        "invitation": invitation,
        "inv": invitation,
        "candidate": candidate,
        "dummy_profile": dummy_profile,
        "dummy_abilities": dummy_abilities,
    }

    # ✅ Om anropet kommer via fetch/AJAX: returnera partial (sheet)
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if is_ajax:
        return render(request, "customer/processes/_candidate_detail_sheet.html", ctx)

    # ✅ Annars: returnera full page som vanligt
    return render(request, "customer/processes/process_candidate_detail.html", ctx)





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