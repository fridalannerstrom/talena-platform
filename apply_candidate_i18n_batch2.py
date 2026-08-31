#!/usr/bin/env python3
"""Synchronise the newest Swedish candidate-workspace translations.

The candidate UI already uses Django i18n tags, but newer msgids can exist in
source before the Swedish catalogue has been refreshed. This script upserts the
translations and compiles ``django.mo`` with Babel, so it works without the
external GNU gettext tooling.

Run from the repository root:

    python apply_candidate_i18n_batch2.py --check
    python apply_candidate_i18n_batch2.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from babel.messages import mofile, pofile


TRANSLATIONS: dict[str, str] = {
    # Candidate insights navigation and workspace
    "Candidate insight areas": "Områden för kandidatinsikter",
    "Prepare for interview": "Förbered inför intervju",
    "After interview": "Efter intervju",
    "Improve candidate insights": "Förbättra kandidatinsikterna",
    "context": "kontext",
    "Add context": "Lägg till kontext",
    "Add": "Lägg till",
    "Add context to make the candidate insights more relevant to this process.": "Lägg till kontext för att göra kandidatinsikterna mer relevanta för den här processen.",
    "No results yet": "Inga resultat ännu",
    "Candidate insights will appear here when assessment data becomes available.": "Kandidatinsikterna visas här när testdata finns tillgänglig.",
    "Reports": "Rapporter",
    "available": "tillgängliga",
    "Uploaded historical assessment report": "Uppladdad historisk testrapport",
    "Open report": "Öppna rapport",
    "No historical reports have been uploaded.": "Inga historiska rapporter har laddats upp.",
    "No assessment reports are currently available.": "Inga testrapporter är tillgängliga just nu.",

    # Candidate directory
    "Candidates": "Kandidater",
    "All candidates": "Alla kandidater",
    "All candidates you have access to across test processes and historical imports.": "Alla kandidater du har tillgång till från testprocesser och historiska importer.",
    "Search candidates...": "Sök kandidater...",
    "Search candidates": "Sök kandidater",
    "Filter candidates by team": "Filtrera kandidater efter team",
    "All teams": "Alla team",
    "No team": "Inget team",
    "Clear filter": "Rensa filter",
    "Candidate": "Kandidat",
    "Teams": "Team",
    "Processes": "Processer",
    "Assessments": "Tester",
    "Latest activity": "Senaste aktivitet",
    "Actions": "Åtgärder",
    "Sent or started": "Skickat eller påbörjat",
    "Not sent": "Inte skickat",
    "View": "Visa",
    "No candidates found.": "Inga kandidater hittades.",

    # Prepare for interview
    "Use the assessment evidence to prepare the conversation and focus the interview on areas that are useful to explore further.": "Använd testunderlaget för att förbereda samtalet och fokusera intervjun på områden som är relevanta att utforska vidare.",
    "Needs update": "Behöver uppdateras",
    "Generate updated decision support": "Generera uppdaterat beslutsstöd",
    "The process information has changed": "Processinformationen har ändrats",
    "This interview preparation was created using an earlier purpose or process context. Generate an updated version before relying on it.": "Den här intervjuförberedelsen skapades med ett tidigare syfte eller en tidigare processkontext. Generera en uppdaterad version innan du använder den som underlag.",
    "Combining the available evidence and preparing the interview…": "Sammanställer tillgängligt underlag och förbereder intervjun…",
    "The interview preparation could not be generated.": "Intervjuförberedelsen kunde inte genereras.",
    "Prepare the interview": "Förbered intervjun",
    "Generate an overall synthesis and practical guidance before reviewing the candidate-specific interview questions.": "Generera en övergripande sammanställning och praktisk vägledning innan du går igenom de kandidatspecifika intervjufrågorna.",
    "Generate interview preparation": "Generera intervjuförberedelse",
    "Overall synthesis": "Övergripande sammanställning",
    "AI-generated insight": "AI-genererad insikt",
    "How to approach the conversation": "Hur du kan lägga upp samtalet",
    "Practical interview guidance based on how the candidate used the personality questionnaire response scale.": "Praktisk intervjuguide baserad på hur kandidaten använde svarsskalan i personlighetsformuläret.",
    "Recommended approach": "Rekommenderat förhållningssätt",
    "Questions to explore": "Frågor att utforska",
    "Response-style interview guidance is not available yet.": "Intervjuvägledning baserad på svarsstil är inte tillgänglig ännu.",

    # After interview and saved notes
    "Save interview evidence and compare it with the assessment indications to add context, nuance and remaining areas for exploration.": "Spara intervjuunderlag och jämför det med indikationerna från testerna för att tillföra kontext, nyanser och kvarstående områden att utforska.",
    "Interview notes and candidate examples": "Intervjuanteckningar och exempel från kandidaten",
    "Include relevant examples, working methods, context and answers that may support, challenge or add nuance to the assessment profile.": "Inkludera relevanta exempel, arbetssätt, kontext och svar som kan stödja, utmana eller nyansera testprofilen.",
    "Paste interview notes, candidate examples and relevant observations here…": "Klistra in intervjuanteckningar, exempel från kandidaten och relevanta observationer här…",
    "Save interview notes": "Spara intervjuanteckningar",
    "The interview notes could not be saved.": "Intervjuanteckningarna kunde inte sparas.",
    "Post-interview decision support": "Beslutsstöd efter intervju",
    "Compares the assessment indications with the saved interview evidence, candidate examples and interviewer observations.": "Jämför indikationerna från testerna med sparat intervjuunderlag, exempel från kandidaten och intervjuarens observationer.",
    "Generate updated post-interview decision support": "Generera uppdaterat beslutsstöd efter intervju",
    "The interview evidence has changed": "Intervjuunderlaget har ändrats",
    "This synthesis was generated using an earlier version of the interview notes or process information. Generate an updated version before relying on it.": "Den här sammanställningen genererades med en tidigare version av intervjuanteckningarna eller processinformationen. Generera en uppdaterad version innan du använder den som underlag.",
    "Comparing the assessment evidence with the interview notes…": "Jämför testunderlaget med intervjuanteckningarna…",
    "The post-interview decision support could not be generated.": "Beslutsstödet efter intervjun kunde inte genereras.",
    "Post-interview synthesis": "Sammanställning efter intervju",
    "The interview evidence has been saved. Generate a synthesis to compare it with the assessment indications and identify remaining uncertainties.": "Intervjuunderlaget har sparats. Generera en sammanställning för att jämföra det med indikationerna från testerna och identifiera kvarstående osäkerheter.",
    "Generate post-interview decision support": "Generera beslutsstöd efter intervju",
    "Add and save interview evidence before generating the post-interview synthesis.": "Lägg till och spara intervjuunderlag innan du genererar sammanställningen efter intervjun.",

    # Post-interview evidence comparison
    "Evidence supporting assessment indications": "Intervjuunderlag som stödjer testindikationerna",
    "Interview evidence that supports patterns identified in the assessment results.": "Intervjuunderlag som stödjer mönster som identifierats i testresultaten.",
    "Assessment indication": "Indikation från testet",
    "Interview evidence": "Intervjuunderlag",
    "Combined interpretation": "Samlad tolkning",
    "No assessment indications received sufficient support from the available interview evidence.": "Inga testindikationer fick tillräckligt stöd av det tillgängliga intervjuunderlaget.",
    "What the interview adds or nuances": "Vad intervjun tillför eller nyanserar",
    "Areas where the interview adds context or suggests a more nuanced interpretation.": "Områden där intervjun tillför kontext eller talar för en mer nyanserad tolkning.",
    "No additional nuance was identified from the available interview evidence.": "Ingen ytterligare nyans identifierades i det tillgängliga intervjuunderlaget.",
    "Contradictions or tensions to consider": "Motsägelser eller spänningar att beakta",
    "These differences should be explored rather than resolved automatically in favour of either source.": "Dessa skillnader bör utforskas snarare än automatiskt avgöras till fördel för någon av källorna.",
    "Assessment evidence:": "Testunderlag:",
    "Interview evidence:": "Intervjuunderlag:",
    "What remains to be explored": "Vad som återstår att utforska",
    "Areas where additional evidence may help the responsible decision-maker form a more complete judgement.": "Områden där ytterligare underlag kan hjälpa den ansvariga beslutsfattaren att göra en mer komplett bedömning.",
    "Remaining uncertainties": "Kvarstående osäkerheter",
    "No specific remaining uncertainties were identified.": "Inga specifika kvarstående osäkerheter identifierades.",
    "Suggested follow-up": "Föreslagen uppföljning",
    "No additional follow-up was suggested.": "Ingen ytterligare uppföljning föreslogs.",
    "Decision support, not a decision": "Beslutsstöd, inte ett beslut",
    "Talena organises and interprets available evidence but does not determine whether the candidate should be selected, rejected, promoted or placed in a role.": "Talena strukturerar och tolkar tillgängligt underlag men avgör inte om kandidaten ska väljas, avslås, befordras eller placeras i en roll.",

    # Small accessibility strings still used in the assessment workspace
    "Personality profile view": "Vy för personlighetsprofil",
    "Left": "Vänster",
    "Right": "Höger",
}


FORMAT_TRANSLATIONS: dict[str, str] = {
    "Last saved %(saved_at)s": "Senast sparat %(saved_at)s",
    "%(character_count)s / 30,000 characters": "%(character_count)s / 30 000 tecken",
}


PLURAL_TRANSLATIONS: dict[tuple[str, str], tuple[str, str]] = {
    (
        "%(process_count)s process",
        "%(process_count)s processes",
    ): (
        "%(process_count)s process",
        "%(process_count)s processer",
    ),
}


PYTHON_FORMAT_RE = re.compile(r"%\(([^)]+)\)[#0 +\-]?[0-9]*(?:\.[0-9]+)?[diouxXeEfFgGcrs]")


def load_catalog(po_file: Path):
    with po_file.open("r", encoding="utf-8") as handle:
        return pofile.read_po(handle, locale="sv", abort_invalid=True)


def placeholders(value: str) -> set[str]:
    return set(PYTHON_FORMAT_RE.findall(value))


def validate_placeholders(source: str, translated: str) -> None:
    if placeholders(source) != placeholders(translated):
        raise ValueError(
            "Placeholder mismatch for translation:\n"
            f"source={source!r}\n"
            f"translation={translated!r}"
        )


def set_message(catalog, msgid: str, msgstr: str, *, python_format: bool = False) -> str:
    validate_placeholders(msgid, msgstr)
    message = catalog.get(msgid)
    state = "unchanged"

    if message is None:
        flags = {"python-format"} if python_format else set()
        catalog.add(msgid, string=msgstr, flags=flags)
        return "added"

    if message.string != msgstr or "fuzzy" in message.flags:
        message.string = msgstr
        message.flags.discard("fuzzy")
        state = "updated"

    if python_format:
        message.flags.add("python-format")

    return state


def set_plural_message(
    catalog,
    msgids: tuple[str, str],
    msgstrs: tuple[str, str],
) -> str:
    for source, translated in zip(msgids, msgstrs, strict=True):
        validate_placeholders(source, translated)

    message = catalog.get(msgids[0])

    if message is None:
        catalog.add(msgids, string=msgstrs, flags={"python-format"})
        return "added"

    state = "unchanged"
    if message.id != msgids or message.string != msgstrs or "fuzzy" in message.flags:
        message.id = msgids
        message.string = msgstrs
        message.flags.discard("fuzzy")
        state = "updated"

    message.flags.add("python-format")
    return state


def validate_catalog(catalog) -> list[str]:
    errors: list[str] = []
    for message, message_errors in catalog.check():
        for error in message_errors:
            errors.append(f"{message.id!r}: {error}")
    return errors


def write_atomic(path: Path, writer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=path.parent, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        writer(temporary)

    temporary_path.replace(path)


def apply_catalog(catalog) -> dict[str, int]:
    counts = {"added": 0, "updated": 0, "unchanged": 0}

    for msgid, msgstr in TRANSLATIONS.items():
        counts[set_message(catalog, msgid, msgstr)] += 1

    for msgid, msgstr in FORMAT_TRANSLATIONS.items():
        counts[set_message(catalog, msgid, msgstr, python_format=True)] += 1

    for msgids, msgstrs in PLURAL_TRANSLATIONS.items():
        counts[set_plural_message(catalog, msgids, msgstrs)] += 1

    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--po", default="locale/sv/LC_MESSAGES/django.po")
    parser.add_argument("--mo", default="locale/sv/LC_MESSAGES/django.mo")
    args = parser.parse_args()

    po_file = Path(args.po).resolve()
    mo_file = Path(args.mo).resolve()

    if not po_file.exists():
        print(f"ERROR: PO file not found: {po_file}", file=sys.stderr)
        return 1

    try:
        catalog = load_catalog(po_file)
        counts = apply_catalog(catalog)
        validation_errors = validate_catalog(catalog)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if validation_errors:
        print("ERROR: PO validation failed:", file=sys.stderr)
        for error in validation_errors[:25]:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "Candidate i18n batch 2: "
        f"{counts['added']} added, "
        f"{counts['updated']} updated, "
        f"{counts['unchanged']} already correct."
    )

    if args.check:
        print("CHECK OK: catalogue is valid; no files were written.")
        return 0

    try:
        write_atomic(
            po_file,
            lambda handle: pofile.write_po(
                handle,
                catalog,
                width=120,
                sort_output=False,
                include_previous=True,
            ),
        )
        write_atomic(
            mo_file,
            lambda handle: mofile.write_mo(handle, catalog),
        )
    except Exception as exc:
        print(f"ERROR writing translation files: {exc}", file=sys.stderr)
        return 1

    print(f"Updated {po_file}")
    print(f"Compiled {mo_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
