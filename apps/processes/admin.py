from django.contrib import admin
from .models import TestInvitation

from .models import HistoricalProcessCandidate, HistoricalCandidateReport

from django.contrib import admin

from .models import (
    TestProcess,
    Candidate,
    TestInvitation,
    HistoricalProcessCandidate,
    HistoricalCandidateReport,
)

@admin.register(TestProcess)
class TestProcessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "org_unit",
        "process_type",
        "is_archived",
        "sova_sync_enabled",
        "created_by",
        "created_at",
    )

    list_filter = (
        "is_historical",
        "is_archived",
        "sova_sync_enabled",
        "company",
        "org_unit",
        "created_at",
    )

    search_fields = (
        "name",
        "company__name",
        "org_unit__name",
        "created_by__email",
        "created_by__first_name",
        "created_by__last_name",
        "account_code",
        "project_code",
        "project_name_snapshot",
    )

    raw_id_fields = (
        "company",
        "org_unit",
        "created_by",
        "created_by_admin",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Basic information", {
            "fields": (
                "name",
                "company",
                "org_unit",
                "created_by",
                "created_by_admin",
            )
        }),
        ("Process type", {
            "fields": (
                "is_historical",
                "is_archived",
                "sova_sync_enabled",
                "source",
            )
        }),
        ("Tests", {
            "fields": (
                "purpose",
                "selected_tests",
            )
        }),
        ("SOVA information", {
            "fields": (
                "provider",
                "account_code",
                "project_code",
                "sova_project_id",
                "project_name_snapshot",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
            )
        }),
    )

    def process_type(self, obj):
        if obj.is_historical:
            return "Historical"
        return "Live SOVA"

    process_type.short_description = "Type"

@admin.register(TestInvitation)
class TestInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidate",
        "process",
        "status",
        "sova_overall_status",
        "sova_current_phase_code",
        "sova_current_phase_idx",
        "request_id",
        "sova_invitation_id",
        "invited_at",
        "completed_at",
        "created_at",
    )

    list_filter = ("status", "source", "sova_overall_status")
    search_fields = (
        "candidate__email",
        "candidate__first_name",
        "candidate__last_name",
        "request_id",
        "sova_invitation_id",
        "sova_overall_status",
    )

    readonly_fields = ("created_at", "invited_at", "completed_at")

    fieldsets = (
        ("Core", {"fields": ("process", "candidate", "status", "source")}),
        ("SOVA status", {"fields": ("sova_overall_status", "sova_current_phase_code", "sova_current_phase_idx")}),
        ("SOVA identifiers", {"fields": ("request_id", "sova_invitation_id", "sova_project_id")}),
        ("Webhook debug (latest payload)", {"fields": ("sova_payload",)}),
        ("Results", {"fields": ("overall_score", "project_results")}),
        ("Timestamps", {"fields": ("created_at", "invited_at", "completed_at")}),
    )


@admin.register(HistoricalProcessCandidate)
class HistoricalProcessCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "process",
        "status",
        "created_by",
        "created_at",
    )
    list_filter = (
        "status",
        "process__company",
        "process",
        "created_at",
    )
    search_fields = (
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
        "process__name",
        "notes",
    )
    raw_id_fields = (
        "process",
        "candidate",
        "created_by",
    )
    readonly_fields = (
        "created_at",
    )


@admin.register(HistoricalCandidateReport)
class HistoricalCandidateReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "historical_candidate",
        "uploaded_by",
        "uploaded_at",
    )
    list_filter = (
        "uploaded_at",
        "historical_candidate__process__company",
        "historical_candidate__process",
    )
    search_fields = (
        "title",
        "original_filename",
        "historical_candidate__candidate__first_name",
        "historical_candidate__candidate__last_name",
        "historical_candidate__candidate__email",
        "historical_candidate__process__name",
    )
    autocomplete_fields = (
        "historical_candidate",
        "uploaded_by",
    )
    readonly_fields = (
        "uploaded_at",
    )