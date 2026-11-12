from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from openpyxl import Workbook, load_workbook

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event
from apps.processes.models import Candidate, TestInvitation, TestProcess
from .access_control import process_edit_access_required


MAX_IMPORT_SIZE = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 500
IMPORT_HEADERS = {
    "first name": "first_name",
    "firstname": "first_name",
    "last name": "last_name",
    "lastname": "last_name",
    "email": "email",
    "email address": "email",
}


def _error(row, message):
    return {"row": row, "message": message}


def _parse_candidate_sheet(upload):
    if upload.size > MAX_IMPORT_SIZE:
        return [], [_("The Excel file must be 5 MB or smaller.")]

    try:
        workbook = load_workbook(upload, read_only=True, data_only=True)
    except Exception:
        return [], [_("This file could not be read. Upload a valid .xlsx file.")]

    try:
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        header = next(iterator, None)
        if not header:
            return [], [_("The Excel file is empty.")]

        columns = {}
        for index, value in enumerate(header):
            key = " ".join(str(value or "").strip().lower().split())
            field = IMPORT_HEADERS.get(key)
            if field and field not in columns:
                columns[field] = index

        required = {"first_name", "last_name", "email"}
        if not required.issubset(columns):
            return [], [_("Required columns: First name, Last name and Email.")]

        rows = []
        for row_number, values in enumerate(iterator, start=2):
            values = list(values or ())
            first_name = str(values[columns["first_name"]] or "").strip() if columns["first_name"] < len(values) else ""
            last_name = str(values[columns["last_name"]] or "").strip() if columns["last_name"] < len(values) else ""
            email = str(values[columns["email"]] or "").strip() if columns["email"] < len(values) else ""
            if not (first_name or last_name or email):
                continue

            errors = []
            if not first_name:
                errors.append(_("First name is required."))
            elif len(first_name) > 80:
                errors.append(_("First name must be 80 characters or fewer."))
            if not last_name:
                errors.append(_("Last name is required."))
            elif len(last_name) > 80:
                errors.append(_("Last name must be 80 characters or fewer."))
            if not email:
                errors.append(_("Email is required."))
            else:
                try:
                    validate_email(email)
                except Exception:
                    errors.append(_("Enter a valid email address."))
                if len(email) > 254:
                    errors.append(_("Email must be 254 characters or fewer."))

            if len(rows) >= MAX_IMPORT_ROWS:
                return [], [_("A maximum of 500 candidates can be imported at once.")]
            rows.append({
                "row": row_number,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "errors": errors,
            })
        return rows, []
    finally:
        workbook.close()


@login_required
@process_edit_access_required
def candidate_import_template(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    if process.is_historical:
        return HttpResponse(_("Historical projects are read-only."), status=403)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Candidates"
    sheet.append(["First name", "Last name", "Email"])
    sheet.append(["Alex", "Taylor", "alex.taylor@example.com"])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:C2"
    sheet.column_dimensions["A"].width = 22
    sheet.column_dimensions["B"].width = 22
    sheet.column_dimensions["C"].width = 34

    instructions = workbook.create_sheet("Instructions")
    instructions.append(["How to prepare your candidate list"])
    instructions.append(["Enter one candidate per row on the Candidates sheet."])
    instructions.append(["Keep the column names First name, Last name and Email."])
    instructions.append(["All three fields are required. Email must be a valid email address."])
    instructions.append(["Remove the example row before uploading your file."])
    instructions.append(["Save and upload the file as .xlsx."])
    instructions.column_dimensions["A"].width = 90

    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="talena-candidates-template.xlsx"'
    return response


@login_required
@process_edit_access_required
def process_add_candidates(request, pk):
    process = get_object_or_404(TestProcess, pk=pk)
    if process.is_historical:
        return HttpResponse(_("Historical projects are read-only."), status=403)

    if request.method == "POST" and request.POST.get("action") == "preview_excel":
        upload = request.FILES.get("candidate_file")
        if not upload:
            return JsonResponse({"ok": False, "errors": [_("Choose an Excel file first.")]}, status=400)
        rows, errors = _parse_candidate_sheet(upload)
        if errors:
            return JsonResponse({"ok": False, "errors": errors}, status=400)

        seen_emails = set()
        for row in rows:
            email = row["email"].strip().lower()
            if email:
                if email in seen_emails:
                    row["errors"].append(_("This email appears more than once in the file."))
                seen_emails.add(email)
                existing = TestInvitation.objects.filter(
                    process=process, candidate__email__iexact=email
                ).first()
                if existing:
                    row["errors"].append(
                        _("This candidate was previously removed from the project.")
                        if existing.removed_from_process_at
                        else _("This candidate is already in the project.")
                    )
            if len(row["first_name"]) > 80:
                row["errors"].append(_("First name must be 80 characters or fewer."))
            if len(row["last_name"]) > 80:
                row["errors"].append(_("Last name must be 80 characters or fewer."))
            if len(row["email"]) > 254:
                row["errors"].append(_("Email must be 254 characters or fewer."))
        return JsonResponse({"ok": True, "rows": rows})

    if request.method == "POST" and request.POST.get("action") == "add_candidates":
        names = request.POST.getlist("first_name[]")
        surnames = request.POST.getlist("last_name[]")
        emails = request.POST.getlist("email[]")
        count = max(len(names), len(surnames), len(emails))
        if count > MAX_IMPORT_ROWS:
            return JsonResponse({
                "ok": False,
                "errors": [_("A maximum of 500 candidates can be added at once.")],
            }, status=400)
        seen = set()
        errors = []
        added_rows = []

        for index in range(count):
            first_name = names[index].strip() if index < len(names) else ""
            last_name = surnames[index].strip() if index < len(surnames) else ""
            email = emails[index].strip().lower() if index < len(emails) else ""
            row_number = index + 1
            if not (first_name or last_name or email):
                continue

            row_errors = []
            if not first_name:
                row_errors.append(_("First name is required."))
            elif len(first_name) > 80:
                row_errors.append(_("First name must be 80 characters or fewer."))
            if not last_name:
                row_errors.append(_("Last name is required."))
            elif len(last_name) > 80:
                row_errors.append(_("Last name must be 80 characters or fewer."))
            if not email:
                row_errors.append(_("Email is required."))
            else:
                try:
                    validate_email(email)
                except Exception:
                    row_errors.append(_("Enter a valid email address."))
                if len(email) > 254:
                    row_errors.append(_("Email must be 254 characters or fewer."))

            if email and email in seen:
                row_errors.append(_("This email appears more than once in the form."))
            elif email:
                seen.add(email)

            if not row_errors:
                existing = TestInvitation.objects.filter(
                    process=process, candidate__email__iexact=email
                ).first()
                if existing:
                    if existing.removed_from_process_at:
                        row_errors.append(_("This candidate was previously removed from the project."))
                    else:
                        row_errors.append(_("This candidate is already in the project."))

            if row_errors:
                errors.append(_error(row_number, " ".join(str(item) for item in row_errors)))
                continue

            candidate, _created = Candidate.objects.get_or_create(
                email=email,
                defaults={"first_name": first_name, "last_name": last_name},
            )
            invitation, created = TestInvitation.objects.get_or_create(
                process=process,
                candidate=candidate,
                defaults={"source": "invited", "status": "created"},
            )
            if not created:
                errors.append(_error(row_number, _("This candidate is already in the project.")))
                continue

            log_event(
                company=process.company,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
                actor=request.user,
                process=process,
                candidate=candidate,
                invitation=invitation,
                meta={"source": "invited", "batch_add": True},
            )
            added_rows.append(row_number)

        return JsonResponse({
            "ok": True,
            "added_count": len(added_rows),
            "added_rows": added_rows,
            "errors": errors,
            "redirect_url": reverse("processes:process_detail", kwargs={"pk": process.pk}),
        })

    return render(request, "customer/processes/_add_candidates_form.html", {
        "process": process,
        "template_url": reverse("processes:candidate_import_template", kwargs={"pk": process.pk}),
        "is_swedish": (request.LANGUAGE_CODE or "").startswith("sv"),
    })
