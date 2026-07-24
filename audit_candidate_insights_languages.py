#!/usr/bin/env python3
"""
Audit saved Candidate Insights AI-language metadata for one invitation.

This script is read-only. It does not update the database.

Place it beside manage.py and run:

    python audit_candidate_insights_languages.py \
        --process-id 123 \
        --candidate-id 456
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


SECTIONS = [
    {
        "label": "AI overview",
        "result_field": "ai_purpose_fit",
        "status_field": "ai_purpose_fit_status",
        "metadata_keys": (
            "purpose_fit",
            "overview",
            "ai_purpose_fit",
        ),
    },
    {
        "label": "Response-style guidance",
        "result_field": "ai_response_style_guidance",
        "status_field": "ai_response_style_guidance_status",
        "metadata_keys": (
            "response_style_guidance",
        ),
    },
    {
        "label": "Personality interpretation",
        "result_field": "ai_personality_interpretation",
        "status_field": "ai_personality_interpretation_status",
        "metadata_keys": (
            "personality_interpretation",
        ),
    },
    {
        "label": "Personality questions",
        "result_field": "ai_personality_questions",
        "status_field": "ai_personality_questions_status",
        "metadata_keys": (
            "personality_questions",
        ),
    },
    {
        "label": "Motivation interpretation",
        "result_field": "ai_motivation_interpretation",
        "status_field": "ai_motivation_interpretation_status",
        "metadata_keys": (
            "motivation_interpretation",
        ),
    },
    {
        "label": "Motivation questions",
        "result_field": "ai_motivation_questions",
        "status_field": "ai_motivation_questions_status",
        "metadata_keys": (
            "motivation_questions",
        ),
    },
    {
        "label": "Cognitive interpretation",
        "result_field": "ai_cognitive_interpretation",
        "status_field": "ai_cognitive_interpretation_status",
        "metadata_keys": (
            "cognitive_interpretation",
        ),
    },
    {
        "label": "Cognitive questions",
        "result_field": "ai_cognitive_questions",
        "status_field": "ai_cognitive_questions_status",
        "metadata_keys": (
            "cognitive_questions",
        ),
    },
    {
        "label": "Pre-interview decision support",
        "result_field": "ai_pre_interview_decision_support",
        "status_field": "ai_pre_interview_decision_support_status",
        "metadata_keys": (
            "pre_interview_decision_support",
        ),
    },
    {
        "label": "Post-interview decision support",
        "result_field": "ai_post_interview_decision_support",
        "status_field": "ai_post_interview_decision_support_status",
        "metadata_keys": (
            "post_interview_decision_support",
        ),
    },
]


def normalise_language(value) -> str:
    value = str(value or "").strip().lower()

    if value.startswith("sv"):
        return "sv"

    if value.startswith("en"):
        return "en"

    return value


def find_metadata_language(
    metadata: dict,
    keys: tuple[str, ...],
) -> tuple[str, str]:
    for key in keys:
        value = metadata.get(key)

        if value:
            return key, normalise_language(value)

    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--process-id",
        type=int,
        required=True,
        help="Talena process ID.",
    )

    parser.add_argument(
        "--candidate-id",
        type=int,
        required=True,
        help="Talena candidate ID.",
    )

    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repository_root))

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings",
    )

    try:
        import django
    except ImportError as exc:
        raise RuntimeError(
            "Django could not be imported. Run this script "
            "inside the Talena virtual environment."
        ) from exc

    django.setup()

    from apps.processes.models import TestInvitation

    try:
        invitation = (
            TestInvitation.objects
            .select_related(
                "candidate",
                "process",
            )
            .get(
                process_id=args.process_id,
                candidate_id=args.candidate_id,
            )
        )
    except TestInvitation.DoesNotExist:
        print(
            "No TestInvitation was found for "
            f"process_id={args.process_id} and "
            f"candidate_id={args.candidate_id}."
        )
        return 2

    candidate_name = " ".join(
        part
        for part in (
            getattr(
                invitation.candidate,
                "first_name",
                "",
            ),
            getattr(
                invitation.candidate,
                "last_name",
                "",
            ),
        )
        if part
    ).strip()

    metadata = (
        getattr(
            invitation,
            "ai_content_languages",
            None,
        )
        or {}
    )

    print()
    print("=" * 88)
    print("Talena Candidate Insights language audit")
    print("=" * 88)
    print(f"Process:   {invitation.process_id} · {invitation.process}")
    print(
        f"Candidate: {invitation.candidate_id} · "
        f"{candidate_name or invitation.candidate}"
    )
    print(f"Invitation status: {invitation.status}")
    print()
    print("Saved ai_content_languages:")
    print(metadata or "(empty)")
    print()
    print("-" * 88)

    issues = []
    generated_count = 0

    for section in SECTIONS:
        result = (
            getattr(
                invitation,
                section["result_field"],
                None,
            )
            or {}
        )

        status = str(
            getattr(
                invitation,
                section["status_field"],
                "",
            )
            or "not_started"
        )

        has_result = isinstance(result, dict) and bool(result)
        result_language = (
            normalise_language(
                result.get("_language")
            )
            if has_result
            else ""
        )

        metadata_key, metadata_language = (
            find_metadata_language(
                metadata,
                section["metadata_keys"],
            )
        )

        if has_result:
            generated_count += 1

        result_display = (
            result_language
            or "missing"
            if has_result
            else "no result"
        )

        metadata_display = (
            f"{metadata_language} ({metadata_key})"
            if metadata_language
            else "missing"
        )

        print(section["label"])
        print(f"  status:          {status}")
        print(f"  result language: {result_display}")
        print(f"  metadata:        {metadata_display}")

        if has_result and not result_language:
            issues.append(
                f"{section['label']}: saved result has no _language."
            )

        if (
            has_result
            and metadata_language
            and result_language
            and metadata_language != result_language
        ):
            issues.append(
                f"{section['label']}: result language "
                f"{result_language!r} does not match metadata "
                f"{metadata_language!r}."
            )

        if (
            status == "completed"
            and not has_result
        ):
            issues.append(
                f"{section['label']}: status is completed "
                "but no saved result exists."
            )

        print("-" * 88)

    print()
    print(f"Generated sections found: {generated_count}")

    if issues:
        print()
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")

        print()
        print("AUDIT RESULT: REVIEW NEEDED")
        return 1

    print()
    print("AUDIT RESULT: OK")
    print(
        "Every saved result found by this audit contains "
        "consistent language information."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
