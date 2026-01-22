from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid
from django.urls import reverse

class TestProcess(models.Model):

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=50, default="sova")

    account_code = models.CharField(max_length=255)
    project_code = models.CharField(max_length=255)
    project_name_snapshot = models.CharField(max_length=255, blank=True, default="")

    job_title = models.CharField(max_length=255, blank=True, default="")
    job_location = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    self_registration_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

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
    
    def get_self_registration_url(self):
                    return reverse("processes:self_register", kwargs={"token": str(self.self_registration_token)})
    
class Candidate(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    email = models.EmailField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uniq_candidate_email")
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class TestInvitation(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("sent", "Sent"),
        ("started", "Started"),
        ("completed", "Completed"),
        ("expired", "Expired"),
        ("failed", "Failed"),
    ]

    SOURCE_CHOICES = [
        ("invited", "Invited"),
        ("self_registered", "Self-registered"),
    ]


    def status_label(self):
        return {
            "created": "Ej skickat",
            "sent": "Inbjuden",
            "started": "Påbörjat",
            "completed": "Färdigt",
            "expired": "Utgånget",
            "failed": "Fel",
        }.get(self.status, self.status)
    
    assessment_url = models.URLField(blank=True, null=True)
    sova_request_id = models.CharField(max_length=512, blank=True, null=True)

    process = models.ForeignKey("processes.TestProcess", on_delete=models.CASCADE, related_name="invitations")
    candidate = models.ForeignKey("processes.Candidate", on_delete=models.CASCADE, related_name="invitations")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="invited")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="created")
    invited_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    sova_invitation_id = models.CharField(max_length=255, blank=True, null=True)
    sova_payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["process", "candidate"], name="uniq_invitation_per_process")
        ]

    def mark_sent(self, sova_id: str | None = None, payload: dict | None = None):
        self.status = "sent"
        self.invited_at = timezone.now()
        if sova_id:
            self.sova_invitation_id = sova_id
        if payload is not None:
            self.sova_payload = payload
        self.save()


class SelfRegistration(models.Model):
    process = models.ForeignKey(TestProcess, on_delete=models.CASCADE, related_name="self_registrations")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    sova_candidate_id = models.CharField(max_length=100, blank=True, null=True)
    sova_order_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["process", "email"], name="uniq_process_email_registration")
        ]