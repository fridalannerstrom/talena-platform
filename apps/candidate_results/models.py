from datetime import timedelta

import hashlib
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CandidateResultSnapshot(models.Model):
    """
    Immutable candidate-facing result content for one project invitation.

    The snapshot deliberately stores presentation-ready content instead of
    reading the current AI fields at request time. Later prompt or AI changes
    must not rewrite a result a candidate has already received.
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
    prompt_versions = models.JSONField(
        default=dict,
        help_text="Prompt/version metadata used to create the content.",
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
            models.Index(fields=["process", "candidate"]),
        ]

    def __str__(self):
        return f"Candidate result snapshot #{self.pk}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "Candidate result snapshots are immutable."
            )
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
            models.Index(fields=["expires_at"]),
            models.Index(fields=["revoked_at"]),
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


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def create_candidate_result_access(
    snapshot: CandidateResultSnapshot,
    *,
    expires_at=None,
):
    """
    Create access credentials once and return the raw secrets once.

    Returning existing access without secrets makes repeated completion events
    safe: an idempotent retry cannot silently replace a candidate's active
    credentials.
    """
    existing = CandidateResultAccess.objects.filter(
        snapshot=snapshot,
    ).first()

    if existing:
        return existing, None, None

    raw_token = secrets.token_urlsafe(32)
    raw_code = generate_verification_code()

    access = CandidateResultAccess.objects.create(
        snapshot=snapshot,
        token_digest=CandidateResultAccess.digest_token(raw_token),
        verification_code_hash=make_password(raw_code),
        locale=snapshot.locale,
        expires_at=expires_at,
    )

    return access, raw_token, raw_code
