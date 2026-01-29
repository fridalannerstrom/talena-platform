from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta
from .forms import TestProcessCreateForm, CandidateCreateForm
from .models import TestProcess, Candidate, TestInvitation, SelfRegistration
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
from django.db.models import Count

from django.http import HttpResponse
from apps.accounts.utils.permissions import filter_by_user_accounts, user_can_access_account
from django.http import HttpResponseForbidden

import json
import uuid
import requests

from django.conf import settings

def render_placeholders(text: str, ctx: dict) -> str:
    text = text or ""
    for key, val in ctx.items():
        text = text.replace("{" + key + "}", str(val or ""))
    return text


@login_required
@login_required
def process_list(request):
    # Hämta alla processer användaren har tillgång till (inte bara sina egna)
    all_processes = TestProcess.objects.all()
    processes = filter_by_user_accounts(all_processes, request.user, 'account')
    
    processes = (
        processes
        .annotate(candidates_count=Count("invitations", distinct=True))
        .order_by("-created_at") 
    )

    return render(request, "customer/processes/process_list.html", {
        "processes": processes,
    })

@login_required
def process_create(request):
    client = SovaClient()
    error = None

    # 1) Hämta accounts + projects från SOVA
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # 2) Hämta all metadata från DB i en dict för snabb lookup
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    # 3) Bygg choices + template_cards + en map för project_id
    choices = []
    template_cards = []
    project_id_map = {}  # key: "ACC|PROJ" -> value: project_id

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()
            active = bool(p.get("active"))

            value = f"{acc}|{proj_code}"

            # ✅ Spara project_id per value
            project_id_map[value] = p.get("id")

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            tests = getattr(meta, "tests", None)
            languages = getattr(meta, "languages", None)

            if isinstance(tests, str) and tests.strip():
                badges = [t.strip() for t in tests.split(",") if t.strip()]
            elif isinstance(tests, list):
                badges = tests
            else:
                badges = []

            if isinstance(languages, str) and languages.strip():
                langs = [l.strip() for l in languages.split(",") if l.strip()]
            elif isinstance(languages, list):
                langs = languages
            else:
                langs = []

            subtitle = getattr(meta, "use_case", "") or ""

            choices.append((value, title))

            template_cards.append({
                "value": value,
                "title": title,
                "subtitle": subtitle,
                "badges": badges,
                "languages": langs,
                "active": active,
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": p.get("id"),  # (valfritt, om du vill visa/debugga i UI)
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # 4) Form init (GET/POST)
    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]  # "ACC|PROJ"
            acc, proj = value.split("|", 1)

            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj

            # ✅ Spara project_id på processen (kräver fält i modellen)
            obj.sova_project_id = project_id_map.get(value)

            print("✅ SOVA project_id for new process:", obj.sova_project_id)

            # Snapshot
            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            if not obj.project_name_snapshot:
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            obj.created_by = request.user

            # ✅ Sätt account från användarens account
            from apps.accounts.utils.permissions import get_user_account
            user_account = get_user_account(request.user)
            if user_account:
                obj.account = user_account

            obj.save()
            return redirect("processes:process_list")
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


@login_required
def process_update(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)
    
    # Säkerhetskontroll: har användaren tillgång till detta account?
    if not user_can_access_account(request.user, obj.account):
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

    # 2) Hämta meta för intern_name (valfritt men nice)
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    # 3) Bygg choices med SAMMA value-format som i create: "ACC|PROJ"
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

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST, instance=obj)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            updated = form.save(commit=False)

            value = form.cleaned_data["sova_template"]  # "ACC|PROJ"
            acc, proj = value.split("|", 1)

            if locked and ((acc.strip() != old_acc) or (proj.strip() != old_proj)):
                messages.error(
                    request,
                    "Du kan inte ändra testpaket efter att tester har skickats i processen."
                )
                return redirect("processes:process_update", pk=obj.pk)

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
            return redirect("processes:process_list") 

    else:
        form = TestProcessCreateForm(instance=obj)
        form.fields["sova_template"].choices = choices

        # Förifyll med samma format som choices
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
@login_required
def process_delete(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk)
    
    # Säkerhetskontroll
    if not user_can_access_account(request.user, obj.account):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    if request.method == "POST":
        obj.delete()
        return redirect("processes:process_list")

    # om någon råkar gå hit via GET
    return redirect("processes:process_list")


@login_required
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    
    # Säkerhetskontroll
    if not user_can_access_account(request.user, process.account):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    # Hämta metadata för testpaketet som processen använder
    meta = ProjectMeta.objects.filter(
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    invitations = (
        process.invitations
        .select_related("candidate")
        .order_by("-created_at")
    )

    return render(
        request,
        "customer/processes/process_detail.html",
        {
            "process": process,
            "invitations": invitations,
            "meta": meta,
            "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        }
    )


@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    
    # Säkerhetskontroll
    if not user_can_access_account(request.user, process.account):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    if request.method == "POST":
        form = CandidateCreateForm(request.POST)
        if form.is_valid():
            # 1) skapa eller hämta kandidat på email (så man slipper dubletter)
            email = form.cleaned_data["email"]
            candidate, created = Candidate.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                }
            )

            # 2) skapa inbjudan i processen (kopplingen)
            invitation, inv_created = TestInvitation.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )

            if inv_created:
                messages.success(request, f"{candidate.email} added to process.")
            else:
                messages.info(request, f"{candidate.email} is already in this process.")

            # 3) (senare) här kan du trigga SOVA-invite direkt om du vill
            # invitation.mark_sent(...)
            # messages.success(request, "Invite sent via SOVA.")

            return redirect("processes:process_detail", pk=process.pk)
    else:
        form = CandidateCreateForm()

    return render(request, "customer/processes/process_add_candidate.html", {
        "process": process,
        "form": form,
    })

@login_required
def invite_candidate(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk)

    # Säkerhetskontroll
    if not user_can_access_account(request.user, process.account):
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
    if not user_can_access_account(request.user, process.account):
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
            name = form.cleaned_data["name"].strip()
            email = form.cleaned_data["email"].strip().lower()

            parts = name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

            client = SovaClient()

            with transaction.atomic():
                # 1) Candidate (dedupe on email)
                candidate, _ = Candidate.objects.get_or_create(
                    email=email,
                    defaults={"first_name": first_name or name, "last_name": last_name},
                )

                # 2) Invitation (dedupe per process+candidate)
                invitation, created = TestInvitation.objects.get_or_create(
                    process=process,
                    candidate=candidate,
                    defaults={
                        "status": "created",
                        "source": "self_registered",
                        # Tips: sätt INTE invited_at här om du vill ha den som "sent timestamp".
                        # Men jag låter din struktur vara och sätter sent längre ner.
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

    return render(request, "customer/processes/self_register_form.html", {"process": process, "form": form})



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

    # Säkerhetskontroll
    if not user_can_access_account(request.user, process.account):
        return HttpResponseForbidden("Du har inte tillgång till denna process.")

    # Endast POST
    if request.method != "POST":
        return redirect("processes:process_detail", pk=process.pk)

    invitation_ids = request.POST.getlist("invitation_ids")

    print("✅ HIT process_send_tests")
    print("process:", process.id)
    print("invitation_ids:", invitation_ids)

    if not invitation_ids:
        messages.warning(request, "Välj minst en kandidat.")
        return redirect("processes:process_detail", pk=process.pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process, id__in=invitation_ids)
        .select_related("candidate")
    )

    print("invitations found:", invitations.count())

    client = SovaClient()
    sent_count = 0
    skipped_count = 0

    # ✅ NEW: hitta sova_project_id EN gång, innan loopen
    accounts = client.get_accounts_with_projects()
    sova_project_id = None
    for a in accounts:
        if (a.get("code") or "").strip() == (process.account_code or "").strip():
            for p in (a.get("projects") or []):
                if (p.get("code") or "").strip() == (process.project_code or "").strip():
                    sova_project_id = p.get("id")
                    break
            break
    print("✅ SOVA project_id:", sova_project_id)

    for inv in invitations:
        candidate = inv.candidate

        # hoppa över om redan skickad/igång/klart
        if inv.status in ("sent", "started", "completed"):
            skipped_count += 1
            print(f"↪️ SKIP {candidate.email} (status={inv.status})")
            continue

        request_id = f"talena-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

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
                "talena_user_id": str(request.user.id),
                "talena_request_id": request_id,  # ✅ NEW (bra för spårbarhet)
            },
        }

        try:
            resp = client.order_assessment(process.project_code, payload)
            test_url = resp.get("url")

            # Välj språk (just nu hårdkodat sv, sen kan du koppla till candidate/process)
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

            # fallback om ingen mall finns (bra för MVP)
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

            # Logga i terminal (så du ser exakt vad som skulle skickas)
            print("\n===== EMAIL PREVIEW =====")
            print("TO:", candidate.email)
            print("SUBJECT:", subject)
            print("BODY:\n", body)
            print("=========================\n")

            # Skapa EmailLog med snapshot (så du kan visa historik i UI senare)
            email_log = EmailLog.objects.create(
                invitation=inv,
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
                raise

            if not test_url:
                # Viktigt: annars känns det som “inget händer”
                messages.error(request, f"SOVA returnerade ingen url för {candidate.email}.")
                print("❌ NO URL from SOVA:", resp)
                continue

            print(f"✅ [SOVA URL] {candidate.email} => {test_url}")

            # ✅ NEW: en enda save, men vi behåller ALLT du sparar
            inv.status = "sent"
            inv.invited_at = timezone.now()
            inv.sova_payload = resp
            inv.request_id = request_id
            inv.assessment_url = test_url 

            if sova_project_id is not None:
                inv.sova_project_id = sova_project_id

            update_fields = [
                "status",
                "invited_at",
                "sova_payload",
                "request_id",
                "assessment_url",
            ]
            if sova_project_id is not None:
                update_fields.append("sova_project_id")

            inv.save(update_fields=update_fields)

            sent_count += 1

        except Exception as e:
            print(f"❌ ERROR sending to {candidate.email}: {e}")
            messages.error(request, f"Kunde inte skicka till {candidate.email}: {e}")

    if sent_count:
        messages.success(request, f"Skickade test till {sent_count} kandidat(er).")

    if sent_count == 0:
        # Om allt blev skip eller fel: ge feedback ändå
        if skipped_count:
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
    if not user_can_access_account(request.user, process.account):
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