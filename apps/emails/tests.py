from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.emails.utils import (
    SWEDISH_DEFAULT_INVITATION_BODY,
    ENGLISH_DEFAULT_INVITATION_BODY,
    get_default_invitation_template,
    render_placeholders,
    upgrade_legacy_default_invitation_template,
)


class CandidateInvitationCopyTests(SimpleTestCase):
    def test_swedish_default_is_the_new_tq_copy_with_an_assessment_link(self):
        template = get_default_invitation_template("sv")
        self.assertEqual(template["body"], SWEDISH_DEFAULT_INVITATION_BODY)
        self.assertEqual(
            template["body"],
            (
                "Hej {first_name},\n\n"
                "Du har blivit inbjuden att genomföra TQ:s tester.\n\n"
                "Testerna är ett sätt att få en bättre förståelse för dina "
                "personliga förutsättningar och kan bidra med värdefulla "
                "insikter som en del av en större helhetsbild.\n\n"
                "När du klickar på länken nedan kommer du till testmiljön, "
                "där du får mer information om vilka tester du ska genomföra, "
                "hur de går till och vad som kan vara bra att tänka på "
                "innan du börjar.\n\n"
                "Ta gärna dig tid att läsa igenom instruktionerna i lugn "
                "och ro innan du sätter igång.\n\n"
                "{assessment_url}"
            ),
        )
        rendered = render_placeholders(
            template["body"],
            {"first_name": "Anna", "assessment_url": "https://example.com/test"},
        )
        self.assertIn("Hej Anna,", rendered)
        self.assertTrue(rendered.endswith("https://example.com/test"))
        self.assertNotIn("{sender_full_name}", rendered)

    def test_english_default_matches_the_full_candidate_invitation_copy(self):
        body = get_default_invitation_template("en")["body"]
        self.assertEqual(body, ENGLISH_DEFAULT_INVITATION_BODY)
        self.assertIn("You have been invited to complete TQ's assessments.", body)
        self.assertTrue(body.endswith("{assessment_url}"))

    def test_saved_old_swedish_default_is_upgraded(self):
        old_body = (
            "Hej {first_name},\n\n"
            "Du har blivit inbjuden att genomföra tester.\n\n"
            "Klicka på länken nedan för att börja:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "{sender_full_name}"
        )
        template = SimpleNamespace(
            subject="Inbjudan till testprocess",
            body=old_body,
            language="sv",
            save=Mock(),
        )
        self.assertTrue(upgrade_legacy_default_invitation_template(template))
        self.assertEqual(template.body, SWEDISH_DEFAULT_INVITATION_BODY)
        template.save.assert_called_once_with(
            update_fields=["subject", "body", "updated_at"]
        )

    def test_custom_saved_invitation_is_not_overwritten(self):
        template = SimpleNamespace(
            subject="Inbjudan till testprocess",
            body="Hej {first_name}, välkommen! {assessment_url}",
            language="sv",
            save=Mock(),
        )
        self.assertFalse(upgrade_legacy_default_invitation_template(template))
        self.assertEqual(
            template.body,
            "Hej {first_name}, välkommen! {assessment_url}",
        )
        template.save.assert_not_called()
