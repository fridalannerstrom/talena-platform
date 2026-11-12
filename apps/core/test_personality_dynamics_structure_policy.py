from django.test import SimpleTestCase

from apps.core.ai.personality_dynamics_structure_policy import (
    PROFILE_DYNAMICS_CONTRACT,
    _replace_profile_dynamics_contract,
    normalise_profile_dynamics_event,
)


class PersonalityDynamicsStructurePolicyTests(SimpleTestCase):
    def test_prompt_contract_requires_exactly_two_separate_items(self):
        original = """
2. INTERPRETATION CONTENT
something

3. PROFILE DYNAMICS

Return one profile_dynamics event:

{"type":"profile_dynamics","text":"One paragraph"}

4. MOTIVATION INTERACTION
something else
""".strip()

        result = _replace_profile_dynamics_contract(original)

        self.assertIn(PROFILE_DYNAMICS_CONTRACT, result)
        self.assertIn("exactly 2 separate, substantive personality dynamics", result)
        self.assertIn('"type":"profile_dynamics","items"', result)
        self.assertNotIn('"type":"profile_dynamics","text":"One paragraph"', result)
        self.assertIn("4. MOTIVATION INTERACTION", result)

    def test_two_items_are_joined_as_two_paragraphs_for_existing_consumers(self):
        event = normalise_profile_dynamics_event(
            {
                "type": "profile_dynamics",
                "items": [
                    "First dynamic. It explores one behavioural tension.",
                    "Second dynamic. It explores another behavioural tension.",
                ],
            }
        )

        self.assertEqual(
            event["items"],
            [
                "First dynamic. It explores one behavioural tension.",
                "Second dynamic. It explores another behavioural tension.",
            ],
        )
        self.assertEqual(
            event["text"],
            (
                "First dynamic. It explores one behavioural tension.\n\n"
                "Second dynamic. It explores another behavioural tension."
            ),
        )

    def test_more_than_two_model_items_are_limited_to_product_contract(self):
        event = normalise_profile_dynamics_event(
            {
                "type": "profile_dynamics",
                "items": ["One", "Two", "Three"],
            }
        )

        self.assertEqual(event["items"], ["One", "Two"])
        self.assertEqual(event["text"], "One\n\nTwo")

    def test_blank_items_are_ignored(self):
        event = normalise_profile_dynamics_event(
            {
                "type": "profile_dynamics",
                "items": ["  First  ", "", "  Second  "],
            }
        )

        self.assertEqual(event["items"], ["First", "Second"])
        self.assertEqual(event["text"], "First\n\nSecond")

    def test_legacy_two_paragraph_text_is_recovered_into_items(self):
        event = normalise_profile_dynamics_event(
            {
                "type": "profile_dynamics",
                "text": "First legacy dynamic.\n\nSecond legacy dynamic.",
            }
        )

        self.assertEqual(
            event["items"],
            ["First legacy dynamic.", "Second legacy dynamic."],
        )
        self.assertEqual(
            event["text"],
            "First legacy dynamic.\n\nSecond legacy dynamic.",
        )

    def test_legacy_single_text_remains_backwards_compatible(self):
        event = normalise_profile_dynamics_event(
            {
                "type": "profile_dynamics",
                "text": "Existing saved dynamics text.",
            }
        )

        self.assertEqual(event["text"], "Existing saved dynamics text.")
        self.assertNotIn("items", event)

    def test_other_event_types_are_unchanged(self):
        event = {
            "type": "motivation_interaction",
            "text": "Unchanged",
        }

        self.assertIs(normalise_profile_dynamics_event(event), event)
