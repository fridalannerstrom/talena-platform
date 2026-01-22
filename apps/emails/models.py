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

    status = models.CharField(max_length=30, default="queued")  # queued/sent/failed
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    def mark_sent(self, provider_message_id: str | None = None):
        self.status = "sent"
        self.sent_at = timezone.now()
        if provider_message_id:
            self.provider_message_id = provider_message_id
        self.save(update_fields=["status", "sent_at", "provider_message_id"])

    def mark_failed(self, error: str):
        self.status = "failed"
        self.error = error
        self.save(update_fields=["status", "error"])