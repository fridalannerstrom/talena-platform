from datetime import timedelta

import secrets

from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import CandidateResultAccess, CandidateResultSnapshot


DEFAULT_ACCESS_LIFETIME = timedelta(days=30)


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

    if expires_at is None:
        expires_at = timezone.now() + DEFAULT_ACCESS_LIFETIME

    access = CandidateResultAccess.objects.create(
        snapshot=snapshot,
        token_digest=CandidateResultAccess.digest_token(raw_token),
        verification_code_hash=make_password(raw_code),
        locale=snapshot.locale,
        expires_at=expires_at,
    )

    return access, raw_token, raw_code
