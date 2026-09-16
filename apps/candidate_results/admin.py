from django.contrib import admin

from .models import CandidateResultAccess, CandidateResultSnapshot


@admin.register(CandidateResultSnapshot)
class CandidateResultSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidate",
        "process",
        "invitation",
        "locale",
        "created_at",
    )
    list_filter = ("locale", "created_at")
    search_fields = (
        "candidate__email",
        "candidate__first_name",
        "candidate__last_name",
        "process__name",
    )
    readonly_fields = (
        "invitation",
        "candidate",
        "process",
        "locale",
        "content",
        "prompt_versions",
        "source_fingerprint",
        "created_at",
    )


@admin.register(CandidateResultAccess)
class CandidateResultAccessAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "snapshot",
        "locale",
        "created_at",
        "expires_at",
        "revoked_at",
        "last_accessed_at",
        "verification_failed_attempts",
    )
    list_filter = ("locale", "revoked_at", "expires_at")
    search_fields = (
        "snapshot__candidate__email",
        "snapshot__candidate__first_name",
        "snapshot__candidate__last_name",
    )
    readonly_fields = (
        "snapshot",
        "token_digest",
        "verification_code_hash",
        "locale",
        "created_at",
        "last_accessed_at",
        "expires_at",
        "revoked_at",
        "verification_failed_attempts",
        "last_verification_failed_at",
        "locked_until",
    )
