from django.contrib import admin
from .models import Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "company",
        "is_archived",
        "created_at",
        "updated_at",
    ]
    list_filter = ["company", "is_archived"]
    search_fields = [
        "name",
        "description",
        "company__name",
    ]
    inlines = [TeamMembershipInline]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = [
        "team",
        "candidate",
        "role",
        "source",
        "added_at",
    ]
    list_filter = [
        "team__company",
        "source",
    ]
    search_fields = [
        "team__name",
    ]