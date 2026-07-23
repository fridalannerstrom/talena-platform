#!/usr/bin/env python3
"""
Fill the Swedish gettext entries created by the Talena Personality UI
and Response Styles language batch.

Run from the repository root:

    python apply_personality_ui_po_translations.py --check
    python apply_personality_ui_po_translations.py --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from io import StringIO
from pathlib import Path

from babel.messages import pofile


TRANSLATIONS = {
    (
        "A combined interpretation of the personality profile in relation "
        "to the selected purpose and available process context."
    ): (
        "En samlad tolkning av personlighetsprofilen i relation till det "
        "valda syftet och tillgänglig processkontext."
    ),
    "Generate a new personality interpretation": (
        "Generera en ny personlighetstolkning"
    ),
    "Interpreting the personality profile…": (
        "Tolkar personlighetsprofilen…"
    ),
    "Overall personality interpretation": (
        "Övergripande personlighetstolkning"
    ),
    "Combined trait dynamics": (
        "Samspel mellan personlighetsdrag"
    ),
    "Potentially supportive patterns": (
        "Potentiellt stödjande mönster"
    ),
    "What to explore or validate": (
        "Vad som bör utforskas eller valideras"
    ),
    (
        "Explore selected personality traits through practical, "
        "purpose-aware questions."
    ): (
        "Utforska valda personlighetsdrag genom praktiska, "
        "syftesanpassade frågor."
    ),
    "Selecting relevant traits and creating questions…": (
        "Väljer relevanta personlighetsdrag och skapar frågor…"
    ),
    "Traits used for these questions": (
        "Personlighetsdrag som används i frågorna"
    ),
    (
        "Talena generated the questions below using these personality "
        "traits, the process purpose and any available context. Change "
        "the selection to shape the next set of questions."
    ): (
        "Talena skapade frågorna nedan utifrån dessa personlighetsdrag, "
        "processens syfte och eventuell tillgänglig kontext. Ändra "
        "urvalet för att påverka nästa uppsättning frågor."
    ),
    "Change traits": "Ändra personlighetsdrag",
    "Questions to explore": "Frågor att utforska",
    "How Talena created these questions": (
        "Så skapade Talena frågorna"
    ),
    "Select traits to explore": (
        "Välj personlighetsdrag att utforska"
    ),
    "Select up to 6 traits": (
        "Välj upp till 6 personlighetsdrag"
    ),
    "0 selected": "0 valda",
    "Save and generate": "Spara och generera",
    "Response styles": "Svarsstilar",
    (
        "These indicators describe how %(candidate_name)s used the "
        "questionnaire response scale. They provide context for "
        "interpreting the personality profile and are not personality "
        "traits themselves."
    ): (
        "Dessa indikatorer beskriver hur %(candidate_name)s använde "
        "frågeformulärets svarsskala. De ger sammanhang för tolkningen "
        "av personlighetsprofilen och är inte personlighetsdrag i sig."
    ),
    "Questionnaire response pattern": (
        "Svarsmönster i frågeformuläret"
    ),
    "Not available": "Ej tillgängligt",
    "Left score": "Vänsterpoäng",
    "Left": "Vänster",
    "Typical": "Typisk",
    "Right": "Höger",
    "Right score": "Högerpoäng",
    "What does this mean for %(candidate_name)s?": (
        "Vad innebär detta för %(candidate_name)s?"
    ),
    (
        "Analysing the response pattern and preparing practical "
        "guidance…"
    ): (
        "Analyserar svarsmönstret och förbereder praktisk vägledning…"
    ),
    "Try again": "Försök igen",
    "Keep in mind when reading the profile": (
        "Ha detta i åtanke när du läser profilen"
    ),
    "Practical approach": "Praktiskt tillvägagångssätt",
    (
        "Response-style indicators should be used as interpretive "
        "context rather than as measures of ability, suitability or "
        "honesty."
    ): (
        "Svarsstilsindikatorer ska användas som tolkningskontext, "
        "inte som mått på förmåga, lämplighet eller ärlighet."
    ),
    "Personality profile": "Personlighetsprofil",
    (
        "Explore the candidate’s overall personality traits and the "
        "detailed indicators that contribute to each result."
    ): (
        "Utforska kandidatens övergripande personlighetsdrag och de "
        "detaljerade indikatorer som bidrar till varje resultat."
    ),
    "Trait Profile": "Egenskapsprofil",
    "Trait & Indicator Profile": (
        "Egenskaps- och indikatorprofil"
    ),
    "Trait Descriptions": (
        "Beskrivningar av personlighetsdrag"
    ),
    "Left Score": "Vänsterpoäng",
    "Description is not yet available.": (
        "Beskrivning är ännu inte tillgänglig."
    ),
    "Right Score": "Högerpoäng",
    "How this trait may show up for %(candidate_name)s": (
        "Så kan detta personlighetsdrag komma till uttryck hos "
        "%(candidate_name)s"
    ),
    (
        "Personality descriptions summarise likely behavioural "
        "preferences. They should be interpreted alongside the full "
        "profile, response-style indicators and other available "
        "assessment information."
    ): (
        "Beskrivningarna av personlighetsdragen sammanfattar sannolika "
        "beteendepreferenser. De bör tolkas tillsammans med hela "
        "profilen, svarsstilsindikatorerna och övrig tillgänglig "
        "testinformation."
    ),
}


def load_catalog(po_path: Path):
    source = po_path.read_text(encoding="utf-8")

    return pofile.read_po(
        StringIO(source),
        locale="sv",
        abort_invalid=True,
    )


def apply_translations(catalog):
    missing = []
    changed = []

    for msgid, msgstr in TRANSLATIONS.items():
        message = catalog.get(msgid)

        if message is None:
            missing.append(msgid)
            continue

        old_string = message.string
        old_flags = set(message.flags)

        message.string = msgstr
        message.flags.discard("fuzzy")

        if (
            old_string != message.string
            or old_flags != message.flags
        ):
            changed.append(msgid)

    return missing, changed


def validate_catalog(catalog) -> list[str]:
    errors = []

    for message, message_errors in catalog.check():
        for error in message_errors:
            errors.append(
                f"{message.id!r}: {error}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(
        required=True
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Validate the PO changes without writing.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply the Swedish translations.",
    )
    parser.add_argument(
        "--po",
        default="locale/sv/LC_MESSAGES/django.po",
        help=(
            "Path to django.po. Defaults to "
            "locale/sv/LC_MESSAGES/django.po"
        ),
    )
    args = parser.parse_args()

    po_path = Path(args.po).resolve()

    if not po_path.exists():
        print(
            f"ERROR: PO file not found: {po_path}",
            file=sys.stderr,
        )
        return 1

    try:
        catalog = load_catalog(po_path)
        missing, changed = apply_translations(
            catalog
        )

        if missing:
            print(
                "ERROR: The following expected msgid values "
                "were not found:",
                file=sys.stderr,
            )

            for msgid in missing:
                print(
                    f"- {msgid}",
                    file=sys.stderr,
                )

            print(
                "No PO file was changed.",
                file=sys.stderr,
            )
            return 1

        validation_errors = validate_catalog(
            catalog
        )

        if validation_errors:
            print(
                "ERROR: PO validation failed:",
                file=sys.stderr,
            )

            for error in validation_errors[:20]:
                print(
                    f"- {error}",
                    file=sys.stderr,
                )

            print(
                "No PO file was changed.",
                file=sys.stderr,
            )
            return 1

        if args.check:
            print(
                "Success: all Personality UI and Response "
                "Styles translations were found and validated."
            )
            print(
                f"Entries that would be updated: "
                f"{len(changed)}"
            )
            print(
                "No PO file was changed."
            )
            return 0

        backup_path = po_path.with_suffix(
            po_path.suffix
            + ".bak-personality-ui"
        )
        temporary_path = po_path.with_suffix(
            po_path.suffix
            + ".tmp-personality-ui"
        )

        if not backup_path.exists():
            shutil.copy2(
                po_path,
                backup_path,
            )

        with temporary_path.open("wb") as output:
            pofile.write_po(
                output,
                catalog,
                width=79,
                omit_header=False,
                sort_output=False,
            )

        temporary_path.replace(po_path)

        print(
            "Success: Swedish Personality UI and "
            "Response Styles translations were applied."
        )
        print(
            f"Updated entries: {len(changed)}"
        )
        print(
            f"Backup: {backup_path}"
        )
        print(
            "\nNext commands:"
        )
        print(
            "python manage.py compilemessages"
        )
        print(
            "python manage.py check"
        )
        return 0

    except Exception as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        print(
            "No PO file was changed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
