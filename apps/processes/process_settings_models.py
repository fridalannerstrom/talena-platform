from django.db import models


class ProcessAutomationSettings(models.Model):
    """Process-level automation settings kept separate from the large process model."""

    process = models.OneToOneField(
        "processes.TestProcess",
        on_delete=models.CASCADE,
        related_name="automation_settings",
    )
    automatic_invitation_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Process automation settings"
        verbose_name_plural = "Process automation settings"

    def __str__(self):
        state = "on" if self.automatic_invitation_enabled else "off"
        return f"{self.process} · automatic invitation {state}"
