"""Generate interview questions as soon as each Sova assessment is ready."""

import logging

from django.db import transaction

from apps.core.ai.cognitive_interpretation import extract_cognitive_results
from apps.core.ai.cognitive_questions import (
    apply_cognitive_questions_event,
    create_empty_cognitive_questions,
    save_cognitive_questions,
    stream_cognitive_questions,
)
from apps.core.ai.language import normalize_ai_language
from apps.core.ai.motivation_interpretation import extract_motivation_results
from apps.core.ai.motivation_questions import (
    apply_motivation_questions_event,
    create_empty_motivation_questions,
    save_motivation_questions,
    stream_motivation_questions,
)
from apps.core.ai.personality_questions import (
    apply_personality_questions_event,
    create_empty_personality_questions,
    extract_personality_question_traits,
    save_personality_questions,
    stream_personality_questions,
)
from apps.processes.models import AssessmentUsage, TestInvitation


logger = logging.getLogger(__name__)


def _claim_question_generation(invitation, *, result_field, status_field):
    """Claim one missing question set without racing a repeated Sova callback."""
    with transaction.atomic():
        owner = (
            TestInvitation.objects.select_for_update()
            .select_related("process", "candidate")
            .get(pk=invitation.pk)
        )
        saved = getattr(owner, result_field) or {}
        status = getattr(owner, status_field) or "not_started"
        if saved.get("questions") or status == "generating":
            return None
        setattr(owner, status_field, "generating")
        owner.save(update_fields=[status_field])
        return owner


def _generate_personality_questions(owner, language_code):
    role_context = getattr(owner.process, "role_context", None)
    if not role_context or not role_context.has_content():
        return

    completed = AssessmentUsage.objects.filter(
        invitation_id=owner.pk,
        assessment_type=AssessmentUsage.AssessmentType.PERSONALITY,
        status=AssessmentUsage.Status.COMPLETED,
    ).exists()
    if not completed:
        return

    results = extract_personality_question_traits(owner)
    if not results:
        return

    owner = _claim_question_generation(
        owner,
        result_field="ai_personality_questions",
        status_field="ai_personality_questions_status",
    )
    if owner is None:
        return

    result = create_empty_personality_questions(
        owner,
        language_code=language_code,
    )
    try:
        for event in stream_personality_questions(
            owner=owner,
            personality_results=results,
            language_code=language_code,
        ):
            result = apply_personality_questions_event(result, event)

        selected_traits = result.get("selected_traits") or []
        if not 1 <= len(selected_traits) <= 6:
            raise ValueError("The personality trait selection was invalid.")
        if not result.get("questions"):
            raise ValueError("No valid personality questions were generated.")

        save_personality_questions(
            owner=owner,
            result=result,
            language_code=language_code,
        )
    except Exception:
        owner.ai_personality_questions_status = "failed"
        owner.save(update_fields=["ai_personality_questions_status"])
        logger.exception(
            "Automatic personality interview-question generation failed for invitation %s",
            owner.pk,
        )


def _generate_motivation_questions(owner, language_code):
    completed = AssessmentUsage.objects.filter(
        invitation_id=owner.pk,
        assessment_type=AssessmentUsage.AssessmentType.MOTIVATION,
        status=AssessmentUsage.Status.COMPLETED,
    ).exists()
    if not completed:
        return

    results = extract_motivation_results(owner)
    if not results:
        return

    owner = _claim_question_generation(
        owner,
        result_field="ai_motivation_questions",
        status_field="ai_motivation_questions_status",
    )
    if owner is None:
        return

    result = create_empty_motivation_questions(
        owner,
        language_code=language_code,
    )
    try:
        for event in stream_motivation_questions(
            owner=owner,
            motivation_results=results,
            language_code=language_code,
        ):
            result = apply_motivation_questions_event(result, event)

        if not result.get("questions"):
            raise ValueError("No valid motivation questions were generated.")

        save_motivation_questions(
            owner=owner,
            result=result,
            language_code=language_code,
        )
    except Exception:
        owner.ai_motivation_questions_status = "failed"
        owner.save(update_fields=["ai_motivation_questions_status"])
        logger.exception(
            "Automatic motivation interview-question generation failed for invitation %s",
            owner.pk,
        )


def _generate_cognitive_questions(owner, language_code):
    completed_types = set(
        AssessmentUsage.objects.filter(
            invitation_id=owner.pk,
            assessment_type__in=(
                AssessmentUsage.AssessmentType.VERBAL,
                AssessmentUsage.AssessmentType.LOGICAL,
                AssessmentUsage.AssessmentType.NUMERICAL,
            ),
            status=AssessmentUsage.Status.COMPLETED,
        ).values_list("assessment_type", flat=True)
    )
    if not completed_types:
        return

    results = [
        item for item in extract_cognitive_results(owner)
        if item.get("key") in completed_types
    ]
    if not results:
        return

    owner = _claim_question_generation(
        owner,
        result_field="ai_cognitive_questions",
        status_field="ai_cognitive_questions_status",
    )
    if owner is None:
        return

    result = create_empty_cognitive_questions(
        owner,
        language_code=language_code,
    )
    try:
        for event in stream_cognitive_questions(
            owner=owner,
            cognitive_results=results,
            language_code=language_code,
        ):
            result = apply_cognitive_questions_event(result, event)

        if not result.get("questions"):
            raise ValueError("No valid skills questions were generated.")

        save_cognitive_questions(
            owner=owner,
            result=result,
            language_code=language_code,
        )
    except Exception:
        owner.ai_cognitive_questions_status = "failed"
        owner.save(update_fields=["ai_cognitive_questions_status"])
        logger.exception(
            "Automatic skills interview-question generation failed for invitation %s",
            owner.pk,
        )


def generate_ready_interview_questions(invitation):
    """Generate each ready question section independently after Sova updates results."""
    owner = (
        TestInvitation.objects.select_related("process", "candidate")
        .get(pk=invitation.pk)
    )
    language_code = normalize_ai_language(
        owner.process.candidate_language
    )

    for generate in (
        _generate_personality_questions,
        _generate_motivation_questions,
        _generate_cognitive_questions,
    ):
        try:
            generate(owner, language_code)
        except Exception:
            logger.exception(
                "Automatic interview-question generation failed for invitation %s",
                owner.pk,
            )
