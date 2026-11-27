# Talena – underlag till AI per funktion och synlig text

**Status:** Kodgranskad funktionskarta, inte verifiering av faktiska produktionsanrop  
**Granskad kod:** main, commit f93d001c57d3f459cc3724d664bcf87e55d0a9c5 (2026-10-22)  
**Målgrupp:** De som skriver adminpromptar, produktägare samt säkerhets-/GDPR-granskare  
**Relaterad teknisk inventering:** [talena-openai-datafloden.md](talena-openai-datafloden.md)

> **Viktigt:** Nedan betyder ”får” att fältet/underlaget enligt programkoden kan byggas in i prompten **före** separat kandidatnamnsmaskering och central PII-sanerare. Faktiska värden beror på genomförda tester, sparat material, språk, processkontext och aktiva adminpromptar. Den slutliga HTTP-payloaden har **inte** fångats eller verifierats mot drift här. Detta dokument är inte en GDPR-garanti. Inga riktiga kandidatuppgifter används.

## 1. För den som skriver promptar

Det finns tre olika saker att hålla isär:

1. **Källunderlag:** råa eller normaliserade Sova-resultat, Talenas Resultatsammanfattning, redan sparade AI-texter, fritext, frågor/svar och processkontext. Varje funktion får olika delar.
2. **Instruktioner:** övergripande Talena-instruktioner, funktionens adminprompt, eventuella särskilda promptar för en viss ruta samt skyddade tekniska instruktioner.
3. **Faktiskt utgående anrop:** ett anrop med system- och användarmeddelanden som passerar centrala saneringslagret. Något som tidigare lagts in i en prompt kan maskeras innan det når OpenAI.

**Ingen prompt ska utgå från att en viss datatyp finns bara för att funktionen kan använda den.** AI:n får inte själv hitta på saknade testvärden, intervjusvar eller härledda statistiska index.

### Översikt över textgenererande funktioner

| ID / var texten används | Underlag som kodvägen bygger av | Saknas eller begränsas | Viktig promptinstruktion / källa |
|---|---|---|---|
| **AI-01 Kandidatsammanfattning** | Processyfte och roll-/processkontext; Sova-kompetenser med tillgängliga poäng; relevant personlighetsunderlag och admininstruktioner. | Skickar inte automatiskt hela Sova-JSON-objektet. | [candidate_summary.py](../../apps/core/ai/candidate_summary.py) |
| **AI-02 Generella insikter (Flexible)** | Personlighetens poäng/profil, motivationsfaktorer inklusive topp/lägst, tillgängliga färdighetspercentiler och den kandidatunika Resultatsammanfattningen. | Ingen obligatorisk rollmatchning. Kan genereras vid kandidatvy, inte enbart med Generera-knapp. | [candidate_insights.py](../../apps/reports/services/candidate_insights.py), [shared_personality_grounding_policy.py](../../apps/core/ai/shared_personality_grounding_policy.py) |
| **AI-03 AI-överblick / ändamålsanpassad profil** | Processyfte, kontext, normaliserade bedömningsresultat från Sova samt kandidatens Resultatsammanfattning med personlighetsinnebörd och admininstruktioner. | Bara assessmenttyper med tillgängliga resultat. | [purpose_fit.py](../../apps/core/ai/purpose_fit.py), [shared_personality_grounding_policy.py](../../apps/core/ai/shared_personality_grounding_policy.py) |
| **AI-04 Personlighetstolkning och Chefsrapportens personlighet** | Översatt Resultatsammanfattning **per personlighetsdrag**; processyfte och kontext; tillgängliga motivationsvärden/definitioner; indikator-/temaunderlag; generella intervjuanteckningar och frågekopplade svar/anteckningar; globala och rut-/funktionsspecifika adminpromptar. | Den sista startup-policyn **ersätter äldre råa STEN-värden för övergripande personlighetsdrag** med Resultatsammanfattning, men andra källor och anteckningar finns kvar. Chefsrapportens personlighet genereras som sex texter (Testbild + Kandidaten beskriver i tre teman) i samma personlighetstolkningsflöde; inte sex nödvändigtvis separata API-anrop. | [personality_interpretation.py](../../apps/core/ai/personality_interpretation.py), [personality_ai_input_contract_policy.py](../../apps/core/ai/personality_ai_input_contract_policy.py) |
| **AI-05 Personlighetsfrågor** | Personlighetens kandidatspecifika Resultatsammanfattning, processyfte/kontext, valda egenskaper eller kompetenser beroende på läge, samt tillhörande admininstruktioner. | För frågor om övergripande personlighetsdrag ersätter en policy äldre direkta STEN-/riktningstexter med Resultatsammanfattningen. Kompetensläget har egen underlagsväg. Ett format-reparationsanrop kan förekomma. | [personality_questions.py](../../apps/core/ai/personality_questions.py), [personality_question_definition_grounding_policy.py](../../apps/core/ai/personality_question_definition_grounding_policy.py) |
| **AI-06 Motivationstolkning** | Motivationsfaktorer, exakta STIVE-resultat där tillgängliga, faktordefinitioner, processyfte/kontext samt administrativa instruktioner till de olika motivationsdelarna. | Om motivationstest saknas ska det inte fyllas ut med gissade värden. | [motivation_interpretation.py](../../apps/core/ai/motivation_interpretation.py) |
| **AI-07 Motivationsfrågor** | Motivationsfaktorer med poäng/definitioner, syfte, processkontext, admins instruktioner. | Extra reparationsanrop möjligt vid ogiltigt JSON-svar. | [motivation_questions.py](../../apps/core/ai/motivation_questions.py) |
| **AI-08 Färdighetstolkning** | Tillgängliga percentiler för verbal, logisk och numerisk förmåga, syfte/kontext och admininstruktioner. | Inget värde för en färdighet som saknas. | [cognitive_interpretation.py](../../apps/core/ai/cognitive_interpretation.py) |
| **AI-09 Färdighetsfrågor** | Tillgängliga färdighetspercentiler, processyfte/kontext och admininstruktioner. | Reparationsanrop kan förekomma. | [cognitive_questions.py](../../apps/core/ai/cognitive_questions.py) |
| **AI-10 Svarsstilar / separat intervjuförhållningssätt** | Tillgängliga svarsstilar med teknisk nyckel och **avrundat STEN**; den översatta Resultatsammanfattningen per personlighetsdrag som stödjande kontext; syfte/kontext; global adminprompt samt separata instruktioner för tolkning respektive samtalsförhållningssätt. | Resultatsammanfattningen får inte användas som en ersättning för mätning av svarsstil. Inga intervjuanteckningar i denna prompts grundkontrakt. | [response_style_guidance.py](../../apps/core/ai/response_style_guidance.py), [personality_ai_input_contract_policy.py](../../apps/core/ai/personality_ai_input_contract_policy.py) |
| **AI-11 Före intervju** | Normaliserade **råa** tillgängliga testresultat (personlighet/STEN, motivation/STIVE, färdigheter/percentiler och förekommande andra poäng); kandidatens översatta Resultatsammanfattning; tidigare sparad AI-överblick, personlighetstolkning, motivationstolkning, färdighetstolkning och svarsstilsvägledning; sparad frågebank med eventuella ”varför” och ”lyssna efter”; syfte/kontext och adminprompt. | **Inga intervjuanteckningar eller redan sparade intervjusvar ska ingå i denna före-intervju-prompt.** En saknad källa tas inte för given. | [decision_support.py](../../apps/core/ai/decision_support.py), [pre_interview_raw_evidence_policy.py](../../apps/core/ai/pre_interview_raw_evidence_policy.py) |
| **AI-12 Efter intervju – äldre syntesväg** | Tidigare samlat beslutsunderlag, tidigare tolkningar, processkontext och intervjumaterial. | Äldre kvarvarande genereringsväg, skild från de separata rutorna nedan; aktiv användning behöver kontrolleras. | [decision_support.py](../../apps/core/ai/decision_support.py) |
| **AI-13 Efter intervju – Helhetsbild** | Normaliserat bedömningsunderlag och sparade bedömningstolkningar, **generella intervjuanteckningar**, exakta frågor med tillhörande sparade svar/anteckningar, syfte/kontext, global och flikspecifik adminprompt. | Kräver intervjuevidens (generell eller frågekopplad). | [decision_support.py](../../apps/core/ai/decision_support.py) – overall_picture |
| **AI-13 Efter intervju – Intervjusammanfattning** | Generella intervjuanteckningar och exakta frågor med tillhörande svar/anteckningar, syfte/kontext samt adminprompt. | **Bedömningssyntesen utelämnas uttryckligen ur fältet ASSESSMENT INDICATIONS** för denna del. | [decision_support.py](../../apps/core/ai/decision_support.py) – interview_summary |
| **AI-13 Efter intervju – Undersök vidare** | Bedömningsunderlag/tolkningar, intervjuanteckningar, kopplade svar/anteckningar, syfte/kontext och separat adminprompt. | Beroende av befintlig intervjuevidens. | [decision_support.py](../../apps/core/ai/decision_support.py) – explore_further |
| **AI-13 Efter intervju – Tips för trivsel (äldre intern blocknyckel)** | Samma huvudsakliga grundunderlag som de andra bedömningsbaserade efter-intervju-blocken, med egen adminprompt. | Blocknyckeln ”wellbeing_tips” finns fortfarande i backend; detta betyder **inte** att en separat synlig flik måste finnas i dagens UI. | [decision_support.py](../../apps/core/ai/decision_support.py) – wellbeing_tips |
| **AI-14 Kandidatens egen resultattext** | Processyfte/kontext, befattning, tillgängliga bedömningar, andra sparade Talena-tolkningar och enligt nuvarande byggare även omfattande Sova-relaterade objekt såsom activities, project_results och reports, samt adminpromptar. | Risk för för bred datamängd, rapportlänkar och onödig metadata. Måste whitelist-granskas innan slutligt godkännande. | [interpretation.py](../../apps/candidate_results/interpretation.py) |
| **AI-15 Teaminsikter** | Teammål, beskrivning/kontext, antal personer med/utan bedömning, aggregerade genomsnitt per teamstil, admininstruktioner. | Individers ID:n förekommer i lokal signatur/fingerprint men inte i promptens aggregerade teamkontext enligt granskad kodväg. | [ai_insights.py](../../apps/teams/ai_insights.py) |
| **AI-18 Admin – Prompt Playground** | Fördefinierad **exempelkandidat** och syntetiska testresultat, vald administratörsprompt, eventuellt adminredigerad kontext, språk och testuppgift. | Playground är **inte bevis** för att produktionsflödet får exakt samma underlag. Administratörer kan ändå klistra in personuppgifter. | [prompt_playground.py](../../apps/core/ai/prompt_playground.py) |

**Ytterligare OpenAI-vägar, utan aktiv kandidatspecifik genererad text:**

- **AI-16 / AI-17, allmän respektive kandidatrelaterad AI-chatt:** båda befintliga endpoints ger nu HTTP 404 innan prompt eller kandidatkontext läses. Äldre riskbeskrivning i huvudrapporten avser dess granskade historiska commit. Källa: [apps/ai_chat/views.py](../../apps/ai_chat/views.py).
- **AI-19 / AI-20, embeddings:** frågetext respektive kunskapschunks skickas för vektorisering, inte för att skriva synlig kandidattext. Information om Pinecone och lagring finns i huvudrapporten.

## 2. Exakt hur ”Kommunikationsstrategi” i Före intervju genereras

**Visad rubrik:** Före intervju → Så når du fram i samtalet → Kommunikationsstrategi.

**Tekniskt textfält:** discussion_guidance.feedback_approach i resultatet från **AI-11 Före intervju**. Det är **inte samma AI-resultat** som AI-10:s recommended_approach från ”Svarsstilar”. JavaScript läser listan och sammanfogar posterna till text på sidan: [pre-interview-briefing.js](../../static/js/talena/pre-interview-briefing.js).

**Adminprompt som styr genereringen:** pre_interview_decision_support. Den skyddade [pre_interview_grounding_policy.py](../../apps/core/ai/pre_interview_grounding_policy.py) tillför krav på att konkreta kommunikationsanpassningar förankras i kandidaten.

### Vilka data kan just Kommunikationsstrategi använda?

Kommunikationsstrategi är **ett fält i samma OpenAI-anrop som resten av Före intervju**. Därför har AI:n tekniskt tillgång till samma sammanlagda input för alla avsnitt:

1. **Rått normaliserat testunderlag:** för varje resultatpost med tillgänglig poäng byggs en läsbar rad med assessment/aktivitet, egenskap, STEN (om finns), STIVE (om finns), percentil (om finns). Även importerade historiska profiler kan normaliseras, men de har annan källdatastruktur. [purpose_fit.py, build_assessment_evidence](../../apps/core/ai/purpose_fit.py).
2. **Personlighetens Resultatsammanfattning:** kandidatunika, översatta beskrivningar till personlighetsdrag, tillagda av startup-policy.
3. **Tidigare AI-resultat:** AI Overview (summary, key_alignment, areas_to_verify, suggested_next_step, context_note); personlighetsinterpretation (interpretation, profile_dynamics, supportive_patterns, areas_to_explore, context_note); motivationstolkning (interpretation, engagement_conditions, areas_to_clarify, expectation_setting, context_note); färdighetstolkning (interpretation, considerations, context_note); svarsstilsvägledning (summary, how_to_interpret, recommended_approach, combination_note, context_note).
4. **Frågebank:** tillgängliga personlighet-, motivation-, färdighets- och svarsstilsfrågor med eventuell why och listen_for.
5. **Process:** valt syfte och de textfält som Talenas delade processkontext sammanställer.
6. **Instruktioner:** den aktuella SV/EN-adminprompten, tekniskt outputkontrakt och skyddade instruktioner om kandidatspecifik förankring.

**Ingår inte som förintervju-underlag:** generella intervjuanteckningar och sparade intervjusvar. **Finns ingen separat beräknad variabel:** ”andel värden i mitten”, spridningsprocent eller ett särskilt mått på hur ”spretig” hela personlighetsprofilen är. AI:n kan jämföra de enskilda poängen, men detta är en tolkning, inte en beräknad, verifierad statistik.

### Konsekvensskala, Värderingsspridning och Social önskvärdhet

Talenas svarsstilsbibliotek använder dessa källnamn för Sova-kompetenser om de finns:

| Svarsstil i Talena | Intern nyckel | Sova-kompetensnamn | Värde i separat svarsstils-AI |
|---|---|---|---|
| Social önskvärdhet | social_desirability | social desirability | Avrundat STEN 1–10 |
| Konsekvensskala / profilspridning | profile_spread | fillers | Avrundat STEN 1–10 |
| Värderingsspridning | ratings_spread | reliability | Avrundat STEN 1–10 |

Källa: [response_styles.py](../../apps/reports/libraries/personality/response_styles.py).

**Viktigt:** dessa värden ingår uttryckligen i den *separata* svarsstils-AI:ns indata när de finns. I AI-11 ingår den **tidigare genererade svarsstilstolkningen**, och dessutom den bredare råa bedömningslistan. Om Sova skickat ovanstående kompetenser med poäng och de finns kvar i den normaliserade listan kan även deras råa resultat bli del av AI-11. AI-11 har däremot **ingen särskild explicit sektion som alltid skickar alla tre svarsstilsnycklar med värden**. Detta måste verifieras i slutlig payload-testning för varje aktuell Sova-payload och historiskt underlag.

**Tolkning:** låg variation i personlighetsdrag och en svarsstilsindikator är inte samma sak. Varken Konsekvensskala eller Värderingsspridning ska utan särskilt validerat stöd beskrivas som ett automatiskt mått på tillförlitlighet, sanningsenlighet eller lämplighet. UI visar inte dessa två mått som värden: [personlighetsflikens mall](../../templates/customer/processes/partials/candidate_insights/personality/_results.html).

### Skyddat produktkontrakt för kommunikationsråden

AI:n uppmanas att framför allt använda **personlighets- och svarsstilsunderlag**, föreslå praktisk anpassning av ton, direkthet, tempo, reflektionstid, uppföljning och exempel, och inte förväxla detta med *vilka ämnen* som ska diskuteras. Om underlaget inte stöder en kandidatspecifik anpassning ska en tom lista vara tillåten. Det är en **instruktion till modellen, inte en garanti för kvalitet**. Källa: [pre_interview_grounding_policy.py](../../apps/core/ai/pre_interview_grounding_policy.py).

## 3. Förändringar sedan den äldre datainventeringen (2026-10-19)

Den tidigare [huvudinventeringen](talena-openai-datafloden.md) är en spårbar **snapshot av main-commit 57a6c9f3**, inte ett säkert nulägesintyg. Vid denna nya kodgranskning på main-commit f93d001c:

- [candidate_name_privacy.py](../../apps/core/ai/candidate_name_privacy.py) ersätter kända kandidatnamn och mejl i berörda prompttexter med neutral referens.
- [openai_client.py](../../apps/core/ai/openai_client.py) omsluter Chat Completions, Responses och Embeddings med central [pii_sanitizer.py](../../apps/core/ai/pii_sanitizer.py) och sanerar meddelanden/input före SDK-anropet; detta ersätter **inte** payloadtester eller juridisk verifiering.
- [apps/ai_chat/views.py](../../apps/ai_chat/views.py) blockerar befintliga fria chatt-endpoints.
- [apps/core/apps.py](../../apps/core/apps.py) installerar flera runtime-policies som ändrar effektiv prompt, bland annat råa testresultat för Före intervju och Resultatsammanfattning för andra personlighetspromptar.
- Chefrapportens AI-genererade **personlighetstexter** återanvänder personlighetstolkningsflödet och kan läsa intervjumaterial, medan numeriska/statiska chefsrapportdelar **inte är separata AI-promptar**. Det finns också kvar en äldre wellbeing_tips-blocknyckel trots UI-förändringar.

De äldre tabellrader som exempelvis anger ”Namn: JA” avser *promptbyggarens ursprungliga data*, inte ett nu verifierat påstående om **utgående identifierande text** efter maskering.

## 4. Krav innan vi kan säga ”exakt detta skickas till OpenAI”

Denna kodgranskning identifierar byggarna, ingående datakategorier och relevanta runtime-policies. Den räcker **inte** som bevis för byte-för-byte-innehåll. För att kunna erbjuda en verkligt exakt matris för varje adminprompt behöver #301 kompletteras med:

- **Testad outbound-payload per funktion:** fånga argumentsamlingen direkt före OpenAI-SDK:ns nätverksanrop **efter** alla runtime-wrappers och efter PII-sanerare; använd bara syntetiska testdata.
- **Tydligt schema per funktions-ID:** fält, typ, källa, exempel med syntetiska värden, villkor för saknat test, språk och om källa är råpoäng/tolkning/fritext.
- **Täckningsfall:** svenska/engelska, historisk/aktiv kandidat, delvis saknade tester, efter-intervju med/utan sparade frågesvar, omgenerering, Chefsrapport och svårtolkade specialfält som fillers/reliability.
- **Regressionsskydd:** nya eller ändrade datakategorier får inte börja skickas utan att test och den här matrisen uppdateras.
- **Separat driftkontroll:** modell, tillåten region, inställningar för lagring och vilken eventuell organisation/projektkonfiguration som faktiskt används i produktion.

Detta dokument är avsett som en läsbar produkt- och promptkarta. Den ursprungliga huvudrapporten är fortsatt den mer tekniska riskinventeringen, tills båda harmoniserats efter automatiska utgående-payloadtester.
