from __future__ import annotations


_INSTALLED = False


PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV = """
UPPGIFT

Förklara hur kandidatens tillgängliga personlighetsprofil kan samspela
med de motivationsfaktorer som finns i underlaget.

Hjälp användaren förstå ett litet antal meningsfulla samband mellan
hur personen föredrar att agera och vad som verkar vara mer eller mindre
centralt som källa till motivation och engagemang.


HÅLL ISÄR MÄTNINGARNA

Personlighetsresultat beskriver preferenser och typiska sätt att agera.
Motivationsresultat beskriver den relativa betydelsen av olika
motivationsfaktorer.

Beskriv inte en motivationsfaktor som en personlighetsegenskap och beskriv
inte ett personlighetsdrag som ett bevis på vad personen är motiverad av.

Ett lågt motivationsresultat betyder inte låg förmåga, låg kompetens,
svag prestation eller att personen saknar egenskapen som faktorn beskriver.


MENINGSFULLT SAMSPEL

Prioritera samband där personlighet och motivation kan:

- förstärka varandra
- påverka hur en motivationsfaktor kan ta sig uttryck i praktiken
- skapa en relevant spänning eller avvägning
- hjälpa användaren förstå under vilka förutsättningar ett tydligt mönster
  kan bli mer eller mindre framträdande

Beskriv inte ett samband enbart för att två resultat råkar vara höga eller
låga. Välj hellre färre, tydligare samband än att försöka kommentera allt.


SPRÅK OCH TON

Skriv ett kort, praktiskt och nyanserat stycke, normalt cirka 80 till 120 ord.

Använd försiktiga formuleringar som:

- kan
- skulle kunna
- tyder på
- kan förstärka
- kan påverka hur

Undvik kategoriska slutsatser, diagnoser och slutliga urvalsbeslut.
Undvik råpoäng om de inte behövs för att göra resonemanget begripligt.
""".strip()


PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN = """
TASK

Explain how the candidate's available personality profile may interact with
the motivation factors available in the evidence.

Help the user understand a small number of meaningful relationships between
how the person tends to prefer to behave and what appears more or less central
as a source of motivation and engagement.


KEEP THE MEASURES DISTINCT

Personality results describe preferences and typical ways of behaving.
Motivation results describe the relative importance of different motivational
factors.

Do not describe a motivation factor as a personality trait and do not treat a
personality trait as proof of what the person is motivated by.

A low motivation result does not mean low ability, low competence, weak
performance or that the person lacks the quality described by the factor.


MEANINGFUL INTERACTION

Prioritise relationships where personality and motivation may:

- reinforce one another
- shape how a motivational factor may be expressed in practice
- create a relevant tension or trade-off
- help the user understand conditions under which a clear pattern may become
  more or less prominent

Do not describe a relationship merely because two results happen to be high
or low. Prefer a smaller number of clearer interactions rather than trying to
comment on everything.


LANGUAGE AND TONE

Write one concise, practical and nuanced paragraph, normally around 80 to 120
words.

Use cautious wording such as:

- may
- could
- suggests
- may reinforce
- may shape how

Avoid categorical conclusions, diagnoses and final selection decisions.
Avoid raw scores unless they are needed to make the reasoning understandable.
""".strip()


def install_personality_motivation_interaction_policy() -> None:
    """Register the dedicated admin prompt for personality × motivation."""

    global _INSTALLED
    if _INSTALLED:
        return

    from apps.core.ai import prompt_templates

    prompt_templates.AI_PROMPT_REGISTRY.setdefault(
        "personality_motivation_interaction",
        {
            "name": "Personality · Interaction with motivation",
            "category": "Personality",
            "description": (
                "Controls the focused AI insight that explains how available "
                "personality preferences may interact with motivation factors."
            ),
            "defaults": {
                "sv": PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_SV,
                "en": PERSONALITY_MOTIVATION_INTERACTION_DEFAULT_EN,
            },
        },
    )

    _INSTALLED = True
