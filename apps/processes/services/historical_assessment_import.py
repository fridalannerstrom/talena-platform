import math
import os
from datetime import datetime

import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.processes.models import (
    Candidate,
    HistoricalProcessCandidate,
    HistoricalAssessmentImport,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
)


TEAM_STYLE_COLUMNS = [
    "Analyst",
    "Director",
    "Catalyst",
    "Energiser",
    "Connector",
    "Auditor",
    "Harmoniser",
    "Architect",
]


KNOWN_METADATA_COLUMNS = {
    "Full Name",
    "First Name",
    "Last Name",
    "Email",
    "Candidate ID",
    "Result ID",
    "Time Added",
    "Time Completed",
    "Language",
    "Status",
    "Labels",
    "ATS ID",
    "Total Time Spent",
    "Sova Score",
}


def detect_assessment_type(filename):
    name = filename.lower()

    if "personality" in name:
        return "personality"

    if "motivation" in name:
        return "motivation"

    if "verbal" in name:
        return "verbal"

    if "logical" in name:
        return "logical"

    if "numerical" in name:
        return "numerical"

    return "unknown"


def detect_scale(filename):
    name = filename.lower()

    if "sten" in name:
        return "sten"

    if "1-to-5" in name or "1_to_5" in name or "1 to 5" in name:
        return "one_to_five"

    if "percentile" in name:
        return "percentile"

    return "unknown"


def clean_value(value):
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    if pd.isna(value):
        return None

    return value


def clean_text(value):
    value = clean_value(value)

    if value is None:
        return ""

    return str(value).strip()


def clean_float(value):
    value = clean_value(value)

    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_datetime(value):
    value = clean_value(value)

    if not value:
        return None

    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value)
        return value

    if isinstance(value, (int, float)) and value > 1000:
        return excel_serial_to_datetime(value)

    try:
        parsed = pd.to_datetime(value)

        if pd.isna(parsed):
            return None

        parsed = parsed.to_pydatetime()

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)

        return parsed

    except Exception:
        return None


def split_name(full_name, first_name="", last_name=""):
    first_name = clean_text(first_name)
    last_name = clean_text(last_name)
    full_name = clean_text(full_name)

    if first_name or last_name:
        return first_name, last_name

    parts = full_name.split()

    if not parts:
        return "", ""

    if len(parts) == 1:
        return parts[0], ""

    return parts[0], " ".join(parts[1:])


def get_score_category(column_name, assessment_type):
    if assessment_type == "personality" and column_name in TEAM_STYLE_COLUMNS:
        return "team_style"

    if assessment_type == "personality":
        return "personality"

    if assessment_type == "motivation":
        return "motivation"

    if assessment_type in ["verbal", "logical", "numerical"]:
        return "ability"

    return "unknown"


def is_score_column(column_name, assessment_type):
    if not column_name:
        return False

    if column_name in KNOWN_METADATA_COLUMNS:
        return False

    # For ability files, keep columns that contain score/percentile or the test name itself
    if assessment_type in ["verbal", "logical", "numerical"]:
        lowered = column_name.lower()
        return (
            "percentile" in lowered
            or "score" in lowered
            or assessment_type in lowered
        )

    # For personality/motivation, most non-metadata numeric columns are scores
    return True

def find_header_row(file_obj, required_columns=None, max_rows=10):
    """
    SOVA exports sometimes have one or more empty rows before the actual header.
    This finds the row containing the real column names.
    """
    required_columns = required_columns or {
        "Email",
        "Candidate ID",
        "Result ID",
        "Full Name",
    }

    file_obj.seek(0)

    preview = pd.read_excel(
        file_obj,
        header=None,
        nrows=max_rows,
        engine="openpyxl",
    )

    for index, row in preview.iterrows():
        values = {
            str(value).strip()
            for value in row.tolist()
            if value is not None and not pd.isna(value)
        }

        if required_columns.intersection(values):
            return index

    return 0


def excel_serial_to_datetime(value):
    """
    Converts Excel serial date numbers to timezone-aware datetimes.
    Example: 45951.345 becomes an actual date/time.
    """
    try:
        parsed = pd.to_datetime(
            float(value),
            unit="D",
            origin="1899-12-30",
        )

        parsed = parsed.to_pydatetime()

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)

        return parsed

    except Exception:
        return None


def json_safe_value(value):
    """
    Makes values safe for JSONField.
    """
    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    try:
        if hasattr(value, "isoformat"):
            return value.isoformat()
    except Exception:
        pass

    return value


@transaction.atomic
def import_historical_assessment_file(process, uploaded_file, user=None):
    original_filename = uploaded_file.name
    assessment_type = detect_assessment_type(original_filename)
    scale = detect_scale(original_filename)

    import_record = HistoricalAssessmentImport.objects.create(
        process=process,
        uploaded_by=user,
        file=uploaded_file,
        original_filename=original_filename,
        assessment_type=assessment_type,
        scale=scale,
        status="processing",
    )

    uploaded_file.seek(0)
    header_row = find_header_row(uploaded_file)

    uploaded_file.seek(0)
    df = pd.read_excel(
        uploaded_file,
        header=header_row,
        engine="openpyxl",
    )

    df = df.where(pd.notnull(df), None)
    df = df.dropna(how="all")

    df = df.where(pd.notnull(df), None)

    # Remove completely empty rows
    df = df.dropna(how="all")

    print("IMPORT START:", original_filename)

    uploaded_file.seek(0)
    print("FINDING HEADER...")
    header_row = find_header_row(uploaded_file)
    print("HEADER ROW:", header_row)

    uploaded_file.seek(0)
    print("READING EXCEL...")
    df = pd.read_excel(
        uploaded_file,
        header=header_row,
        engine="openpyxl",
    )
    print("EXCEL READ DONE:", df.shape)

    df = df.where(pd.notnull(df), None)
    df = df.dropna(how="all")
    print("ROWS AFTER DROP EMPTY:", len(df))

    rows_processed = 0
    candidates_created = 0
    results_created = 0
    scores_created = 0

    for _, row in df.iterrows():
        raw_data = {
            str(column).strip(): json_safe_value(row[column])
            for column in df.columns
        }

        email = clean_text(raw_data.get("Email")).lower()

        if not email:
            continue

        first_name, last_name = split_name(
            raw_data.get("Full Name"),
            raw_data.get("First Name"),
            raw_data.get("Last Name"),
        )

        candidate, candidate_created = Candidate.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        if candidate_created:
            candidates_created += 1
        else:
            changed = False

            if first_name and not candidate.first_name:
                candidate.first_name = first_name
                changed = True

            if last_name and not candidate.last_name:
                candidate.last_name = last_name
                changed = True

            if changed:
                candidate.save(update_fields=["first_name", "last_name"])

        historical_candidate, _ = HistoricalProcessCandidate.objects.get_or_create(
            process=process,
            candidate=candidate,
            defaults={
                "status": clean_text(raw_data.get("Status")).lower() or "completed",
                "created_by": user,
            },
        )

        sova_result_id = clean_text(raw_data.get("Result ID"))

        result_lookup = {
            "process": process,
            "candidate": candidate,
            "assessment_type": assessment_type,
            "scale": scale,
            "sova_result_id": sova_result_id,
        }

        result_defaults = {
            "historical_candidate": historical_candidate,
            "import_file": import_record,
            "sova_candidate_id": clean_text(raw_data.get("Candidate ID")),
            "status": clean_text(raw_data.get("Status")),
            "language": clean_text(raw_data.get("Language")),
            "time_added": parse_datetime(raw_data.get("Time Added")),
            "time_completed": parse_datetime(raw_data.get("Time Completed")),
            "raw_data": raw_data,
        }

        result, result_created = HistoricalAssessmentResult.objects.update_or_create(
            **result_lookup,
            defaults=result_defaults,
        )

        if result_created:
            results_created += 1

        for column in df.columns:
            column_name = str(column).strip()

            if not is_score_column(column_name, assessment_type):
                continue

            value = clean_value(row[column])
            numeric_value = clean_float(value)

            if numeric_value is None:
                continue

            category = get_score_category(column_name, assessment_type)

            score_defaults = {
                "raw_value": str(value),
            }

            if "percentile" in column_name.lower():
                score_defaults["percentile"] = numeric_value
                score_defaults["score"] = None
            else:
                score_defaults["score"] = numeric_value
                score_defaults["percentile"] = None

            _, score_created = HistoricalAssessmentScore.objects.update_or_create(
                result=result,
                name=column_name,
                category=category,
                scale=scale,
                defaults=score_defaults,
            )

            if score_created:
                scores_created += 1

        rows_processed += 1

    import_record.status = "completed"
    import_record.rows_processed = rows_processed
    import_record.candidates_created = candidates_created
    import_record.results_created = results_created
    import_record.scores_created = scores_created
    import_record.save(update_fields=[
        "status",
        "rows_processed",
        "candidates_created",
        "results_created",
        "scores_created",
    ])

    return {
        "import_record": import_record,
        "rows_processed": rows_processed,
        "candidates_created": candidates_created,
        "results_created": results_created,
        "scores_created": scores_created,
        "assessment_type": assessment_type,
        "scale": scale,
        "filename": original_filename,
    }