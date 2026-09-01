from __future__ import annotations

from django.conf import settings
from django.db import models


class InterviewQuestionNote(models.Model):
    """Persistent interviewer notes attached to an exact generated question."""

    class Source(models.TextChoices):
        PERSONALITY = "personality", "Personality"
        MOTIVATION = "motivation", "Motivation"
        COGNITIVE = "cognitive", "Cognitive"

    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="interview_question_notes",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="interview_question_notes",
    )
    source = models.CharField(
        max_length=24,
        choices=Source.choices,
    )
    question_key = models.CharField(
        max_length=64,
    )
    question_text = models.TextField()
    note = models.TextField(blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_question_notes_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "processes"
        ordering = ["source", "created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "process",
                    "candidate",
                    "source",
                    "question_key",
                ],
                name="uniq_interview_question_note",
            ),
        ]
        indexes = [
            models.Index(
                fields=["process", "candidate", "source"],
                name="interview_note_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_source_display()}: {self.question_text[:60]}"
