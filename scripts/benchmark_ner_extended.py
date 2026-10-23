"""Expanded, purely synthetic local-NER QA for Talena #300.

No real candidate data, external inference calls or raw text in test reports.
This is a research benchmark, NOT a guarantee of anonymisation.
"""

import json
import os
import resource
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.core.ai.pii_sanitizer import _local_ner, sanitize_ai_text

# Realistic but fictional short interviews, including first names and
# unusual / hyphenated names. Each case has an opaque report identifier.
PEOPLE = {
    "sv": [
        ("sv01", "Linnea resonerade kring samarbete.", "Linnea"),
        ("sv02", "Vi bad Amina beskriva en svår prioritering.", "Amina"),
        ("sv03", "Samtalet med Abdi handlade om ledarskap.", "Abdi"),
        ("sv04", "Åsa beskrev en pressad arbetssituation.", "Åsa"),
        ("sv05", "Ebbe gav ett exempel på återkoppling.", "Ebbe"),
        ("sv06", "Sara-Li talade om konflikthantering.", "Sara-Li"),
        ("sv07", "Anna-Lena Björk berättade om rollen.", "Anna-Lena Björk"),
        ("sv08", "Intervjuaren talade med Omar Al-Hassan.", "Omar Al-Hassan"),
        ("sv09", "Josefin Lundström fick STEN 8 på Adaptability.", "Josefin Lundström"),
        ("sv10", "Märta förklarade att tydlighet var viktigt.", "Märta"),
        ("sv11", "Enligt Farah är teamets trivsel viktig.", "Farah"),
        ("sv12", "Jag följde upp ett tidigare svar med Joakim.", "Joakim"),
        ("sv13", "Samira talade om förväntningar på rollen.", "Samira"),
        ("sv14", "Nils fick STIVE 4 på Customer Service.", "Nils"),
        ("sv15", "Helena beskrev hur hon organiserar arbetet.", "Helena"),
        ("sv16", "Elin svarade på en följdfråga.", "Elin"),
    ],
    "en": [
        ("en01", "Priya discussed collaboration under pressure.", "Priya"),
        ("en02", "Jordan explained their preferred work setting.", "Jordan"),
        ("en03", "Kai discussed feedback from a manager.", "Kai"),
        ("en04", "Amelia described resolving conflict.", "Amelia"),
        ("en05", "Noah spoke about planning and prioritisation.", "Noah"),
        ("en06", "The recruiter asked Samira about deadlines.", "Samira"),
        ("en07", "Chloe explained her approach to delegation.", "Chloe"),
        ("en08", "Oliver described an unusual team project.", "Oliver"),
        ("en09", "Ana Maria Torres described a past role.", "Ana Maria Torres"),
        ("en10", "We asked Michael O'Brien about motivation.", "Michael O'Brien"),
        ("en11", "Rebecca Thompson received STEN 8 in Adaptability.", "Rebecca Thompson"),
        ("en12", "Eleanor described her leadership style.", "Eleanor"),
        ("en13", "Alex discussed team productivity.", "Alex"),
        ("en14", "The interviewer asked Fatima to elaborate.", "Fatima"),
        ("en15", "According to James, feedback should be timely.", "James"),
        ("en16", "We followed up with Catherine.", "Catherine"),
    ],
}
MIXED = [
    ("mix01", "After the interview, Märta discussed feedback.", "Märta"),
    ("mix02", "Yesterday, Eleanor beskrev sin arbetsmiljö.", "Eleanor"),
    ("mix03", "Vi intervjuade Priya om Customer Service.", "Priya"),
    ("mix04", "Samira described hur hon prioriterar under press.", "Samira"),
]
CONTEXT = [
    ("ctx01", "STEN 8 och STIVE 4. Personlighet: Adaptability."),
    ("ctx02", "Social Desirability. People Development. Customer Service."),
    ("ctx03", "Talent Qode. Talena. Sova Assessments. OpenAI."),
    ("ctx04", 'Resultat: {"sten_rounded": 8, "percentile": 62}.'),
    ("ctx05", "Leda och samarbeta med andra. Organisering och tankestil."),
    ("ctx06", "Samspel och känslomässig hantering. Motivation: STIVE 4."),
    ("ctx07", "Candidate Insights. Interview Summary. Social Desirability."),
    ("ctx08", 'Results: {"sten_rounded": 8, "score": 3.5}.'),
    ("ctx09", "Intervjusammanfattning och helhetsbild. STEN 7."),
    ("ctx10", "The candidate has STEN 8 and STIVE 4; no names included."),
]


def sanitize(text, sv, en):
    with patch.dict(os.environ, {
        "TALENA_PII_NER_SV_MODEL": sv,
        "TALENA_PII_NER_EN_MODEL": en,
        "TALENA_PII_MASK_ORGANIZATIONS": "0",
        "TALENA_PII_MASK_LOCATIONS": "0",
    }):
        return sanitize_ai_text(text)


def evaluate_people(cases, sv, en, model):
    report = {"cases": len(cases), "ner_hits": 0, "regex_hits": 0,
              "combined_hits": 0, "ner_miss_ids": [], "combined_miss_ids": []}
    for case_id, sentence, person in cases:
        begin = sentence.index(person)
        end = begin + len(person)
        hit = any(
            str(e.label_).upper() in {"PERSON", "PER", "PRS"}
            and e.start_char < end and e.end_char > begin
            for e in model(sentence).ents
        )
        regex_hit = person.casefold() not in sanitize(sentence, "", "").casefold()
        combined_hit = person.casefold() not in sanitize(sentence, sv, en).casefold()
        report["ner_hits"] += bool(hit)
        report["regex_hits"] += bool(regex_hit)
        report["combined_hits"] += bool(combined_hit)
        if not hit:
            report["ner_miss_ids"].append(case_id)
        if not combined_hit:
            report["combined_miss_ids"].append(case_id)
    return report


def main():
    sv, en = (os.environ.get(k, "").strip() for k in (
        "TALENA_PII_NER_SV_MODEL", "TALENA_PII_NER_EN_MODEL"))
    if not sv or not en:
        raise RuntimeError("Both locally installed NER models are required")
    start = time.perf_counter()
    sv_model, en_model = _local_ner(sv), _local_ner(en)
    startup_ms = round((time.perf_counter() - start) * 1000, 2)

    person = {
        "sv": evaluate_people(PEOPLE["sv"], sv, "", sv_model),
        "en": evaluate_people(PEOPLE["en"], "", en, en_model),
    }
    mixed_missed = [
        ident for ident, sentence, name in MIXED
        if name.casefold() in sanitize(sentence, sv, en).casefold()
    ]
    changed_context = [
        ident for ident, sentence in CONTEXT
        if sanitize(sentence, sv, en) != sentence
    ]

    sv_context = (
        "Personlighet: STEN 8. Motivation: STIVE 4. "
        "Social Desirability och Customer Service är testbegrepp. "
        "Intervjun handlar om samarbete, prioriteringar och återkoppling. "
    )
    en_context = (
        "Personality: STEN 7. People Development and Customer Service "
        "are assessment labels. Interview evidence concerns planning. "
    )
    long_tests = {}
    for repeat in (20, 80):
        source = ((sv_context + en_context) * repeat
                  + " Anna Svensson spoke with John Smith. "
                  + "Mejl anna.svensson@example.se och telefon 070-123 45 67. "
                  + "Personnummer 19900101-1234. Call +1 415 555 2671.")
        started = time.perf_counter()
        clean = sanitize(source, sv, en)
        ms = round((time.perf_counter() - started) * 1000, 2)
        direct = ("anna.svensson@example.se", "070-123 45 67",
                  "19900101-1234", "+1 415 555 2671")
        required = ("STEN 8", "STIVE 4", "Social Desirability",
                    "Customer Service", "[EMAIL]", "[PHONE]", "[PERSONAL_ID]")
        long_tests[str(repeat)] = {
            "characters": len(source), "latency_ms": ms,
            "direct_id_leak_case_ids": [
                i + 1 for i, marker in enumerate(direct) if marker in clean
            ],
            "missing_context_or_placeholder": [
                marker for marker in required if marker not in clean
            ],
        }

    short_ms = []
    for _, sentence, _ in PEOPLE["sv"] + PEOPLE["en"]:
        start = time.perf_counter()
        sanitize(sentence, sv, en)
        short_ms.append((time.perf_counter() - start) * 1000)
    short_ms.sort()
    report = {
        "status": "SYNTHETIC RESEARCH ONLY; NOT PRODUCTION APPROVAL",
        "models": {
            "sv": {"name": sv, "version": sv_model.meta.get("version")},
            "en": {"name": en, "version": en_model.meta.get("version")},
        },
        "load_both_models_ms": startup_ms,
        "people": person,
        "mixed": {"cases": len(MIXED), "miss_ids": mixed_missed},
        "context": {"cases": len(CONTEXT), "changed_ids": changed_context},
        "long_texts": long_tests,
        "short_ms_median": round(statistics.median(short_ms), 2),
        "short_ms_p95": round(short_ms[int(.95 * (len(short_ms) - 1))], 2),
        "ci_process_peak_rss_mib": round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "limitations": (
            "Purpose-built examples, not representative precision/recall; "
            "CI memory and latency are not Azure production measurements."
        ),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as f:
            f.write("Extended synthetic local NER evaluation (#300)\n\n")
            f.write(json.dumps(report, indent=2, ensure_ascii=False))
            f.write("\n")

    # Only hard safety/context regressions fail CI. Statistical name misses
    # are documented for human review rather than hidden by a green check.
    if changed_context or any(
        row["direct_id_leak_case_ids"] or row["missing_context_or_placeholder"]
        for row in long_tests.values()
    ):
        raise SystemExit("Synthetic sanitizer regression: inspect case IDs")


if __name__ == "__main__":
    main()
