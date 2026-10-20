"""Synthetic, local-only NER benchmark. No real Talena candidate data."""

import json
import os
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.core.ai.pii_sanitizer import _local_ner, sanitize_ai_text

CASES = {
    "sv": [
        ("Helena förklarade hur hon ledde ett nytt team.", "Helena"),
        ("Nils gav flera exempel från tidigare projekt.", "Nils"),
        ("Märta beskrev samarbete med sina kollegor.", "Märta"),
        ("Under intervjun berättade Sofia om konflikthantering.", "Sofia"),
        ("Karin uppgav att rollen kräver hög flexibilitet.", "Karin"),
        ("Vi frågade Erik hur han prioriterar.", "Erik"),
        ("Anna Svensson fick STEN 8 på Adaptability.", "Anna Svensson"),
        ("Oskar Nilsson fick STIVE 4 på Customer Service.", "Oskar Nilsson"),
        ("Intervjusvaret från Elin Karlsson handlade om teamwork.", "Elin Karlsson"),
        ("Enligt Josefin Lundström är tydlighet avgörande.", "Josefin Lundström"),
    ],
    "en": [
        ("Eleanor described how she supported colleagues.", "Eleanor"),
        ("During the interview, Oliver discussed teamwork.", "Oliver"),
        ("Sarah explained her leadership style.", "Sarah"),
        ("The interviewer asked Michael about feedback.", "Michael"),
        ("We spoke with Catherine about accountability.", "Catherine"),
        ("James outlined his preferred work environment.", "James"),
        ("John Smith received STEN 8 for Adaptability.", "John Smith"),
        ("Emily Carter had STIVE 4 for Customer Service.", "Emily Carter"),
        ("The candidate Hannah Wilson discussed conflict.", "Hannah Wilson"),
        ("According to Rebecca Thompson, trust is essential.", "Rebecca Thompson"),
    ],
}
PRESERVE = {
    "sv": [
        "Personlighet: STEN 8. Motivation: STIVE 4. Talena.",
        "Customer Service, People Development och Social Desirability.",
        'Resultat: {"sten_rounded": 8, "percentile": 62}.',
        "Ideal arbetsmiljö. Arbete under press. Interaktion och känslohantering.",
    ],
    "en": [
        "STEN 7, STIVE 4, and the 62nd percentile.",
        "Customer Service and People Development are motivators.",
        "Talent Qode uses the Sova assessment engine.",
        'Results: {"sten_rounded": 8, "score": 3.5}.',
    ],
}


def sanitized(text, sv_model, en_model):
    with patch.dict(os.environ, {
        "TALENA_PII_NER_SV_MODEL": sv_model,
        "TALENA_PII_NER_EN_MODEL": en_model,
    }):
        return sanitize_ai_text(text)


def main():
    sv = os.environ.get("TALENA_PII_NER_SV_MODEL", "").strip()
    en = os.environ.get("TALENA_PII_NER_EN_MODEL", "").strip()
    if not sv or not en:
        raise RuntimeError("Install and configure both local NER models.")

    report = {}
    for language, name in (("sv", sv), ("en", en)):
        model = _local_ner(name)
        model_hits = regex_hits = total_hits = 0
        times = []
        for text, person in CASES[language]:
            start = time.perf_counter()
            clean = sanitized(text, name if language == "sv" else "",
                              name if language == "en" else "")
            times.append((time.perf_counter() - start) * 1000)
            total_hits += person.casefold() not in clean.casefold()
            regex_only = sanitized(text, "", "")
            regex_hits += person.casefold() not in regex_only.casefold()

            doc = model(text)
            begin = text.index(person)
            end = begin + len(person)
            model_hits += any(
                e.label_.upper() in {"PRS", "PER", "PERSON"}
                and e.start_char < end and e.end_char > begin
                for e in doc.ents
            )
        preserved = sum(
            phrase == sanitized(phrase,
                                name if language == "sv" else "",
                                name if language == "en" else "")
            for phrase in PRESERVE[language]
        )
        report[language] = {
            "model": name,
            "version": model.meta.get("version", "unknown"),
            "cases": len(CASES[language]),
            "person_hits_by_ner": model_hits,
            "person_hits_regex_only": regex_hits,
            "person_hits_combined": total_hits,
            "unmodified_context_cases": preserved,
            "context_cases": len(PRESERVE[language]),
            "median_latency_ms": round(statistics.median(times), 1),
        }
    report["status"] = (
        "EXPERIMENTAL. Synthetic benchmark only. Not production approval."
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as f:
            f.write("## Synthetic NER evaluation\n\n")
            f.write(json.dumps(report, ensure_ascii=False, indent=2))
            f.write("\n")


if __name__ == "__main__":
    main()
