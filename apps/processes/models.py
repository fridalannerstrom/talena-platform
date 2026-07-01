from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid
from django.urls import reverse
from apps.accounts.models import OrgUnit, Company
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event
import os
from .purpose_context_config import normalize_purpose_key
from .purpose_utils import normalize_purpose_key


class TestProcess(models.Model):

    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=50, default="sova")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="processes", null=True, blank=True)

    project_code = models.CharField(max_length=255)
    project_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    account_code = models.CharField(max_length=255)

    job_title = models.CharField(max_length=255, blank=True, default="")
    job_location = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    purpose = models.CharField(max_length=80, blank=True, default="")
    selected_tests = models.JSONField(default=list, blank=True)

    self_registration_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        null=True, blank=True,  # TEMP så du slipper backfill nu direkt
        related_name="processes",
    )

    # Denna kan fortsätta vara "kunden" om du vill
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_processes",
    )

    # ✅ NY: admin som skapade processen (valfritt)
    created_by_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_processes_created_as_admin",
    )

    labels = models.ManyToManyField(
        "processes.ProcessLabel",
        blank=True,
        related_name="processes",
    )


    created_at = models.DateTimeField(auto_now_add=True)

    SOURCE_CHOICES = (
        ("talena", "Created in Talena"),
        ("sova_import", "Imported from SOVA"),
    )

    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default="talena",
    )

    is_historical = models.BooleanField(default=False)

    sova_sync_enabled = models.BooleanField(default=True)

    sova_account_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    sova_project_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    sova_import_notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.account_code}:{self.project_code})"
    
    def get_self_registration_url(self):
                    return reverse("processes:self_register", kwargs={"token": str(self.self_registration_token)})
    
    def is_template_locked(self) -> bool:
        """
        Lås testpaket så fort processen är påbörjad.
        Just nu: om någon invitation har status sent/started/completed.
        """
        return self.invitations.filter(status__in=["sent", "started", "completed"]).exists()
    
    def can_delete(self) -> bool:
        # delete OK endast om inget har skickats/påbörjats/avslutats
        return not self.invitations.filter(status__in=["sent", "started", "completed"]).exists()

    def archive(self):
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save(update_fields=["is_archived", "archived_at"])

    def unarchive(self):
        self.is_archived = False
        self.archived_at = None
        self.save(update_fields=["is_archived", "archived_at"])


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
        ("historical", "Historical"),
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
    request_id = models.CharField(max_length=512, null=True, blank=True) 
    sova_project_id = models.IntegerField(null=True, blank=True)   
    overall_score = models.FloatField(null=True, blank=True)
    project_results = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="created")
    invited_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    result_payload = models.JSONField(null=True, blank=True)   # hela resultatet (om du vill)
    score = models.IntegerField(null=True, blank=True)         # demo-score 0–100 (eller vad du vill)

    sova_invitation_id = models.CharField(max_length=255, blank=True, null=True)
    sova_payload = models.JSONField(blank=True, null=True)
    sova_overall_status = models.CharField(max_length=50, blank=True, default="")
    sova_current_phase_code = models.CharField(max_length=255, blank=True, default="")
    sova_current_phase_idx = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    sova_activities = models.JSONField(null=True, blank=True)
    sova_phases = models.JSONField(null=True, blank=True)
    sova_reports = models.JSONField(null=True, blank=True)

    ai_summary = models.TextField(blank=True, default="")
    ai_summary_generated_at = models.DateTimeField(null=True, blank=True)
    ai_summary_status = models.CharField(max_length=30, blank=True, default="not_started")

    # ------------------------------------------------------------
    # AI purpose fit
    # ------------------------------------------------------------
    ai_purpose_fit = models.JSONField(
        default=dict,
        blank=True,
    )

    ai_purpose_fit_status = models.CharField(
        max_length=30,
        blank=True,
        default="not_started",
    )

    ai_purpose_fit_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ai_purpose_fit_purpose = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

        # ------------------------------------------------------------
    # AI response-style guidance
    # ------------------------------------------------------------
    ai_response_style_guidance = models.JSONField(
        default=dict,
        blank=True,
    )

    ai_response_style_guidance_status = models.CharField(
        max_length=30,
        blank=True,
        default="not_started",
        choices=[
            ("not_started", "Not started"),
            ("generating", "Generating"),
            ("completed", "Completed"),
            ("outdated", "Outdated"),
            ("failed", "Failed"),
        ],
    )

    ai_response_style_guidance_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ai_response_style_guidance_purpose = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )



    is_historical = models.BooleanField(default=False, db_index=True)

    historical_report_file = models.FileField(
        upload_to="historical_sova_reports/",
        blank=True,
        null=True,
    )

    historical_report_url = models.URLField(
        blank=True,
        default="",
    )

    historical_notes = models.TextField(
        blank=True,
        default="",
    )

    sova_candidate_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

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

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_invitations",
    )


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


class ProcessLabel(models.Model):
    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="process_labels")
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name
    

class ProcessRoleContext(models.Model):
    process = models.OneToOneField(
        TestProcess,
        on_delete=models.CASCADE,
        related_name="role_context",
    )

    role_title = models.CharField(max_length=255, blank=True)

    job_advertisement = models.TextField(blank=True)
    requirements_profile = models.TextField(blank=True)
    competency_profile = models.TextField(blank=True)
    must_haves = models.TextField(blank=True)
    nice_to_haves = models.TextField(blank=True)
    priorities = models.TextField(blank=True)
    interview_notes = models.TextField(blank=True)

    # Stores a separate version of the context for each purpose.
    purpose_data = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    CONTEXT_FIELDS = (
        "role_title",
        "job_advertisement",
        "requirements_profile",
        "competency_profile",
        "must_haves",
        "nice_to_haves",
        "priorities",
        "interview_notes",
    )

    def get_current_context_data(self):
        return {
            field_name: getattr(self, field_name, "") or ""
            for field_name in self.CONTEXT_FIELDS
        }

    def get_context_for_purpose(self, purpose):
        purpose_key = normalize_purpose_key(purpose)
        saved_data = (self.purpose_data or {}).get(purpose_key)

        if isinstance(saved_data, dict):
            return {
                field_name: saved_data.get(field_name, "") or ""
                for field_name in self.CONTEXT_FIELDS
            }

        return None

    def save_context_for_purpose(self, purpose, context_data=None):
        purpose_key = normalize_purpose_key(purpose)

        data = dict(self.purpose_data or {})

        if context_data is None:
            context_data = self.get_current_context_data()

        data[purpose_key] = {
            field_name: context_data.get(field_name, "") or ""
            for field_name in self.CONTEXT_FIELDS
        }

        self.purpose_data = data

    def apply_context_data(self, context_data):
        for field_name in self.CONTEXT_FIELDS:
            setattr(
                self,
                field_name,
                context_data.get(field_name, "") or "",
            )

    def has_content(self):
        return any(
            (getattr(self, field_name, "") or "").strip()
            for field_name in self.CONTEXT_FIELDS
        )

    def __str__(self):
        return f"Process context for {self.process}"


def historical_candidate_report_upload_path(instance, filename):
    company_id = instance.invitation.process.company_id or "unknown-company"
    process_id = instance.invitation.process_id or "unknown-process"
    candidate_id = instance.invitation.candidate_id or "unknown-candidate"

    return (
        f"historical_sova_reports/"
        f"company_{company_id}/"
        f"process_{process_id}/"
        f"candidate_{candidate_id}/"
        f"{filename}"
    )


class HistoricalProcessCandidate(models.Model):
    STATUS_CHOICES = (
        ("completed", "Completed"),
        ("started", "Started"),
        ("created", "Created / unknown"),
    )

    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="historical_candidates",
    )

    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="historical_process_records",
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="completed",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    sova_candidate_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_historical_process_candidates",
    )

    ai_summary = models.TextField(
        blank=True,
        default="",
    )

    ai_summary_status = models.CharField(
        max_length=20,
        default="not_started",
        choices=[
            ("not_started", "Not started"),
            ("generating", "Generating"),
            ("completed", "Completed"),
            ("outdated", "Outdated"),
            ("failed", "Failed"),
        ],
    )

    ai_summary_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

        # ------------------------------------------------------------
    # AI response-style guidance
    # ------------------------------------------------------------
    ai_response_style_guidance = models.JSONField(
        default=dict,
        blank=True,
    )

    ai_response_style_guidance_status = models.CharField(
        max_length=30,
        blank=True,
        default="not_started",
        choices=[
            ("not_started", "Not started"),
            ("generating", "Generating"),
            ("completed", "Completed"),
            ("outdated", "Outdated"),
            ("failed", "Failed"),
        ],
    )

    ai_response_style_guidance_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ai_response_style_guidance_purpose = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["candidate__last_name", "candidate__first_name", "-created_at"]
        unique_together = ("process", "candidate", "sova_candidate_id")

    def __str__(self):
        return f"{self.candidate} in {self.process}"


def historical_candidate_report_upload_path(instance, filename):
    company_id = instance.historical_candidate.process.company_id or "unknown-company"
    process_id = instance.historical_candidate.process_id or "unknown-process"
    candidate_id = instance.historical_candidate.candidate_id or "unknown-candidate"

    return (
        f"historical_sova_reports/"
        f"company_{company_id}/"
        f"process_{process_id}/"
        f"candidate_{candidate_id}/"
        f"{filename}"
    )


class HistoricalCandidateReport(models.Model):
    historical_candidate = models.ForeignKey(
        "processes.HistoricalProcessCandidate",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    file = models.FileField(
        upload_to=historical_candidate_report_upload_path,
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_historical_candidate_reports",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title", "uploaded_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)

        if not self.title and self.original_filename:
            self.title = self.original_filename

        super().save(*args, **kwargs)


class HistoricalAssessmentImport(models.Model):
    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="assessment_imports",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historical_assessment_imports",
    )

    file = models.FileField(upload_to="historical_assessment_imports/")
    original_filename = models.CharField(max_length=255)

    assessment_type = models.CharField(max_length=50, blank=True)
    scale = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=50, default="uploaded")
    rows_processed = models.PositiveIntegerField(default=0)
    candidates_created = models.PositiveIntegerField(default=0)
    results_created = models.PositiveIntegerField(default=0)
    scores_created = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_filename


class HistoricalAssessmentResult(models.Model):
    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="historical_assessment_results",
    )
    historical_candidate = models.ForeignKey(
        "processes.HistoricalProcessCandidate",
        on_delete=models.CASCADE,
        related_name="assessment_results",
    )
    candidate = models.ForeignKey(
        "processes.Candidate",
        on_delete=models.CASCADE,
        related_name="historical_assessment_results",
    )
    import_file = models.ForeignKey(
        "processes.HistoricalAssessmentImport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results",
    )

    assessment_type = models.CharField(max_length=50)
    scale = models.CharField(max_length=50, blank=True)

    sova_candidate_id = models.CharField(max_length=100, blank=True)
    sova_result_id = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=20, blank=True)

    time_added = models.DateTimeField(null=True, blank=True)
    time_completed = models.DateTimeField(null=True, blank=True)

    raw_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["candidate__last_name", "candidate__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "process",
                    "candidate",
                    "assessment_type",
                    "scale",
                    "sova_result_id",
                ],
                name="unique_historical_assessment_result",
            )
        ]

    def __str__(self):
        return f"{self.candidate} - {self.assessment_type} ({self.scale})"


class HistoricalAssessmentScore(models.Model):
    result = models.ForeignKey(
        "processes.HistoricalAssessmentResult",
        on_delete=models.CASCADE,
        related_name="scores",
    )

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    scale = models.CharField(max_length=50, blank=True)

    score = models.FloatField(null=True, blank=True)
    percentile = models.FloatField(null=True, blank=True)

    raw_value = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["result", "name", "category", "scale"],
                name="unique_historical_assessment_score",
            )
        ]

    def __str__(self):
        return f"{self.name}: {self.score or self.percentile}"