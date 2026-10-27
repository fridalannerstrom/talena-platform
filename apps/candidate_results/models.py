from datetime import timedelta

import hashlib
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CandidateResultSnapshot(models.Model):
    """
    Immutable current candidate-facing result content for one invitation.

    The snapshot stores presentation-ready content instead of reading current
    assessment or AI fields at request time. Older AI snapshots are archived
    in ``legacy_content`` when the candidate report is upgraded to static text.
    """

    invitation = models.OneToOneField(
        "processes.TestInvitation",
        on_delete=models.CASCADE,
        related_name="candidate_result_snapshot",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="candidate_result_snapshots",
    )
    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="candidate_result_snapshots",
    )

    locale = models.CharField(max_length=10, default="sv")
    content = models.JSONField(
        default=dict,
        help_text="Frozen candidate-facing content.",
    )
    content_version = models.CharField(
        max_length=32,
        default="candidate-static-v1",
        help_text="Version of the approved candidate-facing content library.",
    )
    legacy_content = models.JSONField(
        default=dict,
        blank=True,
        help_text="Archived candidate-facing content from a replaced legacy snapshot.",
    )
    prompt_versions = models.JSONField(
        default=dict,
        help_text="Legacy prompt metadata; empty for static candidate reports.",
    )
    legacy_prompt_versions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Archived prompt metadata associated with legacy candidate content.",
    )
    source_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Optional fingerprint of the assessment evidence used.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["process", "candidate"],
                name="candidate_r_process_5c0b8b_idx",
            ),
        ]

    def __str__(self):
        return f"Candidate result snapshot #{self.pk}"

    def clean(self):
        if not self.invitation_id:
            return

        if (
            self.candidate_id
            and self.invitation.candidate_id != self.candidate_id
        ):
            raise ValidationError(
                "Snapshot candidate must match the invitation candidate."
            )

        if (
            self.process_id
            and self.invitation.process_id != self.process_id
        ):
            raise ValidationError(
                "Snapshot process must match the invitation process."
            )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "Candidate result snapshots are immutable."
            )

        self.full_clean()
        return super().save(*args, **kwargs)


class CandidateResultAccess(models.Model):
    """
    Secure, revocable access credentials for a result snapshot.

    The raw URL token and verification code are only returned at creation
    time by the service layer. Only digests/hashes are persisted.
    """

    snapshot = models.OneToOneField(
        CandidateResultSnapshot,
        on_delete=models.CASCADE,
        related_name="access",
    )
    token_digest = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    verification_code_hash = models.CharField(max_length=128)

    locale = models.CharField(max_length=10, default="sv")
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    verification_failed_attempts = models.PositiveIntegerField(default=0)
    last_verification_failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["expires_at"],
                name="candidate_r_expires_4d17a0_idx",
            ),
            models.Index(
                fields=["revoked_at"],
                name="candidate_r_revoked_5f25ea_idx",
            ),
        ]

    def __str__(self):
        return f"Candidate result access #{self.pk}"

    @staticmethod
    def digest_token(raw_token: str) -> str:
        return hashlib.sha256(
            str(raw_token).encode("utf-8")
        ).hexdigest()

    def matches_token(self, raw_token: str) -> bool:
        return secrets.compare_digest(
            self.token_digest,
            self.digest_token(raw_token),
        )

    def is_expired(self, now=None) -> bool:
        now = now or timezone.now()
        return bool(self.expires_at and self.expires_at <= now)

    def is_active(self, now=None) -> bool:
        now = now or timezone.now()
        return not self.revoked_at and not self.is_expired(now)

    def is_rate_limited(self, now=None) -> bool:
        now = now or timezone.now()
        return bool(self.locked_until and self.locked_until > now)

    def verify_code(self, raw_code: str, now=None) -> bool:
        """
        Verify a code while enforcing the access lifecycle.

        The public endpoint will call this method after resolving the URL
        token. The five-attempt/15-minute policy is intentionally kept here
        so every future entry point uses the same rule.
        """
        now = now or timezone.now()

        if not self.is_active(now) or self.is_rate_limited(now):
            return False

        if check_password(str(raw_code or ""), self.verification_code_hash):
            self.verification_failed_attempts = 0
            self.last_verification_failed_at = None
            self.locked_until = None
            self.last_accessed_at = now
            self.save(
                update_fields=[
                    "verification_failed_attempts",
                    "last_verification_failed_at",
                    "locked_until",
                    "last_accessed_at",
                ]
            )
            return True

        self.verification_failed_attempts += 1
        self.last_verification_failed_at = now

        update_fields = [
            "verification_failed_attempts",
            "last_verification_failed_at",
        ]

        if self.verification_failed_attempts >= 5:
            self.locked_until = now + timedelta(minutes=15)
            update_fields.append("locked_until")

        self.save(update_fields=update_fields)
        return False


class CandidateResultFeedback(models.Model):
    """
    A candidate's reflection on one area of a frozen result snapshot.
    """

    RECOGNISES = "recognises"
    PARTLY_RECOGNISES = "partly_recognises"
    DOES_NOT_RECOGNISE = "does_not_recognise"

    RESULT_AREA_CHOICES = (
        ("personality", "Personality"),
        ("skills", "Skills"),
        ("motivation", "Motivation"),
    )
    RESPONSE_CHOICES = (
        (RECOGNISES, "I recognise myself"),
        (PARTLY_RECOGNISES, "I partly recognise myself"),
        (DOES_NOT_RECOGNISE, "I do not recognise myself"),
    )

    snapshot = models.ForeignKey(
        CandidateResultSnapshot,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    result_area = models.CharField(max_length=32, choices=RESULT_AREA_CHOICES)
    response = models.CharField(max_length=32, choices=RESPONSE_CHOICES)
    comment = models.TextField(blank=True, max_length=2000)
    locale = models.CharField(max_length=10, default="sv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["result_area"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "result_area"],
                name="cand_feedback_snap_area_uniq",
            ),
        ]

    def __str__(self):
        return f"Candidate feedback #{self.pk} ({self.result_area})"


class CandidateTestExperienceFeedback(models.Model):
    """Overall test-experience feedback tied to the result the candidate saw."""

    snapshot = models.OneToOneField(
        CandidateResultSnapshot,
        on_delete=models.CASCADE,
        related_name="test_experience_feedback",
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(value, str(value)) for value in range(1, 6)],
    )
    comment = models.TextField(blank=True, max_length=2000)
    locale = models.CharField(max_length=10, default="sv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Test experience feedback #{self.pk}"
