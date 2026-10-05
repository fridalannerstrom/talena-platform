from django.test import SimpleTestCase

from apps.core.motivation_factor_names import MOTIVATION_FACTOR_NAMES_SV
from apps.processes.templatetags.motivation_i18n import motivation_name_sv


EXPECTED_SWEDISH_MOTIVATION_NAMES = {
    "attachment": "Anknytning",
    "customer_service": "Kundservice",
    "work_life_balance": "Work life Balance",
    "people_development": "Människors utveckling",
    "stability": "Stabilitet",
    "authority": "Auktoritet",
    "acquisition": "Anskaffning",
    "independence": "Självständighet",
    "recognition": "Erkännande",
    "making_a_difference": "Göra skillnad",
    "achievement": "Prestation",
    "quality": "Kvalitet",
    "learning": "Lärande",
    "ethics": "Etik",
    "commercial_focus": "Kommersiellt Fokus",
    "curiosity": "Nyfikenhet",
    "creativity": "Kreativitet",
    "enjoyment": "Glädje",
    "variety": "Variation",
    "risk": "Risk",
}


class MotivationFactorNameTests(SimpleTestCase):
    def test_labels_match_the_approved_swedish_display_names(self):
        self.assertEqual(MOTIVATION_FACTOR_NAMES_SV, EXPECTED_SWEDISH_MOTIVATION_NAMES)

    def test_result_view_uses_canonical_swedish_labels(self):
        self.assertEqual(
            motivation_name_sv({"key": "work_life_balance", "name": "Work life Balance"}),
            "Balans mellan arbete och privatliv",
        )
        self.assertEqual(
            motivation_name_sv({"key": "quality", "name": "Kvalité"}),
            "Kvalitet",
        )
        self.assertEqual(
            motivation_name_sv({"key": "commercial_focus", "name": "Commercial Focus"}),
            "Kommersiellt Fokus",
        )
