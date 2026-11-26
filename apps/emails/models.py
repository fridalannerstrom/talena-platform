from django.db import models
from django.utils import timezone


class EmailTemplate(models.Model):
    TEMPLATE_TYPES = [
        ("invitation", "Invitation"),
        ("reminder", "Reminder"),
        ("completion", "Completion"),
    ]

    LANG_CHOICES = [
        ("sv", "Swedish"),
        ("en", "English"),
    ]

    process = models.ForeignKey(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="email_templates",
    )
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    language = models.CharField(max_length=10, choices=LANG_CHOICES, default="sv")

    subject = models.CharField(max_length=255)
    body = models.TextField(help_text="Use placeholders like {first_name}, {process_name}, {assessment_url}")

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["process", "template_type", "language"],
                name="uniq_template_per_process_type_lang",
            )
        ]

    def __str__(self):
        return f"{self.process_id} {self.template_type} {self.language}"


class CompanyInvitationTemplate(models.Model):
    """Company-wide default for candidate invitation emails, per language."""

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="invitation_email_templates",
    )
    language = models.CharField(max_length=10, choices=EmailTemplate.LANG_CHOICES, default="sv")
    subject = models.CharField(max_length=255)
    body = models.TextField(help_text="Include {assessment_url} so the candidate receives the test link.")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "language"],
                name="uniq_company_invitation_template_lang",
            ),
        ]

    def __str__(self):
        return f"{self.company_id} invitation {self.language}"


class EmailLog(models.Model):
    invitation = models.ForeignKey(
        "processes.TestInvitation",
        on_delete=models.CASCADE,
        related_name="email_logs",
    )

    template_type = models.CharField(max_length=50)  # "invitation"
    to_email = models.EmailField()

    subject = models.CharField(max_length=255)
    body_snapshot = models.TextField()

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Accepted by email service"),
        ("failed", "Send failed"),
    ]
    DELIVERY_STATUS_CHOICES = [
        ("unknown", "Unknown"),
        ("pending", "Pending"),
        ("delivered", "Delivered"),
        ("failed", "Could not be delivered"),
    ]

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="queued")
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)
    internet_message_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default="unknown",
    )
    delivery_status_updated_at = models.DateTimeField(blank=True, null=True)
    delivery_error_code = models.CharField(max_length=60, blank=True, default="")
    error = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def mark_sent(self, provider_message_id: str | None = None):
        self.status = "sent"
        self.sent_at = timezone.now()
        if provider_message_id:
            self.provider_message_id = provider_message_id
        if self.delivery_status == "unknown":
            from django.conf import settings
            if getattr(settings, "EMAIL_DELIVERY_TRACKING_ENABLED", False):
                self.delivery_status = "pending"
                self.delivery_status_updated_at = self.sent_at
        self.save(update_fields=[
            "status",
            "sent_at",
            "provider_message_id",
            "delivery_status",
            "delivery_status_updated_at",
        ])

    def mark_failed(self, error: str):
        self.status = "failed"
        self.error = error
        self.delivery_status = "unknown"
        self.delivery_status_updated_at = None
        if not self.delivery_error_code:
            self.delivery_error_code = "send_failed"
        self.save(update_fields=[
            "status",
            "error",
            "delivery_status",
            "delivery_status_updated_at",
            "delivery_error_code",
        ])

class EmailDeliveryUpdate(models.Model):
    """One idempotent delivery event received from the outbound email provider."""

    email_log = models.ForeignKey(
        EmailLog,
        on_delete=models.CASCADE,
        related_name="delivery_updates",
    )
    provider_event_id = models.CharField(max_length=255, unique=True)
    provider_status = models.CharField(max_length=40)
    delivery_status = models.CharField(
        max_length=20,
        choices=EmailLog.DELIVERY_STATUS_CHOICES,
    )
    provider_occurred_at = models.DateTimeField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["received_at", "pk"]
