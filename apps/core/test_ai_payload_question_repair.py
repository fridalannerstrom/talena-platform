"""#301: verify sanitized final SDK arguments in interview-question JSON repair.

No candidate records, real provider calls or API keys are used. Both the
streamed request and the nonstreaming repair request cross PrivacySafeOpenAI.
"""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.openai_client import PrivacySafeOpenAI


class QuestionRepairPayloadPrivacyTests(SimpleTestCase):
    @staticmethod
    def _owner():
        return SimpleNamespace(candidate=SimpleNamespace(
            first_name="Anna",
            last_name="Svensson",
            email="anna.svensson@example.test",
        ))

    @staticmethod
    def _stream_chunk(text):
        return SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=text))]
        )

    @staticmethod
    def _nonstream_result(text):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
        )

    def _test_repair(self, *, module, func_name, result_key, first_response, repair_response):
        import importlib
        feature = importlib.import_module(module)
        for language in ("sv", "en"):
            with self.subTest(module=module, language=language):
                raw = Mock()
                raw.chat.completions.create.side_effect = [
                    iter([self._stream_chunk(first_response)]),
                    self._nonstream_result(repair_response),
                ]
                owner = self._owner()
                context = {
                    "candidate": owner.candidate,
                    "purpose_label": "Hiring",
                    "context_text": (
                        "Interview with Anna Svensson. "
                        "Contact anna.svensson@example.test. "
                        "STEN 8, Customer Service."
                    ),
                }
                with (
                    patch.object(feature, "get_openai_client",
                                 return_value=PrivacySafeOpenAI(raw)),
                    # Runtime policies wrap the prompt builders and may
                    # require a complete ORM owner. Keep this test scoped
                    # to the final SDK boundary, including the JSON retry.
                    patch.object(
                        feature,
                        ("build_motivation_questions_prompt"
                         if "motivation" in module
                         else "build_cognitive_questions_prompt"),
                        return_value=(
                            "ADMIN GUIDANCE from Eva Andersson. "
                            "Interview with Anna Svensson. "
                            "anna.svensson@example.test. "
                            "Contact 070-123 45 67. "
                            "STEN 8, Customer Service."
                        ),
                    ),
                    patch.object(feature, "get_ai_language_instruction",
                                 return_value="Use the requested language."),
                    patch.object(feature, "get_ai_system_language_instruction",
                                 return_value="Use the requested language."),
                    patch.object(feature, result_key,
                                 return_value=(
                                     "STEN 8, Customer Service; "
                                     "contact 070-123 45 67"
                                 )),
                ):
                    events = list(getattr(feature, func_name)(
                        owner=owner,
                        **{
                            ("motivation_results" if "motivation" in module
                             else "cognitive_results"): [
                                {"name": "Customer Service", "score": 8}
                            ]
                        },
                        language_code=language,
                    ))

                self.assertEqual(raw.chat.completions.create.call_count, 2)
                requests = raw.chat.completions.create.call_args_list
                self.assertTrue(requests[0].kwargs["stream"])
                self.assertFalse(requests[1].kwargs["stream"])
                for attempt in requests:
                    sent = json.dumps(
                        attempt.kwargs["messages"], ensure_ascii=False
                    )
                    for secret in (
                        "Anna Svensson",
                        "anna.svensson@example.test",
                        "Eva Andersson",
                        "070-123 45 67",
                    ):
                        self.assertNotIn(secret, sent)
                    self.assertIn("STEN 8", sent)
                    self.assertIn("Customer Service", sent)
                    self.assertIn("ADMIN GUIDANCE", sent)
                self.assertIn("questions", [e["type"] for e in events])
                self.assertEqual(events[-1]["type"], "done")

    def test_motivation_stream_and_json_repair_are_both_sanitized(self):
        response = json.dumps({
            "title": "Motivation",
            "label": "Questions",
            "questions": [{
                "question": f"What motivates you in example {i}?",
                "why": "Follow up the evidence.",
                "listen_for": "A concrete example.",
            } for i in range(3)],
            "context_note": "",
        })
        self._test_repair(
            module="apps.core.ai.motivation_questions",
            func_name="stream_motivation_questions",
            result_key="build_motivation_evidence_text",
            first_response="not a JSON response",
            repair_response=response,
        )

    def test_cognitive_stream_and_json_repair_are_both_sanitized(self):
        response = json.dumps({
            "type": "questions",
            "items": [{
                "question": f"How do you evaluate complex task {i}?",
                "why": "Understand the reasoning approach.",
                "listen_for": "A practical example.",
            } for i in range(3)],
        })
        self._test_repair(
            module="apps.core.ai.cognitive_questions",
            func_name="stream_cognitive_questions",
            result_key="build_cognitive_evidence_text",
            first_response='{"type":"meta","title":"Synthetic","label":"Questions"}\n',
            repair_response=response,
        )
