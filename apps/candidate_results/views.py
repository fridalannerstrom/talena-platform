from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.utils.auth import is_admin
from apps.processes.services.access import get_accessible_processes_for_user

from .models import CandidateResultAccess, CandidateResultSnapshot


def _session_key(access: CandidateResultAccess) -> str:
    return f"candidate_result_verified_{access.pk}_{access.token_digest}"


def _copy(locale: str) -> dict[str, str]:
    if locale == "sv":
        return {
            "verify_title": "Visa ditt resultat",
            "verify_intro": (
                "Ange den personliga verifieringskod du fick tillsammans "
                "med länken för att se ditt resultat."
            ),
            "code_label": "Verifieringskod",
            "code_placeholder": "Sex siffror",
            "verify_button": "Visa resultat",
            "invalid_code": "Koden kunde inte verifieras. Kontrollera den och försök igen.",
            "unavailable_title": "Resultatet är inte tillgängligt",
            "unavailable_body": (
                "Länken kan ha gått ut eller återkallats. Kontakta den som "
                "skickade assessmenten om du behöver hjälp."
            ),
            "result_label": "Ditt assessmentresultat",
            "candidate_label": "Kandidat",
            "project_label": "Process",
            "completed_label": "Slutförd",
            "included_label": "Detta ingår",
            "preview_label": "Förhandsvisning för behörig användare",
            "preview_body": "Detta är en intern förhandsvisning. Kandidaten behöver verifiera sin åtkomst i den publika vyn.",
            "discussion_title": "Ett underlag för reflektion",
            "discussion_body": (
                "Resultatet beskriver möjliga preferenser och tendenser "
                "utifrån dina svar. Det är inte en absolut sanning eller "
                "ett betyg, utan ett underlag för en vidare dialog."
            ),
        }
    return {
        "verify_title": "View your result",
        "verify_intro": (
            "Enter the personal verification code you received with the "
            "link to view your result."
        ),
        "code_label": "Verification code",
        "code_placeholder": "Six digits",
        "verify_button": "View result",
        "invalid_code": "The code could not be verified. Check it and try again.",
        "unavailable_title": "The result is not available",
        "unavailable_body": (
            "The link may have expired or been revoked. Contact the person "
            "who sent the assessment if you need help."
        ),
        "result_label": "Your assessment result",
        "candidate_label": "Candidate",
        "project_label": "Process",
        "completed_label": "Completed",
        "included_label": "Included",
        "preview_label": "Authorised preview",
        "preview_body": "This is an internal preview. Candidates must verify access in the public view.",
        "discussion_title": "A basis for reflection",
        "discussion_body": (
            "The result describes possible preferences and tendencies "
            "based on your responses. It is not an absolute truth or a "
            "grade, but a basis for further conversation."
        ),
    }


def _result_context(
    snapshot: CandidateResultSnapshot,
    *,
    preview: bool = False,
) -> dict:
    content = snapshot.content if isinstance(snapshot.content, dict) else {}
    introduction = content.get("introduction")
    if not isinstance(introduction, dict):
        introduction = {}

    sections = []
    for key in ("personality", "skills", "motivation"):
        section = content.get(key)
        if not isinstance(section, dict):
            continue

        body = (section.get("body") or "").strip()
        points = section.get("points") or []
        points = [
            str(point).strip()
            for point in points
            if str(point).strip()
        ]
        if body or points:
            sections.append(
                {
                    "key": key,
                    "title": section.get("title") or key.title(),
                    "body": body,
                    "points": points,
                }
            )

    invitation = snapshot.invitation
    completed_at = invitation.completed_at or snapshot.created_at
    locale = snapshot.locale if snapshot.locale in {"sv", "en"} else "sv"

    return {
        "copy": _copy(locale),
        "snapshot": snapshot,
        "introduction": introduction,
        "candidate": snapshot.candidate,
        "process": snapshot.process,
        "completed_at": completed_at,
        "sections": sections,
        "locale": locale,
        "preview": preview,
    }


def _get_access(token: str) -> CandidateResultAccess:
    digest = CandidateResultAccess.digest_token(token)
    return get_object_or_404(
        CandidateResultAccess.objects.select_related(
            "snapshot__candidate",
            "snapshot__process",
            "snapshot__invitation",
        ),
        token_digest=digest,
    )


def _render_unavailable(request, access: CandidateResultAccess):
    locale = access.locale if access.locale in {"sv", "en"} else "sv"
    return render(
        request,
        "candidate_results/unavailable.html",
        {"copy": _copy(locale)},
        status=410,
    )


@require_http_methods(["GET", "POST"])
def candidate_result(request, token: str):
    access = _get_access(token)
    now = timezone.now()

    if not access.is_active(now):
        return _render_unavailable(request, access)

    session_key = _session_key(access)
    verified = bool(request.session.get(session_key))
    error = ""

    if request.method == "POST":
        code = (request.POST.get("verification_code") or "").strip()
        verified = access.verify_code(code, now=now)
        if verified:
            request.session[session_key] = True
        else:
            error = _copy(access.locale).get("invalid_code", "Invalid code.")

    if not verified:
        return render(
            request,
            "candidate_results/verify.html",
            {
                "copy": _copy(access.locale),
                "error": error,
            },
        )

    return render(
        request,
        "candidate_results/result.html",
        _result_context(access.snapshot),
    )


@login_required
def candidate_result_preview(request, snapshot_id: int):
    snapshot = get_object_or_404(
        CandidateResultSnapshot.objects.select_related(
            "candidate",
            "process",
            "invitation",
        ),
        pk=snapshot_id,
    )

    if not is_admin(request.user):
        accessible_processes, _company = (
            get_accessible_processes_for_user(request.user)
        )
        if not accessible_processes.filter(pk=snapshot.process_id).exists():
            raise Http404

    return render(
        request,
        "candidate_results/result.html",
        _result_context(snapshot, preview=True),
    )
