from django.conf import settings
from django.db import models

class TestProcess(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=50, default="sova")

    account_code = models.CharField(max_length=255)
    project_code = models.CharField(max_length=255)
    project_name_snapshot = models.CharField(max_length=255, blank=True, default="")

    job_title = models.CharField(max_length=255, blank=True, default="")
    job_location = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_processes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.account_code}:{self.project_code})"