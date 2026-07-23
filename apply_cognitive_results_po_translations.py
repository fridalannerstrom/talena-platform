#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from io import StringIO
from pathlib import Path

from babel.messages import pofile

TRANSLATIONS = {'Not completed': 'Inte genomfört', 'Very low': 'Mycket låg', 'Low': 'Låg', 'Typical range': 'Typiskt intervall', 'High': 'Hög', 'Very high': 'Mycket hög', 'This candidate has not completed this assessment.': 'Kandidaten har inte genomfört det här testet.', 'understand and evaluate written information': 'förstå och utvärdera skriftlig information', 'identify patterns and reach logical conclusions': 'identifiera mönster och dra logiska slutsatser', 'understand and work with numerical information': 'förstå och arbeta med numerisk information', 'The candidate may find it considerably more difficult than most people in the reference group to %(ability)s.': 'Kandidaten kan uppleva det som betydligt svårare än de flesta i referensgruppen att %(ability)s.', 'The candidate may find it more difficult than many others in the reference group to %(ability)s.': 'Kandidaten kan uppleva det som svårare än många andra i referensgruppen att %(ability)s.', 'The candidate is likely to find it about as easy as most people in the reference group to %(ability)s.': 'Kandidaten har sannolikt ungefär lika lätt som de flesta i referensgruppen att %(ability)s.', 'The candidate may find it easier than many others in the reference group to %(ability)s.': 'Kandidaten kan ha lättare än många andra i referensgruppen att %(ability)s.', 'The candidate may find it considerably easier than most people in the reference group to %(ability)s.': 'Kandidaten kan ha betydligt lättare än de flesta i referensgruppen att %(ability)s.', 'Logical reasoning': 'Logisk förmåga', 'Logical reasoning ability': 'Förmåga till logiskt resonemang', 'Numerical reasoning': 'Numerisk förmåga', 'Numerical reasoning ability': 'Förmåga till numeriskt resonemang', 'Verbal reasoning': 'Verbal förmåga', 'Verbal reasoning ability': 'Förmåga till verbalt resonemang', '%(title)s percentile %(percentile)s': '%(title)s, percentil %(percentile)s', '%(title)s assessment not completed': '%(title)s, testet är inte genomfört', 'Cognitive assessment': 'Kognitivt test', 'Percentile': 'Percentil', 'Compared with the reference group': 'Jämfört med referensgruppen', 'Lower': 'Lägre', 'Higher': 'Högre', 'No result': 'Inget resultat', 'No percentile result is available.': 'Inget percentilresultat är tillgängligt.', 'Percentiles describe relative performance compared with a reference group. They are not percentages of questions answered correctly.': 'Percentiler beskriver relativ prestation jämfört med en referensgrupp. De är inte procentandelar av frågorna som besvarades korrekt.', 'Practical interpretation': 'Praktisk tolkning', 'Relevant considerations': 'Relevanta överväganden', 'How Talena created this interpretation': 'Så skapade Talena tolkningen', 'Cognitive assessment results describe relative performance on specific reasoning tasks. They do not measure personality, motivation, experience or overall intelligence, and should be considered together with other relevant evidence.': 'Resultat från kognitiva tester beskriver relativ prestation i specifika resonemangsuppgifter. De mäter inte personlighet, motivation, erfarenhet eller generell intelligens och bör vägas samman med annat relevant underlag.', 'Why this matters': 'Varför detta är viktigt', 'What to look for in the answer': 'Vad du ska vara uppmärksam på i svaret', 'Use these questions to gather concrete examples of how the candidate works with information and approaches problems. Cognitive assessment results provide supporting evidence and should not replace information from relevant experience, structured interviews or other assessment methods.': 'Använd frågorna för att samla konkreta exempel på hur kandidaten arbetar med information och tar sig an problem. Resultat från kognitiva tester ger stödjande underlag och ska inte ersätta information från relevant erfarenhet, strukturerade intervjuer eller andra bedömningsmetoder.'}

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
            errors.append(f"{message.id!r}: {error}")

    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--po",
        default="locale/sv/LC_MESSAGES/django.po",
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
        missing, changed = apply_translations(catalog)

        if missing:
            print(
                "ERROR: These expected Cognitive msgid values "
                "were not found:",
                file=sys.stderr,
            )
            for msgid in missing:
                print(f"- {msgid}", file=sys.stderr)
            print(
                "Run `python manage.py makemessages -l sv` first. "
                "No PO file was changed.",
                file=sys.stderr,
            )
            return 1

        validation_errors = validate_catalog(catalog)

        if validation_errors:
            print(
                "ERROR: PO validation failed:",
                file=sys.stderr,
            )
            for error in validation_errors[:20]:
                print(f"- {error}", file=sys.stderr)
            print(
                "No PO file was changed.",
                file=sys.stderr,
            )
            return 1

        if args.check:
            print(
                "Success: all Cognitive Results translations "
                "were found and validated."
            )
            print(
                f"Entries that would be updated: {len(changed)}"
            )
            print("No PO file was changed.")
            return 0

        backup_path = po_path.with_suffix(
            po_path.suffix + ".bak-cognitive-results"
        )
        temporary_path = po_path.with_suffix(
            po_path.suffix + ".tmp-cognitive-results"
        )

        if not backup_path.exists():
            shutil.copy2(po_path, backup_path)

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
            "Success: Swedish Cognitive Results translations "
            "were applied."
        )
        print(f"Updated entries: {len(changed)}")
        print(f"Backup: {backup_path}")
        print("\nNext commands:")
        print("python manage.py compilemessages")
        print("python manage.py check")
        print("git diff --check")
        return 0

    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        print(
            "No PO file was changed.",
            file=sys.stderr,
        )
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
