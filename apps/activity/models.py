# apps/activity/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _

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
        CANDIDATE_RESULT_EMAIL_SENT = "candidate_result_email_sent", "Kandidatresultat skickat"
        CANDIDATE_RESULT_EMAIL_FAILED = "candidate_result_email_failed", "Kandidatresultat kunde inte skickas"
        CANDIDATE_RESULT_SNAPSHOT_CREATED = "candidate_result_snapshot_created", "Kandidatrapport skapad"
        CANDIDATE_RESULT_LINK_OPENED = "candidate_result_link_opened", "Kandidatrapport öppnad"
        CANDIDATE_RESULT_CODE_VERIFIED = "candidate_result_code_verified", "Verifieringskod godkänd"
        CANDIDATE_RESULT_CODE_FAILED = "candidate_result_code_failed", "Felaktig verifieringskod"
        CANDIDATE_RESULT_FEEDBACK_SUBMITTED = "candidate_result_feedback_submitted", "Kandidatfeedback inskickad"
        CANDIDATE_RESULT_CODE_REPLACED = "candidate_result_code_replaced", "Verifieringskod ersatt"
        CANDIDATE_RESULT_ACCESS_REVOKED = "candidate_result_access_revoked", "Kandidatåtkomst återkallad"
        CANDIDATE_RESULT_ACCESS_EXPIRED = "candidate_result_access_expired", "Kandidatåtkomst utgången"

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
            return full or getattr(
                self.actor,
                "email",
                _("Unknown user"),
            )

        return self.actor_name or _("System")

    def candidate_display(self):
        if self.candidate:
            return str(self.candidate)

        meta = self.meta or {}
        return (
            meta.get("candidate_name")
            or meta.get("candidate_email")
            or _("the candidate")
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

        process_name = (
            self.process.name
            if self.process
            else _("the test process")
        )

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
            return _(
                "%(actor)s created the test process %(process_name)s"
            ) % {
                "actor": actor,
                "process_name": process_name,
            }

        if self.verb == self.Verb.PROCESS_ARCHIVED:
            return _(
                "%(actor)s archived the test process %(process_name)s"
            ) % {
                "actor": actor,
                "process_name": process_name,
            }

        if self.verb == self.Verb.PROCESS_DELETED:
            return _(
                "%(actor)s deleted the test process %(process_name)s"
            ) % {
                "actor": actor,
                "process_name": process_name,
            }

        if self.verb == self.Verb.CANDIDATE_ADDED:
            return _(
                "%(actor)s added %(candidate)s to %(process_name)s"
            ) % {
                "actor": actor,
                "candidate": candidate,
                "process_name": process_name,
            }

        if self.verb == self.Verb.CANDIDATE_REMOVED:
            return _(
                "%(actor)s removed %(candidate)s from %(process_name)s"
            ) % {
                "actor": actor,
                "candidate": candidate,
                "process_name": process_name,
            }

        if self.verb == self.Verb.INVITE_SENT:
            return _(
                "Assessment invitation sent to %(candidate)s by %(actor)s"
            ) % {
                "candidate": candidate,
                "actor": actor,
            }

        if self.verb == self.Verb.TEST_STARTED:
            activity_name = meta.get("activity_name")

            if activity_name:
                return _(
                    "%(candidate)s started %(activity_name)s"
                ) % {
                    "candidate": candidate,
                    "activity_name": activity_name,
                }

            return _(
                "%(candidate)s started the assessment"
            ) % {
                "candidate": candidate,
            }

        if self.verb == self.Verb.TEST_COMPLETED:
            activity_name = meta.get("activity_name")

            if activity_name:
                return _(
                    "%(candidate)s completed %(activity_name)s"
                ) % {
                    "candidate": candidate,
                    "activity_name": activity_name,
                }

            return _(
                "%(candidate)s completed the assessment"
            ) % {
                "candidate": candidate,
            }

        if self.verb == self.Verb.CANDIDATE_RESULT_EMAIL_SENT:
            return _(
                "Candidate result email sent to %(candidate)s"
            ) % {"candidate": candidate}

        if self.verb == self.Verb.CANDIDATE_RESULT_EMAIL_FAILED:
            return _(
                "Candidate result email failed for %(candidate)s"
            ) % {"candidate": candidate}

        if self.verb == self.Verb.CANDIDATE_RESULT_SNAPSHOT_CREATED:
            return _(
                "Candidate report content was created for %(candidate)s"
            ) % {"candidate": candidate}

        if self.verb == self.Verb.CANDIDATE_RESULT_LINK_OPENED:
            return _("%(candidate)s opened the candidate report") % {
                "candidate": candidate,
            }

        if self.verb == self.Verb.CANDIDATE_RESULT_CODE_VERIFIED:
            return _(
                "%(candidate)s successfully verified the result code"
            ) % {"candidate": candidate}

        if self.verb == self.Verb.CANDIDATE_RESULT_CODE_FAILED:
            return _(
                "%(candidate)s entered an incorrect result code"
            ) % {"candidate": candidate}

        if self.verb == self.Verb.CANDIDATE_RESULT_FEEDBACK_SUBMITTED:
            result_areas = {
                "personality": _("personality"),
                "skills": _("skills"),
                "motivation": _("motivation"),
                "test_experience": _("the test experience"),
            }
            area = result_areas.get(meta.get("result_area"), _("the report"))
            return _(
                "%(candidate)s submitted feedback on %(area)s"
            ) % {
                "candidate": candidate,
                "area": area,
            }

        if self.verb == self.Verb.CANDIDATE_RESULT_CODE_REPLACED:
            return _(
                "%(actor)s replaced %(candidate)s's verification code"
            ) % {
                "actor": actor,
                "candidate": candidate,
            }

        if self.verb == self.Verb.CANDIDATE_RESULT_ACCESS_REVOKED:
            if meta.get("reason") == "sharing_disabled":
                return _(
                    "%(actor)s revoked %(candidate)s's access when sharing was disabled"
                ) % {
                    "actor": actor,
                    "candidate": candidate,
                }
            return _(
                "%(actor)s revoked %(candidate)s's candidate report access"
            ) % {
                "actor": actor,
                "candidate": candidate,
            }

        if self.verb == self.Verb.CANDIDATE_RESULT_ACCESS_EXPIRED:
            return _("Access to %(candidate)s's candidate report expired") % {
                "candidate": candidate,
            }

        if self.verb == self.Verb.ALL_TESTS_COMPLETED:
            return _(
                "%(candidate)s completed all assessments"
            ) % {
                "candidate": candidate,
            }

        if self.verb == self.Verb.STATUS_CHANGED:
            old = meta.get("old_status")
            new = meta.get("new_status")
            activity_name = meta.get("activity_name")
            level = meta.get("level")

            if (
                level == "activity"
                and new == "started"
                and activity_name
            ):
                return _(
                    "%(candidate)s started %(activity_name)s"
                ) % {
                    "candidate": candidate,
                    "activity_name": activity_name,
                }

            if (
                level == "activity"
                and new == "completed"
                and activity_name
            ):
                return _(
                    "%(candidate)s completed %(activity_name)s"
                ) % {
                    "candidate": candidate,
                    "activity_name": activity_name,
                }

            if new == "started":
                return _(
                    "%(candidate)s started the process"
                ) % {
                    "candidate": candidate,
                }

            if new == "completed":
                return _(
                    "%(candidate)s completed the process"
                ) % {
                    "candidate": candidate,
                }

            status_labels = {
                "created": _("Created"),
                "sent": _("Sent"),
                "started": _("Started"),
                "completed": _("Completed"),
                "expired": _("Expired"),
                "failed": _("Failed"),
            }

            old_label = status_labels.get(old, old)
            new_label = status_labels.get(new, new)

            if old and new:
                return _(
                    "%(actor)s updated %(candidate)s: "
                    "%(old_status)s → %(new_status)s"
                ) % {
                    "actor": actor,
                    "candidate": candidate,
                    "old_status": old_label,
                    "new_status": new_label,
                }

            return _(
                "%(actor)s updated %(candidate)s"
            ) % {
                "actor": actor,
                "candidate": candidate,
            }

        return self.get_verb_display()
