"""Permission-checked access to uploaded historical assessment PDFs.

Historical files contain sensitive candidate information. Never give customer
views the storage backend's raw .url (which may be a shareable Azure SAS URL).
Authorize each download against the exact process, candidate and report.
"""

import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .access_control import process_view_access_required
from .models import HistoricalCandidateReport


@login_required
@require_GET
@process_view_access_required
def historical_candidate_report_download(
    request, process_id, candidate_id, report_id
):
    report = get_object_or_404(
        HistoricalCandidateReport.objects.select_related(
            "historical_candidate__process",
        ),
        pk=report_id,
        historical_candidate__process_id=process_id,
        historical_candidate__candidate_id=candidate_id,
        historical_candidate__process__is_historical=True,
    )

    if not report.file:
        raise Http404("Report file not available.")

    try:
        document = report.file.open("rb")
    except (OSError, ValueError):
        # Do not expose internal filesystem/blob URLs or storage error details.
        raise Http404("Report file not available.") from None

    filename = os.path.basename(
        report.original_filename or report.file.name or "report.pdf"
    )
    response = FileResponse(
        document,
        as_attachment=False,
        filename=filename,
        content_type="application/pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
