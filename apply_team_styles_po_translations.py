#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from io import StringIO
from pathlib import Path

from babel.messages import pofile


TRANSLATIONS = {'Catalyst': 'Katalysator', 'Director': 'Ledare', 'Energiser': 'Energigivare', 'Architect': 'Arkitekt', 'Harmoniser': 'Harmoniserare', 'Analyst': 'Analytiker', 'Auditor': 'Granskare', 'Connector': 'Nätverkare', 'Explore': 'Utforskande', 'Lead': 'Ledning', 'Deliver': 'Genomförande', 'Critically review': 'Kritisk granskning', 'Looks for creative and innovative solutions and ideas. Brings new insight and new approaches to the team.': 'Söker kreativa och innovativa lösningar och idéer. Bidrar med nya insikter och nya angreppssätt i teamet.', 'May dismiss established approaches too quickly, overcomplicate issues or develop solutions that are more complex than necessary.': 'Kan avfärda etablerade arbetssätt för snabbt, komplicera frågor i onödan eller utveckla lösningar som är mer komplexa än nödvändigt.', 'May communicate spontaneously and move quickly between ideas.': 'Kan kommunicera spontant och snabbt växla mellan olika idéer.', 'Show genuine interest, allow room for creativity and ask questions that help develop the idea.': 'Visa genuint intresse, ge utrymme för kreativitet och ställ frågor som hjälper till att utveckla idén.', 'Rejecting ideas before exploring them, or moving immediately into detailed facts and restrictions.': 'Att avfärda idéer innan de har utforskats eller att omedelbart gå in på detaljer, fakta och begränsningar.', 'Coordinates the group, clarifies needs and goals, and delegates accordingly. Brings clarity and decisiveness to the team.': 'Samordnar gruppen, tydliggör behov och mål och delegerar utifrån detta. Bidrar med tydlighet och beslutsamhet i teamet.', 'May become overly directive, move ahead too quickly or pursue their own agenda without giving enough space to other views.': 'Kan bli alltför styrande, gå framåt för snabbt eller driva sin egen agenda utan att ge tillräckligt utrymme åt andra perspektiv.', 'May focus on tasks, direction and strategy and can sometimes appear relatively businesslike or distant.': 'Kan fokusera på uppgifter, riktning och strategi och ibland uppfattas som relativt saklig eller distanserad.', 'Be clear, rational and businesslike. Focus on the task, expected outcomes and areas of responsibility.': 'Var tydlig, rationell och saklig. Fokusera på uppgiften, förväntade resultat och ansvarsområden.', 'Losing focus on the task, becoming overly personal or failing to deliver what has been agreed.': 'Att tappa fokus på uppgiften, bli alltför personlig eller inte leverera det som har överenskommits.', 'Gets things done and drives the team forward. Brings energy and a sense of motivation to the team.': 'Får saker att hända och driver teamet framåt. Bidrar med energi och en känsla av motivation i teamet.', 'May weaken focus by pursuing too many things at once or changing direction quickly. Can appear forceful or impatient with people who work at a slower pace.': 'Kan försvaga fokus genom att driva för många saker samtidigt eller snabbt byta riktning. Kan uppfattas som pådrivande eller otålig med personer som arbetar i ett lugnare tempo.', 'May communicate quickly, directly and with a strong sense of pace.': 'Kan kommunicera snabbt, direkt och med ett tydligt tempo.', 'Maintain momentum, focus on the most important details, show confidence and involve them in decisions.': 'Behåll tempot, fokusera på de viktigaste detaljerna, visa självförtroende och involvera personen i beslut.', 'Responding too slowly, being excessively cautious or spending too much time on minor details.': 'Att reagera för långsamt, vara överdrivet försiktig eller lägga för mycket tid på mindre detaljer.', 'Turns ideas into practical actions and plans. Brings efficiency, planning and organisation to the team.': 'Omsätter idéer i praktiska handlingar och planer. Bidrar med effektivitet, planering och struktur i teamet.', 'May delay delivery through too much planning and preparation, and may find it difficult to adapt plans when requirements or priorities change.': 'Kan fördröja genomförandet genom alltför mycket planering och förberedelse och kan ha svårt att anpassa planer när krav eller prioriteringar förändras.', 'May prefer concrete discussions about how ideas will be turned into actions.': 'Kan föredra konkreta diskussioner om hur idéer ska omsättas i handling.', 'Be specific, present a clear plan and describe the actions, responsibilities and practical next steps.': 'Var specifik, presentera en tydlig plan och beskriv aktiviteter, ansvar och praktiska nästa steg.', 'Discussing strategy without a practical plan, changing direction after work has started or setting unrealistic timelines.': 'Att diskutera strategi utan en praktisk plan, ändra riktning efter att arbetet har påbörjats eller sätta orealistiska tidsramar.', "Considers other people's needs and feelings. Brings cohesion and a sense of belonging to the team.": 'Tar hänsyn till andra människors behov och känslor. Bidrar med sammanhållning och en känsla av tillhörighet i teamet.', 'May try too hard to please others, find it difficult to say no or set realistic boundaries, and may be less comfortable working independently.': 'Kan anstränga sig för mycket för att tillmötesgå andra, ha svårt att säga nej eller sätta realistiska gränser och kan vara mindre bekväm med att arbeta självständigt.', 'May pay close attention to relationships, inclusion and how other people are feeling.': 'Kan vara särskilt uppmärksam på relationer, delaktighet och hur andra människor mår.', 'Show consideration, recognise individual needs and offer sincere appreciation and support.': 'Visa omtanke, uppmärksamma individuella behov och ge uppriktig uppskattning och stöd.', 'Ignoring relationship concerns, communicating impersonally or placing excessive demands on people who are already under strain.': 'Att ignorera relationsfrågor, kommunicera opersonligt eller ställa alltför höga krav på personer som redan är pressade.', 'Considers alternatives and takes a critical view of ideas and plans. Brings objectivity and critical analysis to the team.': 'Överväger alternativ och granskar idéer och planer kritiskt. Bidrar med objektivitet och kritisk analys i teamet.', 'May spend so much time analysing and evaluating that decisions are delayed or opportunities pass. May appear overly negative or reluctant to accept other perspectives.': 'Kan lägga så mycket tid på analys och utvärdering att beslut fördröjs eller möjligheter går förlorade. Kan uppfattas som alltför negativ eller ovillig att ta in andra perspektiv.', 'May focus on facts, evidence, sources and the reliability of available information.': 'Kan fokusera på fakta, underlag, källor och tillförlitligheten i den information som finns tillgänglig.', 'Be factual and well prepared, provide sufficient detail and allow time to examine or verify important information.': 'Var saklig och väl förberedd, ge tillräckligt med detaljer och lämna tid för att granska eller verifiera viktig information.', 'Making unsupported claims, appearing careless or disorganised, withholding relevant information or setting unrealistic deadlines.': 'Att göra påståenden utan underlag, framstå som slarvig eller oorganiserad, undanhålla relevant information eller sätta orealistiska tidsfrister.', 'Looks for inaccuracies and shortcomings and focuses on delivering what was promised. Brings quality awareness and attention to detail to the team.': 'Söker efter felaktigheter och brister och fokuserar på att leverera det som har utlovats. Bidrar med kvalitetsmedvetenhet och uppmärksamhet på detaljer i teamet.', 'May devote too much time to minor details, overwork to maintain standards or follow rules and procedures so closely that delivery becomes less flexible.': 'Kan lägga för mycket tid på mindre detaljer, arbeta för hårt för att upprätthålla standarder eller följa regler och rutiner så strikt att genomförandet blir mindre flexibelt.', 'May communicate carefully and methodically and prefer time to consider information before responding.': 'Kan kommunicera försiktigt och metodiskt och föredra att få tid att överväga information innan personen svarar.', 'Be calm and systematic, explain the reasons for changes and be clear about deadlines, safety and follow-up.': 'Var lugn och systematisk, förklara skälen till förändringar och var tydlig med tidsfrister, säkerhet och uppföljning.', 'Leaving deadlines unclear, demanding immediate answers or using a forceful approach without explaining why.': 'Att lämna tidsfrister otydliga, kräva omedelbara svar eller använda ett pådrivande arbetssätt utan att förklara varför.', 'Builds, develops and uses networks and other useful resources. Brings new contacts and connections to the team.': 'Bygger, utvecklar och använder nätverk och andra användbara resurser. Bidrar med nya kontakter och förbindelser till teamet.', 'May spend too much time interacting and networking at the expense of other goals, or involve others before the process is sufficiently clear.': 'Kan lägga för mycket tid på interaktion och nätverkande på bekostnad av andra mål eller involvera andra innan processen är tillräckligt tydlig.', 'May communicate in a friendly and relationship-focused way and place value on personal connection.': 'Kan kommunicera på ett vänligt och relationsorienterat sätt och värdesätta personlig kontakt.', 'Explain what you want clearly, allow time for conversation, show appreciation and ask about their perspective.': 'Förklara tydligt vad du vill, ge utrymme för samtal, visa uppskattning och fråga efter personens perspektiv.', 'Taking over the conversation, withholding information, showing little engagement or using a cold or dismissive tone.': 'Att ta över samtalet, undanhålla information, visa lågt engagemang eller använda en kall eller avfärdande ton.', 'Prominent style': 'Framträdande teamstil', "This is a prominent preference in the candidate's profile. The guidance below is therefore likely to be particularly relevant.": 'Detta är en framträdande preferens i kandidatens profil. Vägledningen nedan är därför sannolikt särskilt relevant.', 'Situational style': 'Situationsberoende teamstil', 'This preference is around the middle of the scale. The guidance may be relevant depending on the situation and team context.': 'Denna preferens ligger nära mitten av skalan. Vägledningen kan vara relevant beroende på situationen och teamkontexten.', 'Less likely style': 'Mindre framträdande teamstil', "This is a less prominent preference in the candidate's profile. The guidance below may therefore be less characteristic of their usual approach, but can still be relevant in certain situations.": 'Detta är en mindre framträdande preferens i kandidatens profil. Vägledningen nedan kan därför vara mindre typisk för personens vanliga arbetssätt men ändå relevant i vissa situationer.', 'Team styles': 'Teamstilar', "The profile shows how the candidate may approach eight roles commonly observed in teams. Results use Sova's five-point team-style scale.": 'Profilen visar hur kandidaten kan närma sig åtta roller som ofta förekommer i team. Resultaten använder Sovas femgradiga skala för teamstilar.', 'Team role profile chart': 'Diagram över teamstilsprofil', '%(quadrant)s team style': 'Teamstil inom %(quadrant)s', 'Team style result': 'Teamstilsresultat', '%(title)s: %(value)s out of 5': '%(title)s: %(value)s av 5', 'Less likely': 'Mindre sannolik', 'Typical': 'Typisk', 'More likely': 'Mer sannolik', 'About this team style': 'Om denna teamstil', 'Practical guidance': 'Praktisk vägledning', 'Points to consider when working and communicating with this candidate.': 'Punkter att tänka på när du arbetar och kommunicerar med kandidaten.', 'Communication style': 'Kommunikationsstil', 'Possible limitations': 'Möjliga begränsningar', 'Build trust by': 'Bygg förtroende genom att', 'Try to avoid': 'Försök undvika', 'Team-style results describe likely preferences rather than fixed behaviour or ability. Ordering uses the underlying Sova result, while the displayed values are rounded. Small score differences should not be overinterpreted.': 'Resultat för teamstilar beskriver sannolika preferenser, inte ett fast beteende eller en viss förmåga. Rangordningen använder det underliggande Sova-resultatet, medan de visade värdena är avrundade. Små skillnader i poäng bör inte övertolkas.'}


def load_catalog(po_file: Path):
    return pofile.read_po(
        StringIO(
            po_file.read_text(
                encoding="utf-8"
            )
        ),
        locale="sv",
        abort_invalid=True,
    )


def apply_translations(catalog):
    missing = []
    changed = []

    for msgid, msgstr in TRANSLATIONS.items():
        message = catalog.get(
            msgid
        )

        if message is None:
            missing.append(
                msgid
            )
            continue

        old_string = message.string
        old_flags = set(
            message.flags
        )

        message.string = msgstr
        message.flags.discard(
            "fuzzy"
        )

        if (
            old_string != message.string
            or old_flags != message.flags
        ):
            changed.append(
                msgid
            )

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
    )
    mode.add_argument(
        "--apply",
        action="store_true",
    )
    parser.add_argument(
        "--po",
        default="locale/sv/LC_MESSAGES/django.po",
    )
    args = parser.parse_args()

    po_file = Path(
        args.po
    ).resolve()

    if not po_file.exists():
        print(
            f"ERROR: PO file not found: {po_file}",
            file=sys.stderr,
        )
        return 1

    try:
        catalog = load_catalog(
            po_file
        )
        missing, changed = apply_translations(
            catalog
        )

        if missing:
            print(
                "ERROR: These expected Team Styles msgid "
                "values were not found:",
                file=sys.stderr,
            )
            for msgid in missing:
                print(
                    f"- {msgid}",
                    file=sys.stderr,
                )
            print(
                "Run `python manage.py makemessages -l sv` "
                "first. No PO file was changed.",
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
                "Success: all Team Styles translations "
                "were found and validated."
            )
            print(
                f"Entries that would be updated: {len(changed)}"
            )
            print(
                "No PO file was changed."
            )
            return 0

        backup = po_file.with_suffix(
            po_file.suffix
            + ".bak-team-styles"
        )
        temporary = po_file.with_suffix(
            po_file.suffix
            + ".tmp-team-styles"
        )

        if not backup.exists():
            shutil.copy2(
                po_file,
                backup,
            )

        with temporary.open(
            "wb"
        ) as output:
            pofile.write_po(
                output,
                catalog,
                width=79,
                omit_header=False,
                sort_output=False,
            )

        temporary.replace(
            po_file
        )

        print(
            "Success: Swedish Team Styles translations "
            "were applied."
        )
        print(
            f"Updated entries: {len(changed)}"
        )
        print(
            f"Backup: {backup}"
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
        print(
            "git diff --check"
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
    raise SystemExit(
        main()
    )
