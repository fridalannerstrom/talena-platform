from __future__ import annotations

from .prompt_templates import AI_PROMPT_REGISTRY


POST_INTERVIEW_ROLE_PROMPT_OVERRIDES = {
    "post_interview_decision_support": {
        "name": "After interview · Combined interpretation",
        "category": "Interview",
        "description": (
            "Controls only the Combined interpretation / Samlad tolkning "
            "section in After interview."
        ),
        "defaults": {
            "sv": """UPPGIFT

Styr endast sektionen Samlad tolkning i Efter intervju.

Väg samman tillgängliga testresultat, intervjuunderlag och processens
faktiska kontext till en kort, praktisk helhetsbild.

Processkontexten är ankaret för relevans. Beskriv vad det samlade
underlaget kan betyda i relation till det som faktiskt står i kontexten,
men hitta aldrig på rollkrav, arbetsuppgifter, ansvar eller prioriteringar.

Om processkontext saknas eller är mycket tunn, säg det tydligt och håll
tolkningen bredare.

Skilj mellan testindikationer, kandidatens exempel, intervjuarens
observationer och AI:ns sammanvägda tolkning.

Testresultat och intervjusvar är underlag, inte bevis på lämplighet eller
framtida prestation.

Skriv som standard ungefär 120 till 180 ord.

Sammanfatta de viktigaste rollrelevanta teman som framträder utan att
upprepa de efterföljande sektionerna punkt för punkt.

Gör inte matchningspoäng, lämplighetsbedömning eller beslut om anställning,
avslag, placering eller befordran.""".strip(),
            "en": """TASK

Control only the Combined interpretation section in After interview.

Integrate the available assessment results, interview evidence and the
actual process context into one concise, practical view.

Use the process context as the anchor for relevance. Explain what the
combined evidence may mean in relation to requirements, priorities or
conditions that are explicitly stated in the context, but never invent
role requirements, tasks, responsibilities or priorities.

If process context is missing or very limited, state that clearly and
keep the interpretation broader.

Distinguish assessment indications, candidate examples, interviewer
observations and the AI synthesis.

Assessment and interview evidence are inputs, not proof of suitability or
future performance.

By default, write approximately 120 to 180 words.

Summarise the most important context-relevant themes without repeating the
following sections item by item.

Do not create match scores, suitability verdicts or hiring, rejection,
placement or promotion decisions.""".strip(),
        },
    },
    "post_interview_supported_indications": {
        "name": "After interview · Role support",
        "category": "Interview",
        "description": (
            "Controls the Stöd för rollen / Role support section in "
            "After interview."
        ),
        "defaults": {
            "sv": """UPPGIFT

Styr endast sektionen Stöd för rollen i Efter intervju.

Identifiera områden där det samlade test- och intervjuunderlaget ger
relevant stöd i relation till processkontexten.

Som standard, ge 2 till 4 items när underlaget motiverar det.

Inkludera endast ett område när processkontexten faktiskt beskriver ett
relevant krav, ansvar, arbetssätt eller prioriterat område. Hitta inte på
rollkrav för att fylla sektionen.

För varje item:
- title ska beskriva det kontextområde som underlaget relaterar till
- assessment_indication ska kort ange relevant testunderlag
- interview_evidence ska kort ange relevant intervjuunderlag
- interpretation ska förklara hur den samlade evidensen ger stöd i
  relation till den faktiska kontexten

Ett högt testresultat är inte automatiskt stöd för rollen. Ett enskilt
intervjuexempel bevisar inte kompetens eller framtida prestation.

Beskriv stöd nyanserat, till exempel att underlaget är förenligt med,
ger stöd för eller är relevant för ett uttalat område i kontexten.

Gör inte en slutlig bedömning av lämplighet och skriv inte att kandidaten
är en match.

Om det saknas användbar processkontext får listan vara tom.""".strip(),
            "en": """TASK

Control only the Role support section in After interview.

Identify areas where the combined assessment and interview evidence
provides relevant support in relation to the supplied process context.

By default, provide 2 to 4 items when the evidence warrants it.

Only include an area when the process context actually states a relevant
requirement, responsibility, working condition or priority. Do not invent
role requirements merely to populate the section.

For each item:
- title should describe the context area the evidence relates to
- assessment_indication should briefly state relevant assessment evidence
- interview_evidence should briefly state relevant interview evidence
- interpretation should explain how the combined evidence provides support
  in relation to the actual context

A high assessment result is not automatically role support. A single
interview example does not prove competence or future performance.

Describe support cautiously, for example as evidence being consistent
with, supportive of or relevant to an explicitly stated context area.

Do not make a suitability verdict or state that the candidate is a match.

If no usable process context is available, the list may be empty.""".strip(),
        },
    },
    "post_interview_added_nuance": {
        "name": "After interview · Additional nuance (background)",
        "category": "Interview",
        "description": (
            "Background-only post-interview nuance retained for backwards "
            "compatibility. It is not a main section in the candidate UI."
        ),
        "defaults": {
            "sv": """UPPGIFT

Detta är en bakgrundssektion som behålls för bakåtkompatibilitet och visas
inte som en huvudsektion i Efter intervju.

Som standard, returnera en tom lista så att innehåll inte dupliceras från
Stöd för rollen eller Områden att utforska.

Om administratörens instruktioner uttryckligen kräver bakgrundsnyans, använd
endast faktiskt test- och intervjuunderlag och undvik slutsatser om
lämplighet.""".strip(),
            "en": """TASK

This is a background section retained for backwards compatibility and is
not displayed as a main section in After interview.

By default, return an empty list so content is not duplicated from Role
support or Areas to explore.

If administrator guidance explicitly requires background nuance, use only
actual assessment and interview evidence and avoid suitability conclusions.""".strip(),
        },
    },
    "post_interview_contradictions": {
        "name": "After interview · Areas to explore",
        "category": "Interview",
        "description": (
            "Controls the Områden att utforska / Areas to explore section "
            "in After interview."
        ),
        "defaults": {
            "sv": """UPPGIFT

Styr endast sektionen Områden att utforska i Efter intervju.

Utgå från processkontexten och identifiera områden som är viktiga för den
aktuella rollen eller situationen men där det samlade underlaget är svagt,
blandat, motsägelsefullt eller fortfarande behöver valideras.

Som standard, ge 1 till 4 items när relevanta områden finns.

Ett område kan vara relevant att utforska när:
- kontexten beskriver ett viktigt krav eller ansvar men underlaget är tunt
- test- och intervjuunderlag ger blandade signaler i relation till kontexten
- kandidatens exempel bara delvis belyser ett viktigt kontextområde
- det finns en relevant spänning mellan preferens, testindikation och
  beskrivet praktiskt arbetssätt

För varje item:
- title ska beskriva det roll- eller kontextområde som behöver utforskas
- assessment_evidence ska ange relevant testunderlag
- interview_evidence ska ange relevant intervjuunderlag
- interpretation ska förklara varför området behöver utforskas i relation
  till den faktiska processkontexten och vad som fortfarande är oklart

Beskriv inte dessa områden automatiskt som svagheter, risker eller tecken på
olämplighet. Ett lågt resultat är inte i sig ett skäl att skapa ett item.

Hitta inte på krav eller problem för att fylla sektionen. Om ingen användbar
processkontext finns får listan vara tom.""".strip(),
            "en": """TASK

Control only the Areas to explore section in After interview.

Use the process context to identify areas that matter for the actual role
or situation where the combined evidence is limited, mixed, conflicting or
still requires validation.

By default, provide 1 to 4 items when relevant areas exist.

An area may be useful to explore when:
- the context states an important requirement or responsibility but the
  available evidence is thin
- assessment and interview evidence provide mixed signals in relation to
  the context
- candidate examples only partly address an important context area
- there is a relevant tension between preference, assessment indication and
  described practical behaviour

For each item:
- title should describe the role or context area requiring exploration
- assessment_evidence should state relevant assessment evidence
- interview_evidence should state relevant interview evidence
- interpretation should explain why the area needs exploration in relation
  to the actual process context and what remains unclear

Do not automatically describe these areas as weaknesses, risks or evidence
of poor suitability. A low result alone is not a reason to create an item.

Do not invent requirements or concerns merely to populate the section. If
no usable process context exists, the list may be empty.""".strip(),
        },
    },
    "post_interview_remaining_uncertainties": {
        "name": "After interview · Remaining evidence gaps",
        "category": "Interview",
        "description": (
            "Controls Kvar att utforska / Remaining evidence gaps in "
            "After interview."
        ),
        "defaults": {
            "sv": """UPPGIFT

Styr endast listan Kvarstående frågetecken under Kvar att utforska.

Identifiera verkliga informationsgap som fortfarande återstår efter att
processkontext, testresultat och intervjuunderlag vägts samman.

Som standard, ge upp till 4 korta punkter.

Fokusera på sådant användaren fortfarande inte vet, till exempel:
- ett viktigt område i processkontexten som inte berörts tillräckligt
- avsaknad av konkreta beteendeexempel
- otydlighet kring förutsättningar, ansvar eller arbetssätt
- en relevant hypotes som fortfarande saknar tillräckligt stöd

Duplicera inte bara Områden att utforska. Den här listan ska beskriva
vilken information som faktiskt saknas.

Hitta inte på osäkerheter för att fylla sektionen. Om inget meningsfullt
informationsgap finns får listan vara tom.""".strip(),
            "en": """TASK

Control only the Remaining questions list under What remains to be
explored.

Identify genuine evidence gaps that remain after considering the process
context, assessment results and interview evidence together.

By default, provide up to 4 concise items.

Focus on information the user still does not know, for example:
- an important process-context area that was not sufficiently explored
- missing concrete behavioural examples
- unclear conditions, responsibilities or working approaches
- a relevant hypothesis that still lacks sufficient evidence

Do not simply duplicate Areas to explore. This list should describe what
information is actually missing.

Do not invent uncertainty merely to populate the section. If no meaningful
evidence gap remains, the list may be empty.""".strip(),
        },
    },
    "post_interview_suggested_follow_up": {
        "name": "After interview · Next steps",
        "category": "Interview",
        "description": (
            "Controls the Nästa steg / Next steps section in After interview."
        ),
        "defaults": {
            "sv": """UPPGIFT

Styr endast sektionen Nästa steg i Efter intervju.

Föreslå konkreta och proportionerliga nästa steg som kan ge bättre underlag
kring Områden att utforska och Kvarstående frågetecken.

Som standard, ge 2 till 5 relevanta åtgärder eller frågor.

Nästa steg kan exempelvis vara:
- en riktad följdfråga
- ett arbetsprov
- en referensfråga
- en praktisk eller teknisk övning
- ett förtydligande av rollens faktiska krav
- ytterligare beteendeexempel

Knyt varje förslag till ett verkligt informationsbehov i underlaget. Ge inte
generiska aktiviteter bara för att fylla listan.

Gör inte beslut om anställning, avslag, placering eller befordran.""".strip(),
            "en": """TASK

Control only the Next steps section in After interview.

Suggest concrete, proportionate next steps that may provide better evidence
for Areas to explore and Remaining questions.

By default, provide 2 to 5 relevant actions or questions.

Next steps may include:
- a targeted follow-up question
- a work sample
- a reference question
- a practical or technical exercise
- clarification of the role's actual demands
- further behavioural examples

Tie each suggestion to a genuine information need in the evidence. Do not
provide generic activities merely to populate the list.

Do not make hiring, rejection, placement or promotion decisions.""".strip(),
        },
    },
}


def install_post_interview_role_context_policy() -> None:
    """Install the role-context semantics into the shared prompt registry."""

    for key, override in POST_INTERVIEW_ROLE_PROMPT_OVERRIDES.items():
        definition = AI_PROMPT_REGISTRY.get(key)
        if definition is None:
            continue

        definition.update(override)
