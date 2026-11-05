"""Normalize project terminology in activity event choices.

This migration existed in a local development database before #432.
Include it in the tracked graph so databases agree on the migration lineage.
Only alters Django choice metadata; it does not change stored event rows.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0006_candidate_result_access_events"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activityevent",
            name="verb",
            field=models.CharField(
                choices=[
                    ("process_created", "Process skapad"),
                    ("process_archived", "Process arkiverad"),
                    ("process_deleted", "Process raderad"),
                    ("candidate_added", "Kandidat lades till i projekt"),
                    ("candidate_removed", "Kandidat togs bort från projekt"),
                    ("invite_sent", "Testinbjudan skickad"),
                    ("test_started", "Test påbörjat"),
                    ("test_completed", "Test slutfört"),
                    ("all_tests_completed", "Alla tester slutförda"),
                    (
                        "candidate_result_email_sent",
                        "Kandidatresultat skickat",
                    ),
                    (
                        "candidate_result_email_failed",
                        "Kandidatresultat kunde inte skickas",
                    ),
                    (
                        "candidate_result_snapshot_created",
                        "Kandidatrapport skapad",
                    ),
                    (
                        "candidate_result_link_opened",
                        "Kandidatrapport öppnad",
                    ),
                    (
                        "candidate_result_code_verified",
                        "Verifieringskod godkänd",
                    ),
                    (
                        "candidate_result_code_failed",
                        "Felaktig verifieringskod",
                    ),
                    (
                        "candidate_result_feedback_submitted",
                        "Kandidatfeedback inskickad",
                    ),
                    (
                        "candidate_result_code_replaced",
                        "Verifieringskod ersatt",
                    ),
                    (
                        "candidate_result_access_revoked",
                        "Kandidatåtkomst återkallad",
                    ),
                    (
                        "candidate_result_access_expired",
                        "Kandidatåtkomst utgången",
                    ),
                    ("status_changed", "Status ändrad"),
                    ("company_created", "Företag skapat"),
                    ("company_updated", "Företag uppdaterat"),
                    ("company_deleted", "Företag raderat"),
                    ("company_member_invited", "Användare inbjuden"),
                    ("company_member_added", "Användare tillagd"),
                    ("company_member_removed", "Användare borttagen"),
                    (
                        "company_member_role_updated",
                        "Användarroll uppdaterad",
                    ),
                    ("company_invite_accepted", "Inbjudan accepterad"),
                    ("orgunit_created", "Konto/enhet skapad"),
                    ("orgunit_updated", "Konto/enhet uppdaterad"),
                    ("orgunit_moved", "Konto/enhet flyttad"),
                    ("orgunit_deleted", "Konto/enhet raderad"),
                    ("user_access_updated", "Användaråtkomst uppdaterad"),
                    ("user_logged_in", "Användare loggade in"),
                ],
                max_length=80,
            ),
        ),
    ]
