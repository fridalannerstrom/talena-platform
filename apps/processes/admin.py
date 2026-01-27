from django.contrib import admin
from .models import TestInvitation


@admin.register(TestInvitation)
class TestInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidate",
        "process",
        "status",
        "request_id",
        "sova_invitation_id",
        "invited_at",
        "completed_at",
        "created_at",
    )

    list_filter = ("status", "source")
    search_fields = (
        "candidate__email",
        "candidate__first_name",
        "candidate__last_name",
        "request_id",
        "sova_invitation_id",
    )

    readonly_fields = (
        "created_at",
        "invited_at",
        "completed_at",
    )

    fieldsets = (
        ("Core", {
            "fields": (
                "process",
                "candidate",
                "status",
                "source",
            )
        }),
        ("SOVA identifiers", {
            "fields": (
                "request_id",
                "sova_invitation_id",
                "sova_project_id",
            )
        }),
        ("Webhook debug (latest payload)", {
            "fields": (
                "sova_payload",
            )
        }),
        ("Results", {
            "fields": (
                "overall_score",
                "project_results",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "invited_at",
                "completed_at",
            )
        }),
    )
