#!/usr/bin/env python3
"""
Fill the Swedish gettext entries created by the Talena Motivation language batch.

Run from the repository root:

    python apply_motivation_po_translations.py --check
    python apply_motivation_po_translations.py --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from io import StringIO
from pathlib import Path

from babel.messages import pofile


TRANSLATIONS = {
    "Overall motivation interpretation": (
        "Övergripande motivationstolkning"
    ),
    "Realistic expectation setting": (
        "Realistiska förväntningar"
    ),
    "Conditions likely to support engagement": (
        "Förutsättningar som sannolikt stödjer engagemang"
    ),
    "What to explore or clarify": (
        "Vad som bör utforskas eller förtydligas"
    ),
    "How Talena created this interpretation": (
        "Så skapade Talena tolkningen"
    ),
    (
        "Motivation results describe possible sources of energy, "
        "engagement and preference. Less central factors are not "
        "weaknesses and do not indicate limited capability or poor values."
    ): (
        "Motivationsresultat beskriver möjliga källor till energi, "
        "engagemang och preferenser. Mindre centrala faktorer är inte "
        "svagheter och tyder inte på begränsad förmåga eller bristande "
        "värderingar."
    ),
    (
        "Motivation results indicate possible sources of energy and "
        "preference. Use these questions to gather concrete examples and "
        "the candidate’s own perspective rather than treating assessment "
        "indications as confirmed facts."
    ): (
        "Motivationsresultat visar möjliga källor till energi och "
        "preferenser. Använd frågorna för att samla konkreta exempel och "
        "kandidatens eget perspektiv, snarare än att behandla "
        "indikationerna från testet som bekräftade fakta."
    ),
    "The candidate": "Kandidaten",
    (
        "The profile highlights the candidate's more prominent and less "
        "central motivational drivers, followed by the complete motivation "
        "profile. Results use Sova's rounded five-point STIVE scale."
    ): (
        "Profilen visar kandidatens mer framträdande och mindre centrala "
        "motivationsfaktorer, följt av den fullständiga motivationsprofilen. "
        "Resultaten använder Sovas avrundade femgradiga STIVE-skala."
    ),
    "Circular overview of the candidate's motivation profile": (
        "Cirkulär översikt över kandidatens motivationsprofil"
    ),
    "Preparing motivation overview…": (
        "Förbereder motivationsöversikten…"
    ),
    "%(candidate_name)s’s most prominent drivers": (
        "%(candidate_name)s: mest framträdande drivkrafter"
    ),
    "Factors more likely to provide energy and engagement": (
        "Faktorer som sannolikt ger energi och engagemang"
    ),
    "All motivation factors": (
        "Alla motivationsfaktorer"
    ),
    (
        "Results are grouped according to the four areas in the "
        "motivation model."
    ): (
        "Resultaten är grupperade enligt motivationsmodellens fyra områden."
    ),
    "N/A": "Ej tillgängligt",
    "%(factor_name)s: %(factor_score)s out of 5": (
        "%(factor_name)s: %(factor_score)s av 5"
    ),
    "Less central": "Mindre central",
    "Mid-range": "Mellannivå",
    "More prominent": "Mer framträdande",
    (
        "Motivation scores describe relative sources of energy and "
        "preference. Lower results do not indicate poor performance, weak "
        "values or limited capability. Results should be considered "
        "alongside role context, interview evidence and the candidate's "
        "own reflections."
    ): (
        "Motivationspoäng beskriver relativa källor till energi och "
        "preferenser. Lägre resultat tyder inte på svag prestation, "
        "bristande värderingar eller begränsad förmåga. Resultaten bör "
        "vägas samman med rollkontext, underlag från intervjun och "
        "kandidatens egna reflektioner."
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
        help="Validate without writing the PO file.",
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
                "Success: all Motivation translations were "
                "found and validated."
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
            + ".bak-motivation"
        )
        temporary_path = po_path.with_suffix(
            po_path.suffix
            + ".tmp-motivation"
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
            "Success: Swedish Motivation translations were applied."
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
