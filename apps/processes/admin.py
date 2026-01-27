from django.contrib import admin
from .models import TestInvitation


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
