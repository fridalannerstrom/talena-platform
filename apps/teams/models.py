from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="teams",
    )
    org_unit = models.ForeignKey(
        "accounts.OrgUnit",
        on_delete=models.PROTECT,
        related_name="teams",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_teams",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    goals = models.JSONField(default=list, blank=True)
    context = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_team_name_per_company",
            )
        ]

    def clean(self):
        if (
            self.org_unit_id
            and self.company_id
            and self.org_unit.company_id != self.company_id
        ):
            raise ValidationError(
                {"org_unit": _("The team’s unit must belong to the same company.")}
            )

    def __str__(self):
        return f"{self.name} ({self.company})"


class TeamMembership(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )

    role = models.CharField(max_length=255, blank=True)
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: manual, sova_import",
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["team__name", "candidate"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "candidate"],
                name="unique_candidate_per_team",
            )
        ]

    def __str__(self):
        return f"{self.candidate} in {self.team}"


class TeamAIInsight(models.Model):
    INSIGHT_TYPES = [
        ("communication_styles", "Communication styles"),
        ("collaboration", "Collaboration"),
    ]

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="ai_insights",
    )
    insight_type = models.CharField(max_length=40, choices=INSIGHT_TYPES)
    language = models.CharField(max_length=10, choices=[("sv", "Swedish"), ("en", "English")])
    content = models.TextField()
    source_signature = models.CharField(max_length=64)
    source_metadata = models.JSONField(default=dict, blank=True)
    prompt_key = models.CharField(max_length=100)
    prompt_revision = models.CharField(max_length=100, blank=True)
    prompt_digest = models.CharField(max_length=64)
    generated_at = models.DateTimeField(auto_now=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_team_insights",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "insight_type", "language"],
                name="unique_team_ai_insight_type_language",
            )
        ]

    def __str__(self):
        return f"{self.team}: {self.insight_type} ({self.language})"
