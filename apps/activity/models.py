# apps/activity/models.py
from django.conf import settings
from django.db import models

class ActivityEvent(models.Model):
    class Verb(models.TextChoices):
        # ---------------------------------------------------------
        # Test process activity
        # ---------------------------------------------------------
        PROCESS_CREATED = "process_created", "Process skapad"
        PROCESS_ARCHIVED = "process_archived", "Process arkiverad"
        PROCESS_DELETED = "process_deleted", "Process raderad"

        CANDIDATE_ADDED = "candidate_added", "Kandidat lades till i process"
        CANDIDATE_REMOVED = "candidate_removed", "Kandidat togs bort från process"

        INVITE_SENT = "invite_sent", "Testinbjudan skickad"

        TEST_STARTED = "test_started", "Test påbörjat"
        TEST_COMPLETED = "test_completed", "Test slutfört"
        ALL_TESTS_COMPLETED = "all_tests_completed", "Alla tester slutförda"

        STATUS_CHANGED = "status_changed", "Status ändrad"

        # ---------------------------------------------------------
        # Admin / company activity
        # ---------------------------------------------------------
        COMPANY_CREATED = "company_created", "Företag skapat"
        COMPANY_UPDATED = "company_updated", "Företag uppdaterat"
        COMPANY_DELETED = "company_deleted", "Företag raderat"

        COMPANY_MEMBER_INVITED = "company_member_invited", "Användare inbjuden"
        COMPANY_MEMBER_ADDED = "company_member_added", "Användare tillagd"
        COMPANY_MEMBER_REMOVED = "company_member_removed", "Användare borttagen"
        COMPANY_MEMBER_ROLE_UPDATED = "company_member_role_updated", "Användarroll uppdaterad"

        COMPANY_INVITE_ACCEPTED = "company_invite_accepted", "Inbjudan accepterad"

        ORGUNIT_CREATED = "orgunit_created", "Konto/enhet skapad"
        ORGUNIT_UPDATED = "orgunit_updated", "Konto/enhet uppdaterad"
        ORGUNIT_MOVED = "orgunit_moved", "Konto/enhet flyttad"
        ORGUNIT_DELETED = "orgunit_deleted", "Konto/enhet raderad"

        USER_ACCESS_UPDATED = "user_access_updated", "Användaråtkomst uppdaterad"
        USER_LOGGED_IN = "user_logged_in", "Användare loggade in"

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="activity_events",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_events",
    )

    actor_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    verb = models.CharField(
        max_length=80,
        choices=Verb.choices,
    )

    process = models.ForeignKey(
        "processes.TestProcess",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="activity_events",
    )

    candidate = models.ForeignKey(
        "processes.Candidate",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="activity_events",
    )

    invitation = models.ForeignKey(
        "processes.TestInvitation",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="activity_events",
    )

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

    def __str__(self):
        return f"{self.get_verb_display()} · {self.created_at:%Y-%m-%d %H:%M}"

    def invite_email_log_id(self):
        return (self.meta or {}).get("email_log_id")

    def activity_name(self):
        return (self.meta or {}).get("activity_name")

    def actor_display(self):
        if self.actor:
            full = f"{self.actor.first_name} {self.actor.last_name}".strip()
            return full or getattr(self.actor, "email", "Unknown user")

        return self.actor_name or "System"

    def candidate_display(self):
        if self.candidate:
            return str(self.candidate)

        meta = self.meta or {}
        return (
            meta.get("candidate_name")
            or meta.get("candidate_email")
            or "the candidate"
        )

    def company_display(self):
        meta = self.meta or {}

        if self.company_id:
            return self.company.name

        return meta.get("company_name") or "the company"

    def target_user_display(self):
        """
        Used for admin events where the affected user is stored in meta,
        for example invited_user_email or user_email.
        """
        meta = self.meta or {}

        name = (
            meta.get("user_name")
            or meta.get("invited_user_name")
            or meta.get("member_name")
        )

        email = (
            meta.get("user_email")
            or meta.get("invited_user_email")
            or meta.get("member_email")
        )

        return name or email or "the user"

    def orgunit_display(self):
        meta = self.meta or {}

        return (
            meta.get("org_unit_name")
            or meta.get("unit_name")
            or meta.get("account_name")
            or "the account"
        )

    def message(self):
        actor = self.actor_display()
        meta = self.meta or {}

        candidate = self.candidate_display()
        company = self.company_display()
        target_user = self.target_user_display()
        org_unit = self.orgunit_display()

        process_name = self.process.name if self.process else "the test process"

        # ---------------------------------------------------------
        # Admin / company activity
        # ---------------------------------------------------------

        if self.verb == self.Verb.COMPANY_CREATED:
            return f"{actor} created company {company}"

        if self.verb == self.Verb.COMPANY_UPDATED:
            return f"{actor} updated company {company}"

        if self.verb == self.Verb.COMPANY_DELETED:
            company_name = meta.get("company_name") or company
            return f"{actor} deleted company {company_name}"

        if self.verb == self.Verb.COMPANY_MEMBER_INVITED:
            return f"{actor} invited {target_user} to {company}"

        if self.verb == self.Verb.COMPANY_MEMBER_ADDED:
            return f"{actor} added {target_user} to {company}"

        if self.verb == self.Verb.COMPANY_MEMBER_REMOVED:
            return f"{actor} removed {target_user} from {company}"

        if self.verb == self.Verb.COMPANY_MEMBER_ROLE_UPDATED:
            old_role = meta.get("old_role")
            new_role = meta.get("new_role")

            if old_role and new_role:
                return f"{actor} changed {target_user}'s role in {company}: {old_role} → {new_role}"

            return f"{actor} updated {target_user}'s role in {company}"

        if self.verb == self.Verb.COMPANY_INVITE_ACCEPTED:
            return f"{target_user} accepted the invitation to {company}"

        if self.verb == self.Verb.ORGUNIT_CREATED:
            return f"{actor} created account {org_unit} in {company}"

        if self.verb == self.Verb.ORGUNIT_UPDATED:
            return f"{actor} updated account {org_unit} in {company}"

        if self.verb == self.Verb.ORGUNIT_MOVED:
            old_parent = meta.get("old_parent_name")
            new_parent = meta.get("new_parent_name")

            if old_parent or new_parent:
                return f"{actor} moved account {org_unit} in {company}"

            return f"{actor} moved account {org_unit}"

        if self.verb == self.Verb.ORGUNIT_DELETED:
            return f"{actor} deleted account {org_unit} from {company}"

        if self.verb == self.Verb.USER_ACCESS_UPDATED:
            return f"{actor} updated access for {target_user} in {company}"

        if self.verb == self.Verb.USER_LOGGED_IN:
            return f"{actor} logged in"

        # ---------------------------------------------------------
        # Test process / candidate activity
        # ---------------------------------------------------------

        if self.verb == self.Verb.PROCESS_CREATED:
            return f"{actor} created the test process {process_name}"

        if self.verb == self.Verb.PROCESS_ARCHIVED:
            return f"{actor} archived the test process {process_name}"

        if self.verb == self.Verb.PROCESS_DELETED:
            return f"{actor} deleted the test process {process_name}"

        if self.verb == self.Verb.CANDIDATE_ADDED:
            return f"{actor} added {candidate} to {process_name}"

        if self.verb == self.Verb.CANDIDATE_REMOVED:
            return f"{actor} removed {candidate} from {process_name}"

        if self.verb == self.Verb.INVITE_SENT:
            return f"Assessment invitation sent to {candidate} by {actor}"

        if self.verb == self.Verb.TEST_STARTED:
            activity_name = meta.get("activity_name")
            if activity_name:
                return f"{candidate} started {activity_name}"

            return f"{candidate} started the assessment"

        if self.verb == self.Verb.TEST_COMPLETED:
            activity_name = meta.get("activity_name")
            if activity_name:
                return f"{candidate} completed {activity_name}"

            return f"{candidate} completed the assessment"

        if self.verb == self.Verb.ALL_TESTS_COMPLETED:
            return f"{candidate} completed all assessments"

        if self.verb == self.Verb.STATUS_CHANGED:
            old = meta.get("old_status")
            new = meta.get("new_status")
            activity_name = meta.get("activity_name")
            level = meta.get("level")

            if level == "activity" and new == "started" and activity_name:
                return f"{candidate} started {activity_name}"

            if level == "activity" and new == "completed" and activity_name:
                return f"{candidate} completed {activity_name}"

            if new == "started":
                return f"{candidate} started the process"

            if new == "completed":
                return f"{candidate} completed the process"

            if old and new:
                return f"{actor} updated {candidate}: {old} → {new}"

            return f"{actor} updated {candidate}"

        return self.get_verb_display()