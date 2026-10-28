from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.utils.org_access import user_can_edit_process
from apps.core.utils.auth import is_admin
from apps.processes.models import TestInvitation
from .email import send_candidate_result_email
from apps.processes.services.access import get_accessible_processes_for_user

from .interpretation import ensure_candidate_result_snapshot_current
from .models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
    CandidateTestExperienceFeedback,
)


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
            "feedback_question": "Känner du igen dig i den här beskrivningen?",
            "feedback_recognise": "Jag känner igen mig",
            "feedback_partial": "Delvis",
            "feedback_not_recognise": "Jag känner inte igen mig",
            "feedback_comment_button": "Lämna en kommentar",
            "feedback_edit_comment": "Redigera kommentar",
            "feedback_your_comment": "Din kommentar:",
            "feedback_modal_title": "Din reflektion",
            "feedback_comment_label": "Kommentar (valfritt)",
            "feedback_comment_placeholder": "Är det något du vill bekräfta, nyansera eller kommentera?",
            "feedback_save": "Spara reflektion",
            "feedback_cancel": "Avbryt",
            "feedback_saved": "Din reflektion har sparats.",
            "feedback_saved_short": "Sparad",
            "experience_title": "Hur upplevde du testerna?",
            "experience_intro": "Berätta gärna hur du upplevde att göra testerna. Ditt svar och din kommentar blir synliga för kunden som bjöd in dig.",
            "experience_rating": "Din upplevelse",
            "experience_labels": [(1, "Inte alls bra"), (2, "Inte särskilt bra"), (3, "Helt okej"), (4, "Bra"), (5, "Mycket bra")],
            "experience_comment": "Vill du berätta mer? (valfritt)",
            "experience_save": "Skicka feedback",
            "experience_update": "Uppdatera feedback",
            "experience_saved": "Tack! Din feedback om testupplevelsen har sparats.",
            "feedback_area_unavailable": "Den här resultatdelen är inte tillgänglig.",
            "feedback_response_invalid": "Det här svaret är inte giltigt.",
            "feedback_comment_too_long": "Kommentaren får innehålla högst 2 000 tecken.",
            "experience_rating_invalid": "Välj ett giltigt betyg.",
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
        "feedback_question": "Do you recognise yourself in this description?",
        "feedback_recognise": "I recognise myself",
        "feedback_partial": "Partly",
        "feedback_not_recognise": "I do not recognise myself",
        "feedback_comment_button": "Add a comment",
        "feedback_edit_comment": "Edit comment",
        "feedback_your_comment": "Your comment:",
        "feedback_modal_title": "Your reflection",
        "feedback_comment_label": "Comment (optional)",
        "feedback_comment_placeholder": "Is there anything you would like to confirm, nuance or comment on?",
        "feedback_save": "Save reflection",
        "feedback_cancel": "Cancel",
        "feedback_saved": "Your reflection has been saved.",
        "feedback_saved_short": "Saved",
        "experience_title": "How was your test experience?",
        "experience_intro": "Tell us what it was like to take the tests. Your rating and comment will be visible to the customer who invited you.",
        "experience_rating": "Your experience",
        "experience_labels": [(1, "Not good at all"), (2, "Not very good"), (3, "Okay"), (4, "Good"), (5, "Very good")],
        "experience_comment": "Would you like to tell us more? (optional)",
        "experience_save": "Send feedback",
        "experience_update": "Update feedback",
        "experience_saved": "Thank you! Your test-experience feedback has been saved.",
        "feedback_area_unavailable": "This result section is not available.",
        "feedback_response_invalid": "This response is not valid.",
        "feedback_comment_too_long": "Your comment must be 2,000 characters or fewer.",
        "experience_rating_invalid": "Choose a valid rating.",
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

    feedback_by_area = {
        feedback.result_area: feedback
        for feedback in CandidateResultFeedback.objects.filter(snapshot=snapshot)
    }

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
        groups = []
        for group in section.get("groups") or []:
            if not isinstance(group, dict):
                continue
            items = []
            for item in group.get("items") or []:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                text = str(item.get("text") or "").strip()
                if label or text:
                    items.append({"label": label, "text": text})
            title = str(group.get("title") or "").strip()
            body = str(group.get("body") or "").strip()
            if title or body or items:
                groups.append({
                    "title": title,
                    "body": body,
                    "items": items,
                })

        if key == "personality" and groups:
            # Current personality content is displayed through the three areas;
            # fall back to the section body only for snapshots without groups.
            body = ""
            points = []

        if body or points or groups:
            sections.append(
                {
                    "key": key,
                    "title": section.get("title") or key.title(),
                    "body": body,
                    "points": points,
                    "groups": groups,
                    "feedback": feedback_by_area.get(key),
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
        "feedback_saved": False,
        "experience_feedback": CandidateTestExperienceFeedback.objects.filter(snapshot=snapshot).first(),
        "experience_saved": False,
    }



def _save_candidate_feedback(request, snapshot: CandidateResultSnapshot):
    result_area = (request.POST.get("result_area") or "").strip()
    response_value = (request.POST.get("response") or "").strip()
    comment = (request.POST.get("comment") or "").strip()

    available_areas = {
        section["key"]
        for section in _result_context(snapshot)["sections"]
    }
    valid_responses = {
        choice[0]
        for choice in CandidateResultFeedback.RESPONSE_CHOICES
    }
    locale = snapshot.locale if snapshot.locale in {"sv", "en"} else "sv"
    copy = _copy(locale)

    if result_area not in available_areas:
        return HttpResponseBadRequest(copy["feedback_area_unavailable"])
    if response_value not in valid_responses:
        return HttpResponseBadRequest(copy["feedback_response_invalid"])
    if len(comment) > 2000:
        return HttpResponseBadRequest(copy["feedback_comment_too_long"])

    CandidateResultFeedback.objects.update_or_create(
        snapshot=snapshot,
        result_area=result_area,
        defaults={
            "response": response_value,
            "comment": comment,
            "locale": locale,
        },
    )
    return None


def _save_test_experience(request, snapshot: CandidateResultSnapshot):
    rating = (request.POST.get("rating") or "").strip()
    comment = (request.POST.get("comment") or "").strip()
    locale = snapshot.locale if snapshot.locale in {"sv", "en"} else "sv"
    copy = _copy(locale)
    if rating not in {"1", "2", "3", "4", "5"}:
        return HttpResponseBadRequest(copy["experience_rating_invalid"])
    if len(comment) > 2000:
        return HttpResponseBadRequest(copy["feedback_comment_too_long"])

    CandidateTestExperienceFeedback.objects.update_or_create(
        snapshot=snapshot,
        defaults={"rating": int(rating), "comment": comment, "locale": locale},
    )
    return None


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
        {"copy": _copy(locale), "locale": locale},
        status=410,
    )


@require_http_methods(["GET", "POST"])
def candidate_result(request, token: str):
    access = _get_access(token)
    now = timezone.now()

    if not access.snapshot.process.candidate_results_enabled or not access.is_active(now):
        return _render_unavailable(request, access)

    locale = access.locale if access.locale in {"sv", "en"} else "sv"
    session_key = _session_key(access)
    verified = bool(request.session.get(session_key))
    error = ""

    # Feedback is submitted after the candidate has already verified the
    # result link. Do not try to verify an empty code again on that POST.
    if request.method == "POST" and request.POST.get("action") not in {"save_feedback", "save_experience"}:
        code = (request.POST.get("verification_code") or "").strip()
        verified = access.verify_code(code, now=now)
        if verified:
            request.session[session_key] = True
        else:
            error = _copy(locale).get("invalid_code", "Invalid code.")

    if not verified:
        return render(
            request,
            "candidate_results/verify.html",
            {
                "copy": _copy(locale),
                "locale": locale,
                "error": error,
            },
        )

    snapshot, _upgraded = ensure_candidate_result_snapshot_current(
        access.snapshot
    )

    if request.method == "POST" and request.POST.get("action") == "save_feedback":
        error_response = _save_candidate_feedback(request, snapshot)
        if error_response is not None:
            return error_response
        return redirect(f"{request.path}?feedback_saved=1")

    if request.method == "POST" and request.POST.get("action") == "save_experience":
        error_response = _save_test_experience(request, snapshot)
        if error_response is not None:
            return error_response
        return redirect(f"{request.path}?experience_saved=1#test-experience")

    context = _result_context(snapshot)
    context["feedback_saved"] = request.GET.get("feedback_saved") == "1"
    context["experience_saved"] = request.GET.get("experience_saved") == "1"
    return render(
        request,
        "candidate_results/result.html",
        context,
    )


@login_required
@xframe_options_sameorigin
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

    snapshot, _upgraded = ensure_candidate_result_snapshot_current(snapshot)

    return render(
        request,
        "candidate_results/result.html",
        _result_context(snapshot, preview=True),
    )


def _candidate_result_action_message(request, *, sv: str, en: str) -> str:
    language = str(getattr(request, "LANGUAGE_CODE", "sv") or "sv").lower()
    return sv if language.startswith("sv") else en


@login_required
@require_POST
def manage_candidate_result(request, invitation_id: int):
    invitation = get_object_or_404(
        TestInvitation.objects.select_related(
            "candidate",
            "process__company",
            "process__org_unit",
        ),
        pk=invitation_id,
    )
    process = invitation.process

    if not user_can_edit_process(request.user, process.company, process):
        return HttpResponseForbidden("You do not have permission to manage this result.")

    action = (request.POST.get("action") or "").strip()

    if action == "send":
        if not process.candidate_results_enabled:
            messages.error(
                request,
                _candidate_result_action_message(
                    request,
                    sv="Aktivera delning i processinställningarna innan resultatet skickas.",
                    en="Enable sharing in the process settings before sending the result.",
                ),
            )
        elif invitation.status != "completed":
            messages.error(
                request,
                _candidate_result_action_message(
                    request,
                    sv="Resultatet kan skickas när kandidatens tester är slutförda.",
                    en="The result can be sent once the candidate's assessments are complete.",
                ),
            )
        else:
            try:
                send_candidate_result_email(
                    invitation,
                    actor=request.user,
                    base_url=request.build_absolute_uri("/").rstrip("/"),
                    replace_code=True,
                )
                messages.success(
                    request,
                    _candidate_result_action_message(
                        request,
                        sv="Kandidatrapporten skickades med en ny verifieringskod.",
                        en="The Candidate Report was sent with a new verification code.",
                    ),
                )
            except Exception:
                messages.error(
                    request,
                    _candidate_result_action_message(
                        request,
                        sv="E-postmeddelandet kunde inte skickas. Kontrollera e-poststatusen och försök igen.",
                        en="The email could not be sent. Check the email status and try again.",
                    ),
                )
    elif action == "revoke":
        access = (
            CandidateResultAccess.objects
            .filter(snapshot__invitation=invitation)
            .first()
        )
        if access is None:
            messages.info(
                request,
                _candidate_result_action_message(
                    request,
                    sv="Det finns ingen kandidatåtkomst att återkalla.",
                    en="There is no candidate access to revoke.",
                ),
            )
        elif access.revoked_at:
            messages.info(
                request,
                _candidate_result_action_message(
                    request,
                    sv="Kandidatens åtkomst är redan återkallad.",
                    en="Candidate access has already been revoked.",
                ),
            )
        else:
            access.revoked_at = timezone.now()
            access.save(update_fields=["revoked_at"])
            messages.success(
                request,
                _candidate_result_action_message(
                    request,
                    sv="Kandidatens åtkomst har återkallats.",
                    en="Candidate access has been revoked.",
                ),
            )
    else:
        return HttpResponseBadRequest("Unknown candidate result action.")

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse(
            "processes:process_detail",
            kwargs={"pk": process.pk},
        )
    return HttpResponseRedirect(next_url)
