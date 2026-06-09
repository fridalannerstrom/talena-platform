from django.db import models

# Create your models here.
from django.db import models


class Team(models.Model):
    company = models.ForeignKey(
        "accounts.Company",  # ÄNDRA om din Company-model ligger någon annanstans
        on_delete=models.CASCADE,
        related_name="teams"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_team_name_per_company"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.company})"


class TeamMembership(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="team_memberships"
    )

    role = models.CharField(max_length=255, blank=True)
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: manual, sova_import"
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["team__name", "candidate"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "candidate"],
                name="unique_candidate_per_team"
            )
        ]

    def __str__(self):
        return f"{self.candidate} in {self.team}"