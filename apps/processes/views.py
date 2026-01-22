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
from django.db import transaction

from django.http import HttpResponse

import json
import uuid
import requests



@login_required
def process_list(request):
    # sen kan du filtrera per kund/tenant, men nu: bara per användare
    processes = TestProcess.objects.filter(created_by=request.user)
    return render(request, "customer/processes/process_list.html", {"processes": processes})


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
    # key = (account_code, project_code)
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    # 3) Bygg både:
    #   A) choices -> endast value + "fallback label" (label används inte i kort-UI men behövs för formfältet)
    #   B) template_cards -> allt UI vill visa
    choices = []
    template_cards = []

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()
            active = bool(p.get("active"))

            value = f"{acc}|{proj_code}"

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            # tests/languages kan vara listor (JSONField) eller text
            tests = getattr(meta, "tests", None)
            languages = getattr(meta, "languages", None)

            # gör om till listor för templaten (om du råkar ha strängar i DB)
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

            choices.append((value, title))  # label är irrelevant i card-UI, men måste finnas

            template_cards.append({
                "value": value,
                "title": title,                 # <-- intern_name om finns
                "subtitle": subtitle,           # <-- use_case (valfritt)
                "badges": badges,               # <-- tests
                "languages": langs,             # <-- languages
                "active": active,
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,         # om du vill visa i tooltip/debug
            })

    # (valfritt) sortera mallarna snyggt efter intern titel
    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    # 4) Form init (samma i GET/POST)
    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]  # "ACC|PROJ"
            acc, proj = value.split("|", 1)

            # Spara kopplingen till SOVA
            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj

            # Snapshot (valfritt men bra)
            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            # om du vill ha fallback:
            if not obj.project_name_snapshot:
                # hitta sova_name från template_cards
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            obj.created_by = request.user
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
    obj = get_object_or_404(TestProcess, pk=pk, created_by=request.user)

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
    })


@login_required
def process_delete(request, pk):
    obj = get_object_or_404(TestProcess, pk=pk, created_by=request.user)

    if request.method == "POST":
        obj.delete()
        return redirect("processes:process_list")

    # om någon råkar gå hit via GET
    return redirect("processes:process_list")

@login_required
def process_detail(request, pk):
    process = get_object_or_404(TestProcess, pk=pk, created_by=request.user)

    invitations = (
        process.invitations
        .select_related("candidate")
        .order_by("-created_at")
    )

    return render(request, "customer/processes/process_detail.html", {
        "process": process,
        "invitations": invitations,
    })


@login_required
def process_add_candidate(request, pk):
    process = get_object_or_404(TestProcess, pk=pk, created_by=request.user)

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
    process = get_object_or_404(TestProcess, pk=pk, created_by=request.user)
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
def process_candidate_detail(request, process_id, candidate_id):
    process = get_object_or_404(TestProcess, pk=process_id, created_by=request.user)

    # candidate_id i URL är kandidatens ID (Candidate.pk)
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

    return render(request, "customer/processes/process_candidate_detail.html", {
        "process": process,
        "invitation": invitation,
        "candidate": candidate,
        "dummy_profile": dummy_profile,
        "dummy_abilities": dummy_abilities,
    })




@login_required
def sova_order_assessment_smoke_test(request, pk, candidate_id):
    process = get_object_or_404(TestProcess, pk=pk, created_by=request.user)
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


def self_register(request, token):
    process = get_object_or_404(TestProcess, self_registration_token=token)

    if request.method == "POST":
        form = SelfRegisterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            email = form.cleaned_data["email"].strip().lower()

            # superenkel name-split (räcker för MVP)
            parts = name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

            with transaction.atomic():
                # 1) Candidate (global dedupe på email enligt din constraint)
                candidate, _ = Candidate.objects.get_or_create(
                    email=email,
                    defaults={"first_name": first_name or name, "last_name": last_name},
                )

                # 2) Invitation (dedupe per process+candidate enligt din constraint)
                invitation, created = TestInvitation.objects.get_or_create(
                    process=process,
                    candidate=candidate,
                    defaults={
                        "status": "created",
                        "source": "self_registered",
                        "invited_at": timezone.now(),
                    }
                )

                # Om den redan fanns, uppdatera source om du vill
                if not created and invitation.source != "self_registered":
                    invitation.source = "self_registered"
                    invitation.save(update_fields=["source"])

            return render(request, "customer/processes/self_register_success.html", {
                "process": process,
                "message": "Your test has started. Check your email.",
            })
    else:
        form = SelfRegisterForm()

    return render(request, "customer/processes/self_register_form.html", {"process": process, "form": form})