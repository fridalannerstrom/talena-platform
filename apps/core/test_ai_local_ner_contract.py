"""Local spaCy NER compatibility and fail-closed tests. No models required."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.pii_sanitizer import (
    PrivacySanitizationError,
    _local_ner,
    sanitize_ai_text,
)


class LocalNERModelContractTests(SimpleTestCase):
    def tearDown(self):
        _local_ner.cache_clear()

    @patch("spacy.load")
    def test_swedish_person_label_prs_is_recognized(self, load):
        model = load.return_value
        model.pipe_names = ["tok2vec", "ner"]
        model.get_pipe.return_value.labels = ("PRS", "ORG", "LOC")
        content = "Intervjuaren talade med Märta om arbetsuppgifterna."
        person = "Märta"
        model.return_value = SimpleNamespace(
            ents=[
                SimpleNamespace(
                    label_="PRS",
                    start_char=content.index(person),
                    end_char=content.index(person) + len(person),
                )
            ]
        )
        with patch.dict(
            "os.environ",
            {
                "TALENA_PII_NER_SV_MODEL": "sv_core_news_sm",
                "TALENA_PII_NER_EN_MODEL": "",
            },
        ):
            result = sanitize_ai_text(content)
        self.assertNotIn(person, result)
        self.assertIn("[PERSON]", result)
        load.assert_called_once_with("sv_core_news_sm")

    @patch("spacy.load")
    def test_english_person_label_is_recognized(self, load):
        model = load.return_value
        model.pipe_names = ["tok2vec", "ner"]
        model.get_pipe.return_value.labels = ("PERSON", "GPE", "ORG")
        sentence = "Yesterday, Eleanor presented the interview findings."
        model.return_value = SimpleNamespace(
            ents=[SimpleNamespace(
                label_="PERSON",
                start_char=sentence.index("Eleanor"),
                end_char=sentence.index("Eleanor") + len("Eleanor"),
            )]
        )
        with patch.dict(
            "os.environ",
            {
                "TALENA_PII_NER_SV_MODEL": "",
                "TALENA_PII_NER_EN_MODEL": "en_core_web_sm",
            },
        ):
            result = sanitize_ai_text(sentence)
        self.assertNotIn("Eleanor", result)
        self.assertIn("[PERSON]", result)

    @patch("spacy.load")
    def test_pipeline_missing_ner_fails_closed(self, load):
        load.return_value.pipe_names = ["tagger", "parser"]
        with self.assertRaises(PrivacySanitizationError):
            _local_ner("sv_core_news_sm")
        self.assertEqual(_local_ner.cache_info().currsize, 0)

    @patch("spacy.load")
    def test_pipeline_without_person_labels_fails_closed(self, load):
        load.return_value.pipe_names = ["ner"]
        load.return_value.get_pipe.return_value.labels = ("ORG", "LOC")
        with self.assertRaises(PrivacySanitizationError):
            _local_ner("model-without-people")
        self.assertEqual(_local_ner.cache_info().currsize, 0)

    @patch("spacy.load", side_effect=OSError("Sensitive path in exception"))
    def test_model_load_error_does_not_expose_raw_exception(self, load):
        with self.assertRaises(PrivacySanitizationError) as raised:
            _local_ner("unavailable-ner")
        self.assertNotIn("Sensitive path", str(raised.exception))
