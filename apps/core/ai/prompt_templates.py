from __future__ import annotations

from typing import Any

from django.core.exceptions import ObjectDoesNotExist


SUPPORTED_PROMPT_LANGUAGES = {
    "sv",
    "en",
}


# ============================================================
# Talena AI prompt registry
# ============================================================
#
# This registry defines ALL administrator-editable AI guidance
# for Talena's AI features.
#
# Administrators control the interpretation, reasoning,
# assessment guidance, tone, evidence boundaries, caution,
# conclusions and communication behaviour of the AI.
#
# Only technical runtime requirements remain protected in code:
#
# - input/data plumbing
# - configured output language
# - required JSON/NDJSON structure
# - technical field names
# - streaming event names and order
# - parser/frontend contracts
#
# Database entries in AIPromptTemplate are GLOBAL overrides.
# They affect all customers in Talena.
# ============================================================

RESPONSE_STYLE_GUIDANCE_DEFAULT = """
GENERAL PRINCIPLE

Response styles provide context for interpreting the personality
profile. They are not personality traits, measures of ability,
measures of suitability or proof of honesty.

They may help the practitioner understand how the candidate approached
the questionnaire and how much additional exploration may be useful.


SOCIAL DESIRABILITY

LOW
- May indicate a relatively self-critical way of describing oneself.
- Some personality preferences may be stronger than the displayed
  profile initially suggests.
- Do not assume low confidence or lack of capability.
- A useful next step is to ask the candidate which two or three traits
  someone who knows them well might rate more strongly.
- Invite the candidate to identify qualities they may have understated.

TYPICAL
- Usually suggests a reasonably balanced self-presentation.
- There is no clear tendency towards either overly critical or overly
  positive self-description.
- The personality profile may generally be interpreted in the usual way,
  while still validating important findings with examples.

HIGH
- May indicate a positive self-presentation.
- Some preferences may be less pronounced than the profile initially
  suggests.
- This must not be interpreted as dishonesty.
- A useful next step is to ask which two or three traits the candidate
  may possibly have rated somewhat generously.
- Validate strong results through specific behavioural examples.


PROFILE SPREAD

LOW
- The responses show less differentiation or consistency across
  questions connected to the same personality traits.
- This may have several possible explanations and none should be stated
  as fact.
- Possible areas to explore include:
  - whether the current role matches the person's natural preferences
  - a recent change of role, tasks, goals or responsibilities
  - a role that requires several different behaviours
  - strong situational adaptability
  - the influence of the current environment, manager or team
  - reluctance to take a firm position on some questions
  - uncertainty about how the person typically behaves
- Use neutral questions and explore context before drawing conclusions.

TYPICAL
- The candidate appears to have responded consistently in some parts
  of the questionnaire and with more variation in others.
- Clearer extremes in the personality profile may be the areas in which
  the candidate responded most consistently.
- Validate the most important findings and allow the candidate to add
  situational nuance.

HIGH
- The profile shows clear differentiation across the personality traits.
- The candidate appears to have responded consistently to questions
  connected to the same traits.
- The candidate may be more likely to recognise themselves in the
  resulting personality profile.
- Strong differences should still be explored rather than treated as
  fixed behaviour.


RATINGS SPREAD

LOW
- The candidate used a relatively narrow range of response options and
  made less use of the extreme ends of the scale.
- The candidate may be inclined to qualify answers or explain that their
  behaviour depends on the situation.
- Allow additional time during feedback.
- Use concrete examples and follow-up questions to help the candidate
  clarify where their preferences are strongest.

TYPICAL
- The candidate appears to have used the response scale without a strong
  preference for either neutral or extreme options.
- The profile may generally be interpreted in the usual way while still
  validating important conclusions with examples.

HIGH
- The candidate used a broad range of response options, including the
  more extreme ends of the scale.
- The candidate may express preferences and positions relatively clearly.
- Strong results should still be validated with examples and should not
  automatically be interpreted as fixed or inflexible behaviour.


KNOWN COMBINATION: PROFILE SPREAD HIGH AND RATINGS SPREAD HIGH

- The candidate used a broad range of ratings and appears to have
  responded consistently across related questions.
- The candidate may be relatively likely to recognise themselves in the
  personality profile.
- Consider the candidate's current situation when discussing why
  particular traits are especially pronounced.


KNOWN COMBINATION: PROFILE SPREAD LOW AND RATINGS SPREAD HIGH

- The candidate used clear or extreme ratings, while responses across
  questions connected to the same traits showed less consistency.
- Do not label this as poor self-awareness.
- Explore whether the pattern may relate to:
  - recent changes in role or responsibilities
  - a role requiring several different behaviours
  - strong situational adaptation
  - the influence of a manager, team or working environment
  - uncertainty about which situation to use as the reference point
  - a wish to present oneself in a particular way
- Treat the profile as a starting point for discussion and ask for
  concrete examples from different situations.
""".strip()


AI_PROMPT_REGISTRY: dict[str, dict[str, Any]] = {

    "personality_interpretation": {
        "name": "Personality interpretation",
        "category": "Personality",
        "description": (
            "Controls the tone, emphasis and communication style used "
            "when Talena interprets a candidate's personality profile."
        ),
        "defaults": {

            "sv": """
Skriv tolkningen på ett balanserat, professionellt och utvecklingsorienterat sätt.

Hjälp användaren förstå kandidatens viktigaste beteendepreferenser utan att
beskriva dem som fasta egenskaper.

Lyft både mönster som kan vara stödjande och områden som kan vara relevanta
att utforska vidare.

Var försiktig med negativa formuleringar. Beskriv möjliga utmaningar som
situationsberoende hypoteser eller områden att utforska, inte som konstaterade
brister.

Knyt tolkningen till processens syfte och kontext när det finns stöd för det,
men undvik att överdriva kopplingen.

Använd ett naturligt och lättillgängligt språk som fungerar för en professionell
bedömnings- eller utvecklingssituation.
""".strip(),

            "en": """
Write the interpretation in a balanced, professional and
development-oriented way.

Help the user understand the candidate's most important behavioural
preferences without describing them as fixed characteristics.

Highlight both patterns that may be supportive and areas that may be useful
to explore further.

Be cautious with negative wording. Describe potential challenges as
situational hypotheses or areas to explore, rather than confirmed weaknesses.

Relate the interpretation to the process purpose and context where supported
by the evidence, without overstating the connection.

Use natural and accessible language suitable for a professional assessment
or development context.
""".strip(),

        },
    },
    "response_style_guidance": {
        "name": "Response styles",
        "category": "Personality",
        "description": (
            "Controls the psychometric interpretation guidance used "
            "when Talena explains response styles and how the personality "
            "profile should be approached."
        ),
        "defaults": {
            "sv": RESPONSE_STYLE_GUIDANCE_DEFAULT,
            "en": RESPONSE_STYLE_GUIDANCE_DEFAULT,
        },
    },

    "personality_questions": {
        "name": "Personality questions",
        "category": "Personality",
        "description": (
            "Controls how Talena formulates personality-based interview "
            "and development questions, including tone, focus and the "
            "type of evidence the questions should invite."
        ),
        "defaults": {

            "sv": """
Formulera frågor som hjälper användaren att utforska hur kandidatens
personlighetspreferenser visar sig i verkliga situationer.

Frågorna ska vara öppna, nyfikna och icke-ledande. De ska bjuda in till
konkreta exempel, arbetssätt, reflektion och lärande snarare än att be
kandidaten bekräfta testresultatet.

När det är meningsfullt får två relaterade personlighetsdrag utforskas i
samma fråga, men undvik att kombinera drag som inte naturligt hör ihop.

För rekrytering ska frågorna främst vara beteendeinriktade och be om
konkreta situationer, handlingar och resultat.

För utveckling, onboarding och ledarskapsutveckling ska frågorna kunna vara
mer reflekterande och coachande.

Förklara tydligt varför varje fråga är relevant och vilket beteendemönster
eller vilken hypotes den hjälper användaren att utforska.

I vägledningen om vad användaren ska lyssna efter, prioritera konkreta
beteenden, beslut, avvägningar, anpassningar, resultat och reflektion.

Använd ett naturligt och professionellt språk som fungerar i ett verkligt
intervju- eller återkopplingssamtal.
""".strip(),

            "en": """
Formulate questions that help the user explore how the candidate's
personality preferences appear in real situations.

Questions should be open, curious and non-leading. They should invite
concrete examples, working approaches, reflection and learning rather than
asking the candidate to confirm the assessment result.

Where useful, two meaningfully related personality traits may be explored
in the same question, but avoid combining traits that do not naturally
belong together.

For recruitment, questions should primarily use behavioural interview
wording and request concrete situations, actions and outcomes.

For development, onboarding and leadership development, questions may be
more reflective and coaching-oriented.

Explain clearly why each question is relevant and which behavioural pattern
or hypothesis it helps the user explore.

In the guidance about what to listen for, prioritise concrete behaviour,
decisions, trade-offs, adaptations, outcomes and reflection.

Use natural and professional language suitable for a real interview or
feedback conversation.
""".strip(),

        },
    },
        "motivation_interpretation": {
        "name": "Motivation interpretation",
        "category": "Motivation",
        "description": (
            "Controls the tone, emphasis and communication style used "
            "when Talena interprets a candidate's motivation profile."
        ),
        "defaults": {

            "sv": """
Skriv motivationstolkningen på ett balanserat, praktiskt och
utvecklingsorienterat sätt.

Hjälp användaren förstå vilka faktorer som kan bidra till energi,
engagemang och uthållig motivation, utan att beskriva resultaten som
fasta behov eller absoluta krav.

Beskriv framträdande drivkrafter nyanserat. Förklara både hur de kan
bidra positivt och vilka förväntningar eller frustrationer som kan
uppstå om viktiga drivkrafter inte får tillräckligt utrymme.

Beskriv mindre centrala drivkrafter neutralt. De ska inte framställas
som svagheter eller som något personen aktivt ogillar.

Uppmärksamma relevanta kombinationer och möjliga spänningar mellan
olika drivkrafter när resultaten ger stöd för det.

Knyt tolkningen till processens syfte och kontext när det finns
tillräckligt underlag, men undvik att anta arbetsvillkor, kultur,
belöningar eller ansvar som inte uttryckligen har angetts.

Använd ett naturligt och lättillgängligt språk som hjälper användaren
att förstå vad som kan vara viktigt att utforska vidare tillsammans
med kandidaten.
""".strip(),

            "en": """
Write the motivation interpretation in a balanced, practical and
development-oriented way.

Help the user understand which factors may contribute to energy,
engagement and sustainable motivation without describing the results
as fixed needs or absolute requirements.

Describe prominent drivers with nuance. Explain both how they may
contribute positively and which expectations or frustrations could
arise when important drivers receive insufficient space.

Describe less central drivers neutrally. They should not be presented
as weaknesses or as conditions the person actively dislikes.

Highlight relevant combinations and possible tensions between
different drivers when supported by the results.

Relate the interpretation to the process purpose and context where
there is sufficient evidence, but do not assume working conditions,
culture, rewards or responsibilities that have not been explicitly
provided.

Use natural and accessible language that helps the user understand
what may be useful to explore further with the candidate.
""".strip(),

        },
    },
        "motivation_questions": {
        "name": "Motivation questions",
        "category": "Motivation",
        "description": (
            "Controls how Talena formulates motivation-based interview "
            "and development questions, including tone, focus and the "
            "type of evidence the questions should invite."
        ),
        "defaults": {

            "sv": """
Formulera frågor som hjälper användaren att förstå hur kandidatens
motivationsprofil visar sig i verkliga situationer.

Frågorna ska vara öppna, nyfikna och icke-ledande. De ska bjuda in
kandidaten att beskriva konkreta situationer, prioriteringar, val och
reflektioner snarare än att bekräfta testresultatet.

Utforska olika delar av motivationsprofilen. Frågorna kan till exempel
handla om vad som ger energi, vad som händer när en viktig drivkraft inte
får utrymme, hur mindre centrala drivkrafter fungerar i praktiken eller
hur olika drivkrafter kan stå i spänning med varandra.

För rekrytering ska frågorna vara naturliga att ställa i en intervju och
gärna be om konkreta exempel.

För utveckling, onboarding och ledarskapsutveckling får frågorna vara mer
reflekterande och coachande.

Förklara tydligt varför varje fråga är relevant och vilken
motivationshypotes den hjälper användaren att utforska.

I vägledningen om vad användaren ska lyssna efter, prioritera konkreta
exempel på energi, engagemang, prioriteringar, avvägningar, arbetssätt,
anpassningar och självinsikt.

Använd ett professionellt och naturligt språk som fungerar i ett verkligt
intervju-, utvecklings- eller återkopplingssamtal.
""".strip(),

            "en": """
Formulate questions that help the user understand how the candidate's
motivation profile appears in real situations.

Questions should be open, curious and non-leading. They should invite
the candidate to describe concrete situations, priorities, choices and
reflections rather than asking them to confirm the assessment result.

Explore different parts of the motivation profile. Questions may, for
example, address what provides energy, what happens when an important
driver is absent, how less central drivers appear in practice, or how
different motivational preferences may create tension.

For recruitment, questions should feel natural in an interview and
preferably invite concrete examples.

For development, onboarding and leadership development, questions may
be more reflective and coaching-oriented.

Explain clearly why each question is relevant and which motivation
hypothesis it helps the user explore.

In the guidance about what to listen for, prioritise concrete examples
of energy, engagement, priorities, trade-offs, working approaches,
adaptation and self-awareness.

Use professional and natural language suitable for a real interview,
development or feedback conversation.
""".strip(),

        },
    },
        "cognitive_interpretation": {
        "name": "Cognitive interpretation",
        "category": "Cognitive",
        "description": (
            "Controls the tone, emphasis and communication style used "
            "when Talena interprets cognitive assessment results."
        ),
        "defaults": {

"sv": """
UPPGIFT

Skapa en praktisk och nyanserad tolkning av de tillgängliga
kognitiva testresultaten.

Hjälp användaren förstå:

- vad resultaten kan indikera om hur lätt personen bearbetar den
  typ av information som respektive test mäter
- vilka typer av kognitiva krav som kan göra resultaten mer eller
  mindre relevanta
- vilka förutsättningar, strategier eller former av stöd som kan
  vara relevanta att utforska
- vilka frågor som kan ge ytterligare konkret beteendeunderlag


GRUNDPRINCIPER FÖR TOLKNING

Kognitiva testresultat beskriver relativ prestation på specifika
resonemangsuppgifter jämfört med en referensgrupp.

Beskriv inte resultaten som ett mått på generell intelligens.

Beskriv inte resultaten som ett direkt mått på personlighet,
motivation, kunskap, erfarenhet eller faktisk arbetsförmåga.

Ett lägre resultat innebär inte att personen inte kan utföra en
viss arbetsuppgift.

Ett högre resultat garanterar inte stark arbetsprestation.

Behandla resultaten som indikationer och hypoteser som kan behöva
valideras med andra typer av underlag.

Erfarenhet, förberedelse, språk, trötthet, testförhållanden,
arbetssätt och andra omständigheter kan påverka hur resultatet
bör förstås.

Gör inte en slutlig rekommendation om rekrytering, befordran,
placering eller utvecklingsbeslut enbart utifrån testresultatet.

Skapa inte matchningspoäng eller definitiva lämplighetsbedömningar.

Diagnostisera inte kandidaten.

Hitta inte på kandidatens erfarenheter, arbetsuppgifter,
rollkrav eller annan kontext som inte finns i underlaget.


TOLKNING AV KOGNITIVA KRAV

När det är relevant kan olika nivåer av kognitiva krav användas
för att sätta resultaten i ett praktiskt sammanhang.

Högre kognitiva krav kan exempelvis innebära:

- nya, otydliga eller komplexa problem
- stora informationsmängder från flera källor
- självständiga beslut med betydande konsekvenser
- snabb inlärning med begränsat stöd
- situationer där fel kan få bred påverkan

Måttliga kognitiva krav kan exempelvis innebära:

- viss komplexitet inom relativt tydliga ramar
- flera informationskällor som fortfarande är hanterbara
- viss självständig bedömning
- gradvis inlärning med stöd
- fel som påverkar delar av arbetet eller processen

Lägre kognitiva krav kan exempelvis innebära:

- tydliga och återkommande arbetsuppgifter
- begränsad, strukturerad och linjär information
- regelbaserade beslut
- tydliga instruktioner, träning och repetition
- fel med mer begränsade konsekvenser

Beskriv inte dessa nivåer som bättre eller sämre.
Betydelsen beror på den faktiska situationen och dess krav.


PROCESSENS SYFTE OCH KONTEXT

Knyt tolkningen till processens valda syfte när det är relevant.

Om processkontext finns, använd endast information som faktiskt
finns i underlaget.

Skilj tydligt mellan:

- vad testresultaten kan indikera
- vad processkontexten faktiskt säger
- vad som fortfarande behöver utforskas med andra underlag

Om kontext saknas, gör inte specifika antaganden om arbetsuppgifter,
ansvar, ledarskapskrav, kundsituationer, system eller arbetsmiljö.


SPRÅK OCH TON

Skriv på ett balanserat, praktiskt och icke-dömande sätt.

Använd försiktiga formuleringar när underlaget inte möjliggör
en säker slutsats, exempelvis:

- kan indikera
- tyder på
- skulle kunna innebära
- kan kräva
- kan vara relevant att utforska

Undvik onödigt akademiskt eller tekniskt språk.

Undvik att upprepa formuleringar som "kandidaten är".

Använd personens förnamn när det känns naturligt.

Beskriv både högre och lägre resultat nyanserat.

Ett högre resultat ska inte automatiskt beskrivas som en styrka.

Ett lägre resultat ska inte automatiskt beskrivas som en svaghet.


PRAKTISK TOLKNING

Skriv ungefär 90 till 140 ord.

Tolkningen bör:

- omfatta alla tillgängliga kognitiva testresultat
- beskriva resultatens sannolika praktiska betydelse
- koppla försiktigt till processens syfte
- använda processkontext när sådan finns
- uppmärksamma relevanta begränsningar
- undvika att bara upprepa övriga punkter


RELEVANTA ÖVERVÄGANDEN

Ge 2 till 4 korta punkter.

Punkterna kan exempelvis beskriva:

- en relevant förutsättning
- ett möjligt stödbehov
- en begränsning i underlaget
- ett kognitivt krav som behöver förtydligas

Beskriv inte dessa automatiskt som bekräftade svagheter.


UPPFÖLJNINGSFRÅGOR

Ge 3 öppna och praktiska frågor.

Frågorna ska hjälpa användaren att samla in konkret beteendeunderlag
och jämföra testets indikationer med hur personen faktiskt arbetar.

Frågorna ska inte leda personen mot ett önskat svar.

För rekrytering kan frågorna formuleras som intervjufrågor.

För utveckling, onboarding, ledarskap eller liknande syften kan
frågorna vara mer reflekterande.

För varje fråga, förklara också:

- varför frågan är relevant
- vad användaren kan lyssna efter


KONTEXTNOTERING

Förklara kort:

- vilka kognitiva testresultat som fanns tillgängliga
- om ytterligare processkontext fanns
- hur detta påverkar tolkningens omfattning


RÅDATA

Inkludera inte råa percentilvärden i den slutliga användartexten.
""".strip(),

"en": """
TASK

Create a practical and nuanced interpretation of the available
cognitive assessment results.

Help the user understand:

- what the results may indicate about how readily the person
  processes the type of information measured by each assessment
- which types of cognitive demands may make the results more or
  less relevant
- which conditions, strategies or forms of support may be useful
  to explore
- which questions may provide additional behavioural evidence


CORE INTERPRETATION PRINCIPLES

Cognitive assessment results describe relative performance on
specific reasoning tasks compared with a reference group.

Do not describe the results as a measure of general intelligence.

Do not describe the results as a direct measure of personality,
motivation, knowledge, experience or actual workplace capability.

A lower result does not mean that the person cannot perform a
particular task.

A higher result does not guarantee strong workplace performance.

Treat the results as indications and hypotheses that may need to
be validated using other sources of evidence.

Experience, preparation, language, fatigue, test conditions,
working methods and other circumstances may affect how the
results should be understood.

Do not make a final hiring, promotion, placement or development
decision based solely on the assessment result.

Do not create match scores or definitive suitability verdicts.

Do not diagnose the candidate.

Do not invent candidate experience, job tasks, role requirements
or other context that is not present in the supplied information.


INTERPRETING COGNITIVE DEMANDS

Where relevant, different levels of cognitive demand may be used
to put the results into practical context.

Higher cognitive demands may involve:

- unfamiliar, ambiguous or complex problems
- large amounts of information from multiple sources
- independent decisions with significant consequences
- rapid learning with limited support
- situations where errors may have broad impact

Moderate cognitive demands may involve:

- some complexity within reasonably defined boundaries
- several information sources that remain manageable
- some independent judgement
- gradual learning with support
- errors affecting part of the work or process

Lower cognitive demands may involve:

- clear and recurring tasks
- limited, structured and linear information
- rule-based decisions
- clear instruction, training and repetition
- errors with more limited consequences

Do not describe these levels as better or worse.
Their relevance depends on the actual situation and its demands.


PROCESS PURPOSE AND CONTEXT

Relate the interpretation to the selected process purpose where relevant.

When process context is available, use only information actually
contained in the supplied evidence.

Clearly distinguish between:

- what the assessment results may indicate
- what the supplied process context actually states
- what still needs to be explored using other evidence

When context is unavailable, do not make specific assumptions about
job tasks, responsibilities, leadership demands, customer situations,
systems or working conditions.


LANGUAGE AND TONE

Write in a balanced, practical and non-judgemental way.

Use cautious formulations where the evidence does not support a
definitive conclusion, such as:

- may indicate
- suggests
- could mean
- may require
- could be useful to explore

Avoid unnecessarily academic or technical language.

Avoid repeatedly writing "the candidate is".

Refer to the person by first name where natural.

Describe both higher and lower results with nuance.

A higher result should not automatically be presented as a strength.

A lower result should not automatically be presented as a weakness.


PRACTICAL INTERPRETATION

Write approximately 90 to 140 words.

The interpretation should:

- cover all available cognitive assessment results
- explain the likely practical meaning of the results
- connect cautiously to the selected purpose
- use supplied process context where available
- highlight relevant limitations
- avoid simply repeating the later points


RELEVANT CONSIDERATIONS

Provide 2 to 4 concise points.

These may describe:

- a relevant condition
- a possible support need
- a limitation of the evidence
- a cognitive demand that should be clarified

Do not automatically frame these as confirmed weaknesses.


FOLLOW-UP QUESTIONS

Provide 3 open and practical questions.

The questions should help the user gather concrete behavioural
evidence and compare assessment indications with how the person
actually works.

Questions should not lead the respondent towards a preferred answer.

For recruitment, questions may be phrased as interview questions.

For development, onboarding, leadership or similar purposes,
questions may be more reflective.

For every question, also explain:

- why the question is relevant
- what the user should listen for


CONTEXT NOTE

Briefly explain:

- which cognitive assessments were available
- whether additional process context was available
- how this affects the scope of the interpretation


RAW DATA

Do not include raw percentile values in the final user-facing text.
""".strip(),

        },
    },
        "cognitive_questions": {
        "name": "Cognitive questions",
        "category": "Cognitive",
        "description": (
            "Controls how Talena formulates cognitive follow-up questions, "
            "including tone, focus and the type of behavioural evidence "
            "the questions should invite."
        ),
        "defaults": {

            "sv": """
Formulera frågor som hjälper användaren att samla in konkret beteendeunderlag
kring hur kandidaten angriper olika typer av kognitiva krav i verkliga
situationer.

Frågorna ska vara öppna, praktiska och icke-ledande. De ska bjuda in till
konkreta exempel på hur personen har förstått, strukturerat och arbetat med
information eller problem.

Utforska olika teman, exempelvis komplexitet, mängden information, tempo,
prioriteringar, struktur, självständighet, anpassning och användning av stöd
eller verktyg.

Frågorna ska inte be kandidaten bekräfta testresultatet. De ska i stället
samla in beteendeevidens som kan bekräfta, utmana eller nyansera den
hypotes som testresultatet ger.

För rekrytering ska frågorna vara naturliga att ställa i en intervju och
gärna be om konkreta situationer, arbetssätt, beslut och resultat.

För utveckling, onboarding och ledarskapsutveckling får frågorna vara mer
reflekterande och fokusera på arbetssätt, strategier, stödbehov och lärande.

Förklara tydligt varför varje fråga är relevant och vilken hypotes den
hjälper användaren att utforska.

I vägledningen om vad användaren ska lyssna efter, prioritera konkreta
beteenden såsom hur situationen definierades, vilken information som
användes, hur arbetet strukturerades, vilka beslut eller avvägningar som
gjordes, hur personen anpassade sitt arbetssätt och vad utfallet blev.

Använd ett professionellt och naturligt språk som fungerar i ett verkligt
intervju-, utvecklings- eller återkopplingssamtal.
""".strip(),

            "en": """
Formulate questions that help the user gather concrete behavioural evidence
about how the candidate approaches different types of cognitive demands in
real situations.

Questions should be open, practical and non-leading. They should invite
concrete examples of how the person understood, structured and worked with
information or problems.

Explore different themes, such as complexity, amount of information, pace,
priorities, structure, independence, adaptation and the use of support or
tools.

Questions should not ask the candidate to confirm the assessment result.
Instead, they should gather behavioural evidence that may confirm, challenge
or add nuance to the hypothesis suggested by the assessment.

For recruitment, questions should feel natural in an interview and preferably
invite concrete situations, working methods, decisions and outcomes.

For development, onboarding and leadership development, questions may be
more reflective and focus on working approaches, strategies, support needs
and learning.

Explain clearly why each question is relevant and which hypothesis it helps
the user explore.

In the guidance about what to listen for, prioritise concrete behaviour such
as how the situation was defined, which information was used, how the work
was structured, which decisions or trade-offs were made, how the person
adapted their approach and what the outcome was.

Use professional and natural language suitable for a real interview,
development or feedback conversation.
""".strip(),

        },
    },
        "ai_overview": {
        "name": "AI Overview",
        "category": "Overview",
        "description": (
            "Controls the tone, emphasis and synthesis style used when "
            "Talena combines available assessment evidence into the "
            "candidate's overall AI Overview."
        ),
        "defaults": {

            "sv": """
Skriv den övergripande syntesen på ett balanserat, praktiskt och
icke-dömande sätt.

Hjälp användaren förstå de viktigaste mönstren i det samlade
bedömningsunderlaget utan att göra resultaten mer definitiva än
underlaget tillåter.

Integrera information från personlighet, motivation och kognitiva
resultat när dessa finns tillgängliga. Undvik att skriva separata
mini-rapporter för varje testområde. Fokusera i stället på de
viktigaste gemensamma teman, kombinationerna och nyanserna.

Lyft både indikationer som kan vara relevanta eller stödjande för
processens syfte och områden som behöver utforskas eller förstås
bättre.

Om olika delar av underlaget pekar i olika riktningar, beskriv
spänningen eller nyansen tydligt i stället för att försöka lösa den
med en förenklad slutsats.

Knyt syntesen till processens syfte och eventuell kontext när det finns
stöd för det. Var tydlig när kontext eller annan viktig information
saknas.

Prioritera praktisk användbarhet. Hjälp användaren förstå vad
bedömningsunderlaget kan indikera, vad som fortfarande är osäkert och
vilket nästa steg som kan ge bättre underlag.

Använd ett naturligt och lättillgängligt språk för en professionell
bedömnings-, rekryterings- eller utvecklingssituation.
""".strip(),

            "en": """
Write the overall synthesis in a balanced, practical and
non-judgemental way.

Help the user understand the most important patterns in the combined
assessment evidence without making the results more definitive than
the evidence allows.

Integrate personality, motivation and cognitive results when available.
Avoid writing separate mini-reports for each assessment area. Instead,
focus on the most important shared themes, combinations and nuances.

Highlight both indications that may be relevant or supportive for the
process purpose and areas that should be explored or understood further.

Where different parts of the evidence point in different directions,
describe the tension or nuance clearly rather than resolving it through
an oversimplified conclusion.

Relate the synthesis to the process purpose and any supplied context
where supported. Be clear when context or other important information
is missing.

Prioritise practical usefulness. Help the user understand what the
assessment evidence may indicate, what remains uncertain and which
next step may provide better evidence.

Use natural and accessible language suitable for a professional
assessment, recruitment or development context.
""".strip(),

        },
    },
        "pre_interview_decision_support": {
        "name": "Pre-interview decision support",
        "category": "Final output",
        "description": (
            "Controls the tone, emphasis and synthesis style used when "
            "Talena prepares the final pre-interview decision support "
            "from available assessment evidence."
        ),
        "defaults": {

            "sv": """
Skapa beslutsstödet inför intervjun på ett balanserat, praktiskt och
icke-dömande sätt.

Hjälp användaren få en tydlig helhetsbild av det tillgängliga
bedömningsunderlaget inför intervju eller återkoppling.

Prioritera de viktigaste integrerade teman som framträder när
personlighet, motivation, kognitiva resultat, svarsstilar och tidigare
AI-tolkningar vägs samman.

Undvik att skriva separata sammanfattningar av varje test. Fokusera i
stället på de teman, kombinationer, nyanser och osäkerheter som är mest
relevanta att ta med in i nästa samtal.

Var tydlig med skillnaden mellan:
- vad bedömningsunderlaget kan indikera
- vad processkontexten faktiskt säger
- vad som fortfarande behöver valideras med kandidatens egna exempel

Lyft både relevanta indikationer och områden som kräver försiktig
tolkning. Osäkerhet ska beskrivas öppet snarare än döljas bakom en
förenklad slutsats.

Prioritera frågor och fokusområden som kan ge ny information och hjälpa
användaren att bekräfta, utmana eller nyansera bedömningshypoteserna.

Skriv så att en rekryterare, chef eller annan professionell användare
enkelt kan förstå vad som är viktigt att ta med sig till intervjun.

Beslutsstödet ska hjälpa människan att förbereda nästa steg, inte fatta
beslutet åt henne.
""".strip(),

            "en": """
Create the pre-interview decision support in a balanced, practical and
non-judgemental way.

Help the user gain a clear overall view of the available assessment
evidence before an interview or feedback conversation.

Prioritise the most important integrated themes that emerge when
personality, motivation, cognitive results, response styles and previous
AI interpretations are considered together.

Avoid writing separate summaries of each assessment. Instead, focus on
the themes, combinations, nuances and uncertainties that are most
important to carry into the next conversation.

Clearly distinguish between:
- what the assessment evidence may indicate
- what the process context actually states
- what still needs to be validated through the candidate's own examples

Highlight both relevant indications and areas requiring cautious
interpretation. Describe uncertainty openly rather than hiding it behind
an oversimplified conclusion.

Prioritise questions and focus areas that may provide new information and
help the user confirm, challenge or add nuance to the assessment
hypotheses.

Write so that a recruiter, manager or other professional user can easily
understand what is most important to take into the interview.

The decision support should help the human prepare the next step, not make
the decision for them.
""".strip(),

        },
    },
        "post_interview_decision_support": {
        "name": "Post-interview decision support",
        "category": "Final output",
        "description": (
            "Controls the tone, emphasis and synthesis style used when "
            "Talena combines assessment evidence with interview notes "
            "after the interview."
        ),
        "defaults": {

            "sv": """
Skapa beslutsstödet efter intervjun på ett balanserat, praktiskt och
evidensmedvetet sätt.

Hjälp användaren förstå hur intervjuunderlaget förhåller sig till de
tidigare indikationerna från testresultaten.

Prioritera samspelet mellan testresultat och konkret intervjuunderlag.
Beskriv tydligt när kandidatens exempel ger stöd åt en tidigare hypotes,
när de tillför viktig nyans och när olika delar av underlaget verkar peka
i olika riktningar.

Ge större vikt åt konkreta beteendeexempel med tydlig situation,
agerande och resultat än åt breda självbeskrivningar, hypotetiska svar
eller allmänna intryck.

Beskriv motsägelser och spänningar neutralt. Försök inte avgöra vilken
informationskälla som är rätt när underlaget inte räcker för det.

Uppmärksamma skillnaden mellan personens preferenser, faktiska beteenden,
strategier, erfarenheter och förmåga när det är relevant.

Var tydlig med vad som fortfarande är osäkert eller saknar tillräckligt
underlag även efter intervjun.

Föreslå uppföljning som kan ge relevant ny information, exempelvis
ytterligare frågor, arbetsprov, referenser eller förtydliganden av den
faktiska kontexten.

Använd ett naturligt och professionellt språk som hjälper användaren att
väga samman underlaget utan att göra AI:n till beslutsfattare.
""".strip(),

            "en": """
Create the post-interview decision support in a balanced, practical and
evidence-aware way.

Help the user understand how the interview evidence relates to the
previous indications from the assessments.

Prioritise the relationship between assessment results and concrete
interview evidence. Clearly describe when candidate examples support a
previous hypothesis, when they add important nuance and when different
parts of the evidence appear to point in different directions.

Give greater weight to concrete behavioural examples with a clear
situation, action and outcome than to broad self-descriptions,
hypothetical answers or general impressions.

Describe contradictions and tensions neutrally. Do not decide which
source is correct where the evidence is insufficient to do so.

Highlight the distinction between preferences, actual behaviour,
strategies, experience and capability where relevant.

Be clear about what remains uncertain or insufficiently evidenced even
after the interview.

Suggest follow-up that may provide meaningful new evidence, such as
additional questions, work samples, references or clarification of the
actual context.

Use natural and professional language that helps the user integrate the
evidence without turning the AI into the decision-maker.
""".strip(),

        },
    },
}


def normalize_prompt_language(
    language: str | None,
) -> str:
    """
    Normalize language codes used for editable AI prompts.

    Examples:
    sv-SE -> sv
    sv_SE -> sv
    en-GB -> en
    """

    normalized = (
        str(language or "sv")
        .strip()
        .lower()
        .replace("_", "-")
    )

    base_language = normalized.split(
        "-",
        1,
    )[0]

    if base_language in SUPPORTED_PROMPT_LANGUAGES:
        return base_language

    return "sv"


def get_ai_prompt_definition(
    key: str,
) -> dict[str, Any]:
    """
    Return the registry definition for one AI prompt.
    """

    try:
        return AI_PROMPT_REGISTRY[key]

    except KeyError as exc:
        raise KeyError(
            f"Unknown AI prompt key: {key}"
        ) from exc


def get_default_ai_prompt(
    *,
    key: str,
    language: str,
) -> str:
    """
    Return Talena's protected default business guidance.
    """

    language = normalize_prompt_language(
        language
    )

    definition = get_ai_prompt_definition(
        key
    )

    defaults = definition.get(
        "defaults",
        {},
    )

    default_prompt = (
        defaults.get(language)
        or defaults.get("en")
        or defaults.get("sv")
        or ""
    )

    return str(
        default_prompt
    ).strip()


def get_ai_prompt_instructions(
    *,
    key: str,
    language: str,
    default: str | None = None,
) -> str:
    """
    Return the currently active GLOBAL business guidance.

    Priority:

    1. Active global administrator override from AIPromptTemplate.
    2. Explicit fallback supplied by the caller, for backwards compatibility.
    3. Protected Talena default from AI_PROMPT_REGISTRY.

    Customer/company-specific prompts are intentionally not supported here.
    """

    from apps.processes.models import AIPromptTemplate

    normalized_language = normalize_prompt_language(
        language
    )

    if default is None:
        protected_default = get_default_ai_prompt(
            key=key,
            language=normalized_language,
        )

    else:
        protected_default = str(
            default
        ).strip()

    try:
        prompt_template = AIPromptTemplate.objects.get(
            key=key,
            language=normalized_language,
            is_active=True,
        )

    except ObjectDoesNotExist:
        return protected_default

    prompt_text = (
        prompt_template.prompt_text
        or ""
    ).strip()

    if not prompt_text:
        return protected_default

    return prompt_text


def list_ai_prompt_definitions() -> list[dict[str, Any]]:
    """
    Return all registered AI features in display order.

    This is used by Talena's admin UI so prompts appear even
    when no database override has ever been created.
    """

    result = []

    for key, definition in AI_PROMPT_REGISTRY.items():
        result.append(
            {
                "key": key,
                "name": definition.get(
                    "name",
                    key,
                ),
                "category": definition.get(
                    "category",
                    "",
                ),
                "description": definition.get(
                    "description",
                    "",
                ),
            }
        )

    return sorted(
        result,
        key=lambda item: (
            item["category"],
            item["name"],
        ),
    )