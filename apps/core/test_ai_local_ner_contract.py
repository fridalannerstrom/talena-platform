"""Local NER compatibility tests. Do not require spaCy or model downloads."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.pii_sanitizer import (
    PrivacySanitizationError,
    _local_ner,
    sanitize_ai_text,
)


class LocalNERModelContractTests(SimpleTestCase):
    def setUp(self):
        _local_ner.cache_clear()

    def tearDown(self):
        _local_ner.cache_clear()

    def fake_spacy(self, model=None, *, error=None):
        loader = Mock(side_effect=error) if error else Mock(return_value=model)
        return patch.dict(sys.modules, {"spacy": SimpleNamespace(load=loader)})

    def test_swedish_spacy_prs_label_masks_single_first_name(self):
        sentence = "Intervjuaren talade med Märta om arbetsuppgifterna."
        person = "Märta"
        model = Mock()
        model.pipe_names = ["tok2vec", "ner"]
        model.get_pipe.return_value.labels = ("PRS", "ORG", "LOC")
        model.return_value = SimpleNamespace(ents=[
            SimpleNamespace(
                label_="PRS",
                start_char=sentence.index(person),
                end_char=sentence.index(person) + len(person),
            )
        ])
        with (
            self.fake_spacy(model),
            patch.dict("os.environ", {
                "TALENA_PII_NER_SV_MODEL": "sv_core_news_sm",
                "TALENA_PII_NER_EN_MODEL": "",
            }),
        ):
            output = sanitize_ai_text(sentence)
        self.assertNotIn(person, output)
        self.assertIn("[PERSON]", output)

    def test_english_spacy_person_label_masks_single_first_name(self):
        sentence = "Yesterday, Eleanor presented the interview findings."
        model = Mock()
        model.pipe_names = ["tok2vec", "ner"]
        model.get_pipe.return_value.labels = ("PERSON", "GPE", "ORG")
        model.return_value = SimpleNamespace(ents=[
            SimpleNamespace(
                label_="PERSON",
                start_char=sentence.index("Eleanor"),
                end_char=sentence.index("Eleanor") + len("Eleanor"),
            )
        ])
        with (
            self.fake_spacy(model),
            patch.dict("os.environ", {
                "TALENA_PII_NER_SV_MODEL": "",
                "TALENA_PII_NER_EN_MODEL": "en_core_web_sm",
            }),
        ):
            output = sanitize_ai_text(sentence)
        self.assertNotIn("Eleanor", output)
        self.assertIn("[PERSON]", output)

    def test_false_positive_person_labels_cannot_erase_assessment_schema(self):
        sentence = (
            'Social Desirability. Talent Qode. Resultat: '
            '{"sten_rounded": 8}. Helena described her role.'
        )
        model = Mock()
        model.pipe_names = ["tok2vec", "ner"]
        model.get_pipe.return_value.labels = ("PRS", "ORG", "LOC")
        entities = ("Social Desirability", "Qode", "Resultat",
                    "sten_rounded", "Helena")
        model.return_value = SimpleNamespace(ents=[
            SimpleNamespace(
                label_="PRS",
                start_char=sentence.index(word),
                end_char=sentence.index(word) + len(word),
            )
            for word in entities
        ])
        with (
            self.fake_spacy(model),
            patch.dict("os.environ", {
                "TALENA_PII_NER_SV_MODEL": "sv_core_news_sm",
                "TALENA_PII_NER_EN_MODEL": "",
            }),
        ):
            clean = sanitize_ai_text(sentence)

        for expected in ("Social Desirability", "Talent Qode", "Resultat:",
                         '"sten_rounded": 8'):
            self.assertIn(expected, clean)
        self.assertNotIn("Helena", clean)
        self.assertIn("[PERSON]", clean)

    def test_assessment_theme_headings_are_not_masked_as_people(self):
        sentence = (
            "Leda och samarbeta med andra. Organisering och tankestil. "
            "Samspel och känslomässig hantering. "
            "Helena berättade om arbetsuppgifterna."
        )
        labels = ("Leda", "Organisering", "Samspel", "Helena")
        model = Mock()
        model.pipe_names = ["ner"]
        model.get_pipe.return_value.labels = ("PRS", "ORG")
        model.return_value = SimpleNamespace(ents=[
            SimpleNamespace(
                label_="PRS",
                start_char=sentence.index(token),
                end_char=sentence.index(token) + len(token),
            )
            for token in labels
        ])
        with (
            self.fake_spacy(model),
            patch.dict("os.environ", {
                "TALENA_PII_NER_SV_MODEL": "sv_core_news_sm",
                "TALENA_PII_NER_EN_MODEL": "",
            }),
        ):
            clean = sanitize_ai_text(sentence)

        self.assertEqual(clean, sentence.replace("Helena", "[PERSON]"))

    def test_model_with_no_ner_fails_closed(self):
        model = Mock()
        model.pipe_names = ["tagger", "parser"]
        with self.fake_spacy(model), self.assertRaises(PrivacySanitizationError):
            _local_ner("pipeline-without-ner")
        self.assertEqual(_local_ner.cache_info().currsize, 0)

    def test_model_without_person_label_fails_closed(self):
        model = Mock()
        model.pipe_names = ["ner"]
        model.get_pipe.return_value.labels = ("ORG", "LOC")
        with self.fake_spacy(model), self.assertRaises(PrivacySanitizationError):
            _local_ner("ner-without-people")
        self.assertEqual(_local_ner.cache_info().currsize, 0)

    def test_model_exception_message_is_not_exposed(self):
        with (
            self.fake_spacy(error=OSError("Sensitive local filesystem path")),
            self.assertRaises(PrivacySanitizationError) as raised,
        ):
            _local_ner("not-installed")
        self.assertNotIn("Sensitive", str(raised.exception))
