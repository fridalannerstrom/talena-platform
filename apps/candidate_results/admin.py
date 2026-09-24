from django.contrib import admin

from .models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
    CandidateTestExperienceFeedback,
)


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


@admin.register(CandidateResultFeedback)
class CandidateResultFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "snapshot",
        "result_area",
        "response",
        "locale",
        "updated_at",
    )
    list_filter = ("result_area", "response", "locale")
    search_fields = (
        "snapshot__candidate__email",
        "snapshot__candidate__first_name",
        "snapshot__candidate__last_name",
    )
    readonly_fields = (
        "snapshot",
        "result_area",
        "response",
        "comment",
        "locale",
        "created_at",
        "updated_at",
    )


@admin.register(CandidateTestExperienceFeedback)
class CandidateTestExperienceFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "snapshot", "rating", "locale", "updated_at")
    list_filter = ("rating", "locale")
    search_fields = ("snapshot__candidate__email",)
    readonly_fields = ("snapshot", "rating", "comment", "locale", "created_at", "updated_at")
