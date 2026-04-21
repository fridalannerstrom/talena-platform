# apps/activity/models.py
from django.conf import settings
from django.db import models

class ActivityEvent(models.Model):
    class Verb(models.TextChoices):
        PROCESS_CREATED = "process_created", "Process skapad"
        PROCESS_ARCHIVED = "process_archived", "Process arkiverad"
        PROCESS_DELETED = "process_deleted", "Process raderad"

        CANDIDATE_ADDED = "candidate_added", "Kandidat lades till i process"
        CANDIDATE_REMOVED = "candidate_removed", "Kandidat togs bort från process"

        INVITE_SENT = "invite_sent", "Inbjudan skickad"

        TEST_STARTED = "test_started", "Test påbörjat"
        TEST_COMPLETED = "test_completed", "Test slutfört"
        ALL_TESTS_COMPLETED = "all_tests_completed", "Alla tester slutförda"

        STATUS_CHANGED = "status_changed", "Status ändrad"

    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="activity_events")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_events",
    )
    actor_name = models.CharField(max_length=255, blank=True, default="")  # t.ex. "SOVA" vid webhook

    verb = models.CharField(max_length=50, choices=Verb.choices)

    process = models.ForeignKey("processes.TestProcess", null=True, blank=True, on_delete=models.CASCADE, related_name="activity_events")
    candidate = models.ForeignKey("processes.Candidate", null=True, blank=True, on_delete=models.CASCADE, related_name="activity_events")
    invitation = models.ForeignKey("processes.TestInvitation", null=True, blank=True, on_delete=models.CASCADE, related_name="activity_events")

    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "-created_at"]),
            models.Index(fields=["process", "-created_at"]),
            models.Index(fields=["candidate", "-created_at"]),
            models.Index(fields=["invitation", "-created_at"]),
            models.Index(fields=["verb", "-created_at"]),
        ]

    def invite_email_log_id(self):
        return (self.meta or {}).get("email_log_id")
    
    def activity_name(self):
        return (self.meta or {}).get("activity_name")

    def actor_display(self):
        if self.actor:
            full = f"{self.actor.first_name} {self.actor.last_name}".strip()
            return full or getattr(self.actor, "email", "Okänd")
        return self.actor_name or "System"
    
    def message(self):
        actor = self.actor_display()
        meta = self.meta or {}

        if self.verb == self.Verb.PROCESS_CREATED:
            return f"{actor} skapade testprocessen {self.process.name}"

        if self.verb == self.Verb.PROCESS_ARCHIVED:
            return f"{actor} arkiverade testprocessen {self.process.name}"

        if self.verb == self.Verb.PROCESS_DELETED:
            return f"{actor} raderade testprocessen {self.process.name}"

        if self.verb == self.Verb.CANDIDATE_ADDED:
            return f"{actor} lade till {self.candidate}"

        if self.verb == self.Verb.CANDIDATE_REMOVED:
            return f"{actor} tog bort {self.candidate}"

        if self.verb == self.Verb.INVITE_SENT:
            return f"Inbjudan skickades till {self.candidate}"

        if self.verb == self.Verb.STATUS_CHANGED:
            old = (self.meta or {}).get("old_status")
            new = (self.meta or {}).get("new_status")
            activity_name = (self.meta or {}).get("activity_name")
            level = (self.meta or {}).get("level")

            if level == "activity" and new == "started" and activity_name:
                return f"{self.candidate} påbörjade {activity_name}"

            if level == "activity" and new == "completed" and activity_name:
                return f"{self.candidate} slutförde {activity_name}"

            if new == "started":
                return f"{self.candidate} påbörjade testet"

            if new == "completed":
                return f"{self.candidate} slutförde testet"

            return f"{actor} uppdaterade {self.candidate}: {old} → {new}"
    
