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


class ManagerReportTextEdit(models.Model):
    """A human-edited narrative block in one candidate manager report."""

    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="manager_report_text_edits",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="manager_report_text_edits",
    )
    block_key = models.CharField(max_length=100)
    language_code = models.CharField(max_length=2)
    text = models.TextField(blank=True, default="", max_length=30000)
    version = models.PositiveIntegerField(default=1)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manager_report_text_edits_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "processes"
        ordering = ["block_key", "language_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["process", "candidate", "block_key", "language_code"],
                name="uniq_manager_report_text_edit",
            ),
        ]
        indexes = [
            models.Index(
                fields=["process", "candidate", "language_code"],
                name="mgr_rpt_edit_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"Manager report edit · {self.block_key} · v{self.version}"


class ManagerReportTextEditEvent(models.Model):
    """Metadata-only audit event for a manager-report text edit."""

    class Action(models.TextChoices):
        SAVED = "saved", "Text saved"
        RESTORED_AI = "restored_ai", "AI text restored"

    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="manager_report_text_edit_events",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="manager_report_text_edit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manager_report_text_edit_events",
    )
    block_key = models.CharField(max_length=100)
    language_code = models.CharField(max_length=2)
    action = models.CharField(max_length=24, choices=Action.choices)
    version = models.PositiveIntegerField()
    source_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "processes"
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["process", "candidate", "-created_at"],
                name="mgr_rpt_edit_event_idx",
            ),
        ]

    def __str__(self):
        return f"Manager report {self.action} · {self.block_key} · v{self.version}"

