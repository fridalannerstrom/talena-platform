from django.db import migrations
from django.utils import timezone


ROLE_SUPPORT_SV = """UPPGIFT

Styr endast sektionen Stöd för rollen i Efter intervju.

Syftet med sektionen är att lyfta sådant som det samlade underlaget faktiskt
GER STÖD FÖR i relation till den uttryckliga roll- eller processkontexten.

Som standard, ge 1 till 4 items när underlaget motiverar det.

ETT ITEM FÅR ENDAST TAS MED OM ALLA FÖLJANDE VILLKOR ÄR UPPFYLLDA:

1. Processkontexten beskriver uttryckligen ett relevant krav, ansvar,
   arbetssätt, prioriterat område eller annan förutsättning.
2. Det finns relevant testunderlag som är förenligt med området.
3. Det finns relevant intervjuunderlag som ger ytterligare stöd eller
   konkretisering.
4. Den samlade tolkningen kan beskrivas som stödjande utan att göra en
   lämplighetsbedömning.

TA INTE MED:

- områden där underlaget är tunt eller motsägelsefullt
- sådant som fortfarande behöver valideras
- möjliga svagheter, utmaningar eller risker
- låga testresultat enbart för att de är låga
- frågor som hör hemma i Områden att utforska
- informationsluckor
- generella positiva egenskaper som inte har tydlig koppling till faktisk
  processkontext

Om ett område behöver diskuteras, verifieras eller utforskas vidare hör det
INTE hemma i Stöd för rollen. Placera den typen av resonemang i Områden att
utforska i stället.

För varje item:

- title ska beskriva det roll- eller kontextområde som faktiskt får stöd
- assessment_indication ska kort ange relevant testunderlag
- interview_evidence ska kort ange relevant intervjuunderlag
- interpretation ska beskriva den konkreta kopplingen till den faktiska
  processkontexten

Använd försiktiga formuleringar, exempelvis att underlaget är förenligt med,
ger stöd för eller är relevant för ett uttalat område.

Skriv inte att kandidaten "är stark", "passar rollen" eller "är en match".
Ett högt testresultat bevisar inte kompetens och ett intervju-exempel
bevisar inte framtida prestation.

Hitta aldrig på rollkrav eller positiva slutsatser för att fylla sektionen.
Om inget område uppfyller villkoren ska listan vara tom.""".strip()


ROLE_SUPPORT_EN = """TASK

Control only the Role support section in After interview.

The purpose of this section is to surface areas where the combined evidence
actually PROVIDES SUPPORT in relation to explicitly supplied role or process
context.

By default, provide 1 to 4 items when warranted by the evidence.

AN ITEM MAY ONLY BE INCLUDED WHEN ALL OF THE FOLLOWING ARE TRUE:

1. The process context explicitly states a relevant requirement,
   responsibility, working approach, priority or condition.
2. Relevant assessment evidence is consistent with that area.
3. Relevant interview evidence provides additional support or
   concretisation.
4. The integrated interpretation can be described as supportive without
   making a suitability judgement.

DO NOT INCLUDE:

- areas where evidence is thin, mixed or contradictory
- anything that still needs validation
- possible weaknesses, challenges or risks
- low assessment results merely because they are low
- questions that belong in Areas to explore
- evidence gaps
- generally positive traits without a clear link to the actual process
  context

If an area still needs discussion, verification or further exploration, it
does NOT belong in Role support. That reasoning belongs in Areas to explore.

For every item:

- title should describe the role or context area that actually receives
  support
- assessment_indication should briefly state relevant assessment evidence
- interview_evidence should briefly state relevant interview evidence
- interpretation should explain the concrete link to the actual process
  context

Use cautious wording, for example that evidence is consistent with,
supportive of or relevant to an explicitly stated context area.

Do not state that the candidate "is strong", "fits the role" or "is a
match". A high assessment result does not prove competence and an interview
example does not prove future performance.

Never invent role requirements or positive conclusions merely to populate
the section. If no area meets the criteria, return an empty list.""".strip()


EVIDENCE_GAPS_SV = """UPPGIFT

Styr endast underdelen Saknas fortfarande i underlaget som visas inne i
Områden att utforska i Efter intervju.

Detta är INTE en andra lista över områden att utforska.

Lista endast konkret information som fortfarande saknas efter att
processkontext, testresultat och intervjuunderlag har vägts samman.

Som standard, ge 0 till 4 korta punkter.

Bra exempel är:
- ett viktigt kontextområde som inte alls eller bara ytligt berörts
- avsaknad av ett konkret beteendeexempel
- en faktisk arbetsförutsättning som behöver klargöras
- en relevant hypotes där nödvändigt underlag saknas

Undvik att återupprepa problemformuleringen från Områden att utforska.
Beskriv i stället exakt vilken information som saknas.

Om ingen tydlig informationslucka finns ska listan vara tom.""".strip()


EVIDENCE_GAPS_EN = """TASK

Control only the Still missing from the evidence subsection displayed
inside Areas to explore in After interview.

This is NOT a second list of areas to explore.

List only concrete information that remains unavailable after integrating
process context, assessment results and interview evidence.

By default, provide 0 to 4 concise items.

Useful examples include:
- an important context area that was not addressed or was only touched on
- a missing concrete behavioural example
- an actual working condition that still needs clarification
- a relevant hypothesis for which necessary evidence is still unavailable

Do not repeat the problem statement from Areas to explore. Instead, state
exactly what information is missing.

If no clear evidence gap remains, return an empty list.""".strip()


def refine_prompts(apps, schema_editor):
    AIPromptTemplate = apps.get_model(
        "processes",
        "AIPromptTemplate",
    )
    db_alias = schema_editor.connection.alias
    now = timezone.now()

    updated = 0

    updated += (
        AIPromptTemplate.objects
        .using(db_alias)
        .filter(
            key="post_interview_supported_indications",
            language="sv",
            prompt_text__contains=(
                "Identifiera områden där det samlade test- och intervjuunderlaget"
            ),
        )
        .update(
            name="After interview · Role support",
            description=(
                "Controls only genuine supporting evidence in the "
                "Stöd för rollen / Role support section. Areas that "
                "need validation belong in Areas to explore instead."
            ),
            prompt_text=ROLE_SUPPORT_SV,
            updated_at=now,
        )
    )

    updated += (
        AIPromptTemplate.objects
        .using(db_alias)
        .filter(
            key="post_interview_supported_indications",
            language="en",
            prompt_text__contains=(
                "Identify areas where the combined assessment and interview evidence"
            ),
        )
        .update(
            name="After interview · Role support",
            description=(
                "Controls only genuine supporting evidence in the "
                "Stöd för rollen / Role support section. Areas that "
                "need validation belong in Areas to explore instead."
            ),
            prompt_text=ROLE_SUPPORT_EN,
            updated_at=now,
        )
    )

    updated += (
        AIPromptTemplate.objects
        .using(db_alias)
        .filter(
            key="post_interview_remaining_uncertainties",
            language="sv",
            prompt_text__contains="Identifiera verkliga informationsgap",
        )
        .update(
            name="After interview · Evidence gaps",
            description=(
                "Controls the optional evidence-gap subsection inside "
                "Areas to explore, not a separate main section."
            ),
            prompt_text=EVIDENCE_GAPS_SV,
            updated_at=now,
        )
    )

    updated += (
        AIPromptTemplate.objects
        .using(db_alias)
        .filter(
            key="post_interview_remaining_uncertainties",
            language="en",
            prompt_text__contains="Identify genuine evidence gaps",
        )
        .update(
            name="After interview · Evidence gaps",
            description=(
                "Controls the optional evidence-gap subsection inside "
                "Areas to explore, not a separate main section."
            ),
            prompt_text=EVIDENCE_GAPS_EN,
            updated_at=now,
        )
    )

    if not updated:
        return

    for model_name in (
        "TestInvitation",
        "HistoricalProcessCandidate",
    ):
        Model = apps.get_model(
            "processes",
            model_name,
        )
        (
            Model.objects
            .using(db_alias)
            .filter(
                ai_post_interview_decision_support_status="completed",
            )
            .exclude(
                ai_post_interview_decision_support={},
            )
            .update(
                ai_post_interview_decision_support_status="outdated",
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0058_mark_post_interview_role_context_outdated"),
    ]

    operations = [
        migrations.RunPython(
            refine_prompts,
            migrations.RunPython.noop,
        ),
    ]
