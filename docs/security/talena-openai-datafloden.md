# Talena – inventering av AI-anrop och dataflöden

**Dokumentstatus:** HISTORISK kodgranskad inventering v0.1 från 2026-10-19, **INTE aktuell slutlig payloadinventering eller verifierad i drift**. Uppdatering krävs i [#301](https://github.com/fridalannerstrom/talena-platform/issues/301).  
**Datum:** 2026-10-19  
**Källa:** `fridalannerstrom/talena-platform`, gren `main`, commit `57a6c9f3f79de481ff729719eec0eada36b63b02`  
**Ärende:** [#301 – Audit all OpenAI payloads and block personal-data regressions](https://github.com/fridalannerstrom/talena-platform/issues/301)  
**Dokumentägare:** Talena / Talent Qode; slutligt godkännande krävs av utsedd ansvarig.

> **Viktigt:** Detta dokument beskriver kodens möjliga dataöverföringar, inte uppmätta produktionsanrop. Slutligt utgående innehåll kan ändras av adminredigerade promptar, dynamiska indata och runtime-installerade promptpolicies. Dokumentet ska kompletteras med automatiska tester som fångar de exakta argumenten precis innan HTTP-anrop skickas. Ingen faktisk kandidatinformation behövs eller har använts i denna inventering.

### Viktig aktualitetsnotering 2026-10-22

**Läs inte de äldre raderna `Namn: JA` eller beskrivningar av kandidat-chatten som en beskrivning av Talenas nuvarande slutliga utgående API-payloads.** Dokumentet kartlägger *ursprungliga indata till promptbyggare* vid en äldre commit. Sedan dess har [#298](https://github.com/fridalannerstrom/talena-platform/issues/298) infört kandidatnamnsredaktion, [#300](https://github.com/fridalannerstrom/talena-platform/issues/300) en gemensam, lokal skyddsadapter före OpenAI SDK-anrop, och [#302](https://github.com/fridalannerstrom/talena-platform/issues/302) har avaktiverat chatten med 404 på dess endpoints. Dessa kontroller är kod-/regressionstestade, men **stängd chatt och en sanerare garanterar inte att all persondata saknas i varje enskild payload**.

Det krävs en **ny feature-för-feature-inventering av råpromptar och slutligt sanerade SDK-argument, syntetiska end-to-end-tester och produktionens faktiska OpenAI-konfiguration** innan detta kan användas som kundintyg. Se [#301](https://github.com/fridalannerstrom/talena-platform/issues/301), [#303](https://github.com/fridalannerstrom/talena-platform/issues/303) och [#304](https://github.com/fridalannerstrom/talena-platform/issues/304). De detaljerade tabellerna nedan bevaras för spårbarhet, inte som aktuellt sändningskontrakt.

## 1. Sammanfattning

Talena använder OpenAI för kandidatbaserade tolkningar, intervjufrågor, rapporttexter, AI-chattar, teaminsikter, en administrativ prompttestfunktion och embeddings till sökindex. Tre API-ytor identifierades i den granskade Python-koden: **Chat Completions**, **Responses** och **Embeddings**. Sova levererar underlagsdata, Talena bygger promptarna i Django och lagrar i flera fall resultaten i sin egen databas. **Pinecone är en separat mottagare** vid kunskapsindexering och RAG-sökningar.

**Verifierade uppmärksamhetspunkter:**

1. Flera kandidatpromptar innehåller uttryckligen för- och efternamn. Detta måste åtgärdas centralt enligt [#298](https://github.com/fridalannerstrom/talena-platform/issues/298).
2. Kandidat-chatten skickar namn, mejladress, kandidat-ID, projekt-ID och projekt-/bedömningsunderlag i JSON. Se [`apps/ai_chat/services/candidate_chat_context.py`](../../apps/ai_chat/services/candidate_chat_context.py) och [`apps/ai_chat/views.py`](../../apps/ai_chat/views.py).
3. Kandidatens egen AI-genererade resultattext får ett omfattande källobjekt som inkluderar `sova_activities`, `project_results` och `sova_reports` samt kandidatens namn. Rapportobjekt kan innehålla URL:er, och bör granskas för onödiga fält.
4. För `flexible` kan AI-generering ske när kandidatunderlaget byggs i en sidvy, inte bara vid ett särskilt Generate-klick. Samma vy skriver ut kandidatmejl och bedömningsunderlag med `print()`.
5. OpenAI-klienten väljer inget uttryckligt EU-endpoint, och användningen av `store` är inte explicit styrd i de identifierade anropen. Faktisk region, retention och ZDR är **inte verifierade** här; se [#303](https://github.com/fridalannerstrom/talena-platform/issues/303) och [#304](https://github.com/fridalannerstrom/talena-platform/issues/304).
6. Kommentarer, intervjunoteringar, projekt- och teambeskrivningar kan vara fritext. Identiteter kan finnas inuti sådan fritext även om fasta personnamnsfält tas bort.
7. Vissa genereringsfunktioner kan skicka en **andra** förfrågan för att reparera ogiltigt AI-JSON-svar. Ett klick är därför inte alltid exakt ett API-anrop.

## 2. Så läses inventeringen

- **Skickas:** fält/kategorier som byggs in i OpenAI-anropet enligt koden. Data som saknas för en viss kandidat utelämnas ofta.
- **När:** konstaterat anropstrigger i backend; faktisk frontendordning kan innebära att flera endpoints anropas efter varandra.
- **Risk:** kända personidentifierare eller fri text, inte en fullständig säkerhetsklassificering.
- **Ej samma sak:** att Talena lagrar AI-svaret i sin egen databas innebär inte att OpenAI lagrar samma svar. OpenAI:s leverantörslagring måste bedömas separat per endpoint/inställning.
- **Fältnamn i tabellerna:** är datakategorier, inte garanti för ett oföränderligt JSON-schema.

## 3. Gemensam OpenAI-konfiguration

| Aspekt | Kodverifierat läge | Källa / konsekvens |
|---|---|---|
| API-nyckel | `OPENAI_API_KEY` i miljövariabel | `apps/core/ai/openai_client.py:5–9` |
| Vanlig textmodell | `OPENAI_CHAT_MODEL`, fallback `gpt-4o-mini` | `apps/core/ai/openai_client.py:12–13` |
| Kandidat-chat Responses | `OPENAI_CHAT_MODEL`, fallback `gpt-5-mini` | `apps/ai_chat/views.py:288–295` |
| Embeddingsmodell | `OPENAI_EMBED_MODEL`, fallback `text-embedding-3-large` | `apps/core/ai/openai_client.py:16–17` |
| Region | Ingen explicit `base_url` i gemensamma klienten eller kandidat-chattklienten | Kräver kontroll av faktisk driftkonfiguration och eventuell flytt till EU |
| Lagring hos OpenAI | Ingen explicit `store`-parameter i genomgångna anrop | Betyder **inte** att retention är noll; utreds i #304 |
| Administratörspromptar | System-/användarprompten får ofta dynamiskt hämtad `get_ai_prompt_instructions` och/eller `get_ai_feature_prompt_instructions` | Innehåll kan skilja mellan SV/EN och installationer |
| Flera språk | SV/EN används i genereringsflödena | Måste testas separat |
| Egna sparade AI-resultat | T.ex. `ai_summary`, `ai_personality_interpretation`, `ai_post_interview_decision_support` | Talena-lagring som ska ingå i datakarta/gallring #310 |

Källor: [OpenAI-klient](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/openai_client.py), [kandidat-chatt](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/ai_chat/views.py), [gemensam kontext](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/shared_context.py).

## 4. Samtliga identifierade AI-funktionsvägar

### 4.1 Kandidatens testresultat, tolkning och intervjufrågor

| ID / funktion | När och varför | Underlag som skickas till OpenAI | Namn / fritextrisk | Källkod |
|---|---|---|---|---|
| AI-01 Kandidatsammanfattning | När sammanfattningsstreamen anropas efter tillgängliga tester; kan lämna sparat resultat utan nytt API-anrop. Sammanfattar testprofilen. | Kandidatens namn; valt processyfte; all tillgänglig bedömningsdata med kompetenser/poäng; processkontext (fält hämtade ur `ProcessRoleContext`). | **Namn: JA**. Kontext är fritext. | [`candidate_summary.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/candidate_summary.py#L239-L445), [vy](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/processes/views.py#L8031-L8160) |
| AI-02 Generella insikter / Flexible | I kandidatvyn när `process.purpose == "flexible"` och resultat finns; sammanfattar personlighets-, motivations- och färdighetsresultat utan rollmatchning. Kan köras vid sidvisning. | Kandidatens fullständiga namn; poäng för personlighet och motivation (även topp/lägst); verbal/logisk/numerisk percentil; statiska instruktioner. | **Namn: JA**. Separat risk: loggar mejladress och indata. | [vy](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/accounts/views.py#L1444-L1537), [service](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/reports/services/candidate_insights.py#L71-L169) |
| AI-03 AI-överblick | När AI-överblicken genereras för kandidat med tillämpligt processyfte; skapar sammanvägd profil. | Kandidatens namn; syfte; processkontext; tillgängliga Sova-resultat inklusive tolkningstext för personlighet; admininstruktioner. | **Namn: JA**. Projektkontext kan innehålla fritext. | [`purpose_fit.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/purpose_fit.py#L427-L550) |
| AI-04 Personlighetstolkning inkl. chefsrapport | När personlighetstolkning genereras, eller chefsrapportens personlighet behöver uppdateras. | Kandidatnamn; syfte/kontext; STEN/drag; motivationspoäng/definitioner när tillgängliga; indikator- och definitionsbibliotek; **generella intervjuanteckningar samt sparade svar/anteckningar kopplade till exakta intervjufrågor**; admininstruktioner. | **Namn: JA**. **Intervju-fritext: JA**. Särskilt viktigt flöde. | [`personality_interpretation.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/personality_interpretation.py#L296-L480), [chefsrapportsgenerering](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/processes/interview_question_notes.py#L350-L438) |
| AI-05 Frågor: personlighet | När intervjufrågor för personlighetsdrag genereras; användaren kan ha valt drag manuellt, annars AI-urval. | Kandidatnamn; syfte/kontext; personlighetsdrag och poäng/alternativt policybearbetad tolkningsgrund; eventuellt manuellt valda drag; admininstruktioner. **Ett reparationsanrop kan tillkomma** vid otillräckligt JSON. | **Namn: JA i grundbyggaren**. Slutligt underlag påverkas av startup-policies. | [`personality_questions.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/personality_questions.py#L322-L450), [reparation](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/personality_questions.py#L1110-L1155) |
| AI-06 Motivationstolkning | När motivationsfliken genereras; tolkar motivationsfaktorerna. | Kandidatnamn; syfte/kontext; motivationsfaktorer och exakta STIVE-poäng; biblioteksdefinitioner och admininstruktioner. | **Namn: JA**. Kontext är fritext. | [`motivation_interpretation.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/motivation_interpretation.py#L387-L455) |
| AI-07 Frågor: motivation | När motivationsfrågor genereras; föreslår frågor och observationer. | Kandidatnamn; syfte/kontext; motivationsfaktorer, poäng och definitioner; admininstruktioner. **Extra reparationsanrop** vid trasigt JSON. | **Namn: JA**. | [`motivation_questions.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/motivation_questions.py#L32-L100), [reparation](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/motivation_questions.py#L439-L535) |
| AI-08 Färdighetstolkning | När kognitiv/färdighetsflik genereras. | Kandidatnamn; syfte/kontext; tillgängliga percentiler för verbal, logisk och numerisk färdighet; admininstruktioner. | **Namn: JA**. | [`cognitive_interpretation.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/cognitive_interpretation.py#L139-L205) |
| AI-09 Frågor: färdighet | När färdighetsbaserade intervjufrågor genereras. | Kandidatnamn; syfte/kontext; verbala, logiska och numeriska percentiler; admininstruktioner. **Extra reparationsanrop** kan ske. | **Namn: JA**. | [`cognitive_questions.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/cognitive_questions.py#L33-L100), [reparation](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/cognitive_questions.py#L738-L786) |
| AI-10 Svarsstilsvägledning | När vägledning kring personlighetens svarsstilar genereras; kräver giltiga indikatorer. | Kandidatnamn; syfte/kontext; svarsstilsindikatorer, tekniska nycklar och avrundade STEN, eventuellt profilkontrastanalys, admininstruktioner. | **Namn: JA**. | [`response_style_guidance.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/response_style_guidance.py#L73-L237) |
| AI-11 Inför intervju | När syntesen inför intervju genereras. Bygger på redan sparade Talena-tolkningar, inte bara råpoäng. | Kandidatnamn; syfte/kontext; tidigare genererade överblickar/tolkningar, motivation, personlighet, färdighet, frågor och tillgängliga textunderlag enligt evidensbyggaren; admininstruktioner. | **Namn: JA**. Kan innehålla personliga uppgifter som redan finns i AI-genererad text. | [`decision_support.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/decision_support.py#L219-L285), [prompt](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/decision_support.py#L680-L750) |
| AI-12 Efter intervju: äldre sammanhållen syntes | När äldre sammanhängande post-intervju-endpoint anropas (kvarvarande kodväg). Tolkar sparade bedömningar mot intervjuunderlag. | Kandidatnamn; syfte/kontext; sparade tolkningar; `ai_pre_interview_decision_support`; allmänna intervjuanteckningar; frågespecifika svar/anteckningar via runtime-policy; admininstruktioner. | **Namn: JA**; **intervju-fritext: JA**. | [`decision_support.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/decision_support.py#L2754-L2880), [runtime-policy](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/post_interview_question_evidence_policy.py#L327-L447) |
| AI-13 Efter intervju: separat innehållsflik (fyra varianter) | När en flik genereras/omgenereras eller alla flikar sammanställs, med egna API-anrop per flik: `overall_picture`, `interview_summary`, `explore_further`, `wellbeing_tips`. | Kandidatnamn; processyfte och kontext; sparade bedömningstolkningar där flikens logik tillåter; **generella intervjuanteckningar**; **exakta intervjufrågor med sparade svar/anteckningar**; flikspecifika adminpromptar. `interview_summary` skickar inte bedömningssyntes i det fältet. | **Namn: JA**; **intervju-fritext: JA**. Ett "generera alla" kan utlösa flera OpenAI-anrop. | [`decision_support.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/decision_support.py#L3258-L3409), [orchestrering](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/processes/interview_question_notes.py#L470-L715) |
| AI-14 Kandidatens egen resultattext | Vid skapande/återanvändning av kandidatsnapshot, bland annat när Sova meddelar att testerna slutförts och resultatdelning är påslagen. Omformulerar till kandidatvänlig text. | **För- och efternamn**; processyfte, befattning och processkontext; tillgängliga testresultat; **hela `sova_activities`, `project_results` och `sova_reports`**; tidigare genererade kundtolkningar; adminpromptar. | **Namn: JA**. **Särskild risk för onödigt bred JSON och rapport-URL:er**; kräver fältnivågranskning. | [`interpretation.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/candidate_results/interpretation.py#L193-L243), [anrop](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/candidate_results/interpretation.py#L515-L546), [webhook](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/integrations/views.py#L503-L525) |

**Gemensam kandidatkontext:** `build_shared_ai_context()` returnerar både kandidatobjektet och namn, inklusive möjlighet att använda kandidatens mejladress som fallback för visningsnamn. Själva objektet skickas inte automatiskt till OpenAI; enskilda promptbyggare avgör vad som tas med. [Källa](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/shared_context.py#L168-L225).

### 4.2 Team, chatt och admin

| ID / funktion | När och varför | Underlag till OpenAI | Risk / anmärkning | Källkod |
|---|---|---|---|---|
| AI-15 Teaminsikt | När användare med behörighet väljer att skapa en teaminsikt via POST. | Teamets mål, fri beskrivning, kontext, medlemsantal, antal med/utan bedömning samt **aggregerade genomsnitt per teamstil**; admininstruktioner. | Individuella kandidat-ID:n finns i lokal fingerprint/signaturdata men **ingår inte i `prompt_context` som skickas**. Teambeskrivning/kontext är fritext och kan innehålla identifierare. | [`ai_insights.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/teams/ai_insights.py#L43-L122), [anrop](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/teams/ai_insights.py#L147-L195), [vy](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/teams/team_report_views.py#L539-L569) |
| AI-16 Allmän AI-chatt med RAG | När inloggad användare skickar meddelande till `chat_api`. | Användarens **hela frågetext** till embeddingssökning samt, separat, som `USER MESSAGE` i Chat Completions tillsammans med Pinecone-hämtat kunskapsinnehåll och systeminstruktioner. | Fritext kan innehålla kandidatdata; första överföringen kan vara **embedding**, innan textsvar genereras. Kodens standard `scope="base"`. | [`ai_chat/views.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/ai_chat/views.py#L47-L71), [`chat.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/chat.py#L14-L88), [`rag.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/rag.py) |
| AI-17 Kandidatrelaterad AI-chatt | När chattstream begärs med process- och kandidat-ID. | **Namn, mejladress, kandidat-ID**, process-ID, projektnamn/syfte, eventuell processkontext, Sova-bedömningsresultat, projektresultat, frågetext samt administratörsinstruktioner. Historiska kandidater har motsvarande importerade profildata. | **Kritiskt:** direkta identifierare. Använder **Responses API** och en annan standardmodell än gemensamma klienten. Avses stängas av enligt #302. | [`candidate_chat_context.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/ai_chat/services/candidate_chat_context.py#L94-L263), [`views.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/ai_chat/views.py#L75-L295) |
| AI-18 Admin: Prompt Playground | När administratör testar osparad prompt i adminvyn. | Fördefinierad exempelkandidat och exempelbedömningsdata; prompttext och eventuellt **adminredigerad process-/kontextfritext**; språkinstruktioner. | Ingen riktig kandidatdata enligt funktionens design, **men** administratören kan klistra in personuppgifter i fritexten. | [`prompt_playground.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/prompt_playground.py#L803-L893), [anrop](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/prompt_playground.py#L994-L1168), [vy](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/views.py#L870-L892) |

### 4.3 Embeddings och Pinecone

| ID / funktion | När och varför | Data till OpenAI | Ytterligare lagring / risk | Källkod |
|---|---|---|---|---|
| AI-19 RAG-sökfråga → Embeddings | När `retrieve_context()` används av den allmänna AI-chatten; gör ett embedding-anrop per sökning/index, två om `scope="both"`. | Användarens sökfråga som **rå text** i `input` till `embeddings.create`. | Den resulterande vektorn skickas vidare som en **Pinecone-query**; kunskapsutdrag hämtas sedan tillbaka till Chat Completions. | [`rag.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/rag.py#L6-L35), [`chat.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/chat.py#L27-L54) |
| AI-20 Kunskapsindexering → Embeddings | Vid `KnowledgeEntry`-save, om inte tidsbegränsad spärr slår till; används för att indexera dokument. | Varje textchunk av `KnowledgeEntry.content` till OpenAI Embeddings, normalt högst 1 200 tecken per chunk. | Vektor **och originalchunkens text** sparas sedan som Pinecone-metadata (`text`, `title`, `source`, `tags`, `doc_id`). `ingest.py` väljer dessutom `tq`-index efter initialt indexval; kontrollera detta avseende avsett dataflöde. | [`signals.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/knowledge/signals.py#L9-L28), [`ingest.py`](https://github.com/fridalannerstrom/talena-platform/blob/57a6c9f3f79de481ff729719eec0eada36b63b02/apps/core/ai/ingest.py#L29-L89) |

**Externt men inte ett OpenAI-anrop:** kommunikation mellan Talena och Sova, Azure-lagring, e-postutskick och Pinecones egna API-anrop. Dessa ska finnas i den större datakartan #310.

## 5. Hur många HTTP-anrop sker?

Det går **inte** att utläsa ett fast antal per användarklick. Överföring sker när respektive Python-funktion faktiskt anropas och när dess villkor uppfylls:

- Streaming och cache: flera kandidatendpoints återger sparad text vid `completed` och undviker nytt OpenAI-anrop tills materialet blir `outdated` eller omgenereras.
- Efter intervju: de fyra separata innehållsblocken genereras var för sig, även om användaren väljer ett övergripande genereringsflöde.
- Reparationsanrop: personlighet-, motivation- och färdighetsfrågor har möjliga extra `chat.completions.create`-anrop när AI-svaret inte uppfyller formatkraven.
- RAG: texten i frågan kan skickas först till Embeddings och sedan till Chat Completions.
- Kandidatresultat: Sova-webhook med `completed` och aktiverad kandidatresultatdelning kan påbörja resultatgenerering och därefter mejlutskick.
- Flexible: `apps/accounts/views.py` innehåller en direkt genereringsgren i kandidatunderlagsbyggaren, **utan synligt sparad-resultat-skydd i den grenen**. Antal upprepningar måste kontrolleras.
- Administrativa promptändringar, språkbyte, återgenerering och ändrade testdata kan leda till ny AI-generering.

## 6. Vad skickas INTE automatiskt?

Detta är avgränsningar i **vissa specifika kodvägar**, inte generella garantier:

- Teaminsikternas OpenAI-prompt inkluderar aggregerade teamresultat. Kandidat-ID:n i hashunderlaget skickas inte i den aktuella prompten.
- Embeddings-sökningen skickar frågetext, inte hela Pinecone-indexets databas; Pinecone-fragmenten returneras senare i chattprompten.
- Den vanliga kandidatsammanfattningen sammanställer Sova-kompetenspoäng i läsbar text; den skickar inte per automatik hela Sova-payloaden.
- Prompts som bara skickar `name` plus bedömningspoäng skickar inte kandidatens mejladress explicit, men **fritext och tidigare genererade texter kan fortfarande innehålla identifierare**.
- Inga utgående API-argument hämtas här från riktiga kandidater; varken produktionsloggar, nätverkstrafik eller databas har granskats.

## 7. Kända risker och föreslagna åtgärder

| Prioritet | Fynd | Rekommenderad åtgärd | Ticket |
|---|---|---|---|
| P0 | Direkta kandidatnamn i många promptbyggare | Exkludera namn från backend-payloads; neutralt subjektnamn, säkra tester SV/EN | [#298](https://github.com/fridalannerstrom/talena-platform/issues/298) |
| P0 | Kandidatrelaterad chatt skickar namn, mejl, ID och omfattande data | Stäng av UI **och direktanrop i backend** före lansering; verifiera spärr med test | [#302](https://github.com/fridalannerstrom/talena-platform/issues/302) |
| P0 | Fritext i intervju- och projekt-/teamkontext | En central sanering före alla anrop; svensk/engelsk NER och regler; fail closed vid fel | [#300](https://github.com/fridalannerstrom/talena-platform/issues/300) |
| P0 | Ingen gemensam whitelist/allowlist för AI-innehåll | Central klient/gateway, fältschema per funktion, tester av effektiva promptar **efter runtime-policies** | [#301](https://github.com/fridalannerstrom/talena-platform/issues/301) |
| P0 | Kandidatportal skickar bred `assessment_evidence` inkl. `sova_reports` | Bygg minimerat evidensschema; tillåt bara motiverade poäng och text; exkludera rapport-URL:er och metadata utan behov | #301 / #298 |
| P0 | Debug-`print` exponerar kandidatmejl och bedömningsunderlag i `accounts/views.py` | Ta bort; metadata-/ID-baserad strukturerad loggning utan rådata | [#305](https://github.com/fridalannerstrom/talena-platform/issues/305) |
| P0 | Otydlig leverantörslagring och Responses `store`-beteende | Verifiera per endpoint, projekt och modell; aktivera rätt inställningar efter godkännande | [#304](https://github.com/fridalannerstrom/talena-platform/issues/304) |
| P0 | EU-region och avtalsgrund ej bekräftad | Verifiera företaget, EU-endpoint, tilläggsavtal, DPA, modeller och faktisk driftmiljö | [#303](https://github.com/fridalannerstrom/talena-platform/issues/303) |
| P0 | AI kan triggas när flexible-kandidatunderlag visas | Flytta till kontrollerad on-demand-generering eller spara/cacha resultat med tydlig omgenereringslogik | #301 |
| P0 | Inehåll i fri text kan skickas trots UI-varningar | Tydliga svenska/engelska inline-texter, dock ej ersättning för teknisk sanering | [#299](https://github.com/fridalannerstrom/talena-platform/issues/299) |
| P1 | Pinecone-lagring av originalchunks och tvångsval av `tq`-index | Granska datatyper, tillåtna källor, Pinecone-region och felaktigt indexval | [#310](https://github.com/fridalannerstrom/talena-platform/issues/310) |
| P1 | Många dynamiska, runtime-installerade promptwrappers | Regressionstesta sammansatta **slutliga** promptar och håll dokumentet synkat med kodändringar | #301 |
| P1 | Modell, region, anropstyp och dokumenterad källinformation saknas i sammanhållen spårbarhet | Minimal strukturerad AI-auditlogg med lämplig retention utan fulla prompts | #305 / #310 |

## 8. Viktigt om runtime-policies och versionsspecifik kod

`apps/core/apps.py` installerar många policywrappers vid Django-start. De kan ändra den prompt som slutligen skickas till OpenAI. Exempelvis har personlighetens frågegenerering separata regler för valda drag, tekniska bevis och frågeprecision. `decision_support.py` innehåller dessutom senare funktionsdefinitioner med samma namn som tidigare definitioner, och en post-intervju-policy som wrappar dessa funktioner.

**Konsekvens:** källkodsraderna ovan anger ursprungligt underlag och kända datafält. **Slutlig byte-för-byte-payload är inte verifierad** förrän anropen fångats i applikationens startade runtime med samma adminpromptar som gäller i drift. Ändringar i admin kan ge ytterligare indata.

## 9. Färdigställ #301: plan för automatisk verifiering

1. **Lägg central datamodell/gateway:** alla OpenAI-utrop via ett gemensamt adapterlager, även direkt `OpenAI()` i kandidat-chatten och Embeddings. Dokumentera feature-ID, endpoint, modell, källkategorier och tillåtna fält.
2. **Skapa anropsinventering i test:** mocka SDK-anropen (`chat.completions.create`, `responses.create` och `embeddings.create`) och fånga slutliga `messages`, `instructions` och `input` utan nätverk.
3. **Kör representative fall:** svensk/engelsk; aktiv/historisk kandidat; resultat med/utan personlighet/motivation/färdighet; efter intervju med generella och frågespecifika anteckningar; team; kandidatportal; admins promptlekplats.
4. **Testa verkliga riskfält:** strängar som `Anna Andersson`, mejl, telefonnummer, tillhörande ID, orter och falska positiva matchningar. Testa särskilt fritext, PDF-/rapport-URL:er samt metadata.
5. **Testa villkor:** cache, språkbyte, omgenerering, fel/retry, sidvisning med flexible, Sova-webhook och avstängd kandidat-chatt.
6. **Testa felhantering och loggar:** sanitiseringsfel ska inte tyst fortsätta; fel/logg får inte exponera prompts eller persondata.
7. **Skapa maskinläsbar matris:** ett testat manifest av alla aktiva utgående datakategorier, uppdaterat i CI vid nya AI-funktioner.
8. **Komplettera driftverifiering:** OpenAI-organisations-/projektinställningar, modeller, EU, datalagring och avtal; lägg inte hemligheter eller kandidatdata i PR eller auditdokument.

### Klart-kriterier för dokumentdelen

- [x] Identifierade OpenAI-SDK-anrop och huvudsakliga kodvägar på granskad `main`-commit.
- [x] Triggers, syfte, datakategorier, direkta identifierare och fritextrisker dokumenterade.
- [x] Befintliga risker och ansvariga tickets angivna.
- [ ] Faktiska slutliga utgående payloads fångade i automatiska tester.
- [ ] Slutliga promptar efter samtliga startup-policywrappers verifierade.
- [ ] Produktionens endpoint, modell, nyckelägarskap, region och retention kontrollerade.
- [ ] Inventeringen godkänd, versionshanterad och uppdaterad vid kodförändringar.

**Slutsats:** #301 är **påbörjad, inte stängningsklar**. Denna version är underlag för implementation och en testbaserad slutverifiering, inte ett intyg om GDPR-efterlevnad.
