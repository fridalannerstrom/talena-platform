# Talena AI-dataflöden: Efter intervju, Chefsrapport och Teaminsikter

**Datum:** 2026-10-22  
**Ticket:** [#301](https://github.com/fridalannerstrom/talena-platform/issues/301)  
**Status:** Kodgranskad **teknisk delkartläggning** på aktuell `main` och syntetiska mock-tester. **Inte** slutligt runtime-/produktionsintyg. Läs ihop med [AI-dataflöden v0.2](./301-ai-datafloden-v02.md) och [maskinläsbar SDK-lista](./301-openai-callsites.json).

## A. Efter intervju: vilka sparade tolkningar återanvänds?

Funktionen `apps.core.ai.decision_support.build_pre_interview_evidence(owner)` sammanställer **selektivt** tidigare sparade Talena-texter, inte varje JSON-fält automatiskt. Det är ett underlag som sedan kan bäddas in i nya AI-prompter.

| Källa i `owner` | Återanvända JSON-fält i koden | Användning |
|---|---|---|
| `ai_purpose_fit` (AI Overview) | `summary`, `key_alignment`, `areas_to_verify`, `suggested_next_step`, `context_note` | Övergripande AI-bedömning |
| `ai_personality_interpretation` | `interpretation`, `profile_dynamics`, `supportive_patterns`, `areas_to_explore`, `context_note` | Personlighet och relationer mellan drag |
| Sova-motivation via `_build_motivation_assessment_evidence` | Tolkat ur aktuella testresultat, med valda toppfaktorer och relevanta STIVE-värden | **Inte** en tidigare AI-text, utan separat testunderlag |
| `ai_motivation_interpretation` | `interpretation`, `engagement_conditions`, `areas_to_clarify`, `expectation_setting`, `context_note` | Tidigare motivationstolkning |
| `ai_cognitive_interpretation` | `interpretation`, `considerations`, `context_note` | Tidigare färdighetstolkning |
| `ai_response_style_guidance` | `summary`, `how_to_interpret`, `recommended_approach`, `combination_note`, `context_note` | Tidigare svarsstilsvägledning |
| Sparade frågebanker | `questions[].question`, `why`, `listen_for` för personlighet, motivation, färdighet och svarsstilar | Returneras i `question_text`; **inkludering i ett specifikt OpenAI-anrop måste kontrolleras separat**, eftersom en prompt kan använda enbart `evidence_text` |

**Ytterligare runtime-lager:** I Talenas startkonfiguration kan `apps/core/ai/pre_interview_raw_evidence_policy.py` *wrappa* `build_pre_interview_evidence` och lägga **normaliserade råa Sova-testresultat** från `apps/core/ai/purpose_fit.build_assessment_evidence(owner)` *före* de sparade AI-tolkningarna i `evidence_text`, med rubriken `Assessment results`. Detta gäller även när råa assessment-resultat inte ser ut att läsas i den ursprungliga funktionens kod. Därför måste en slutlig payloadinventering ta hänsyn till installerade runtime-policys, inte bara själva promptbyggaren. Regressionstestet simulerar uttryckligen det här lagret.

**Viktig gräns:** `build_pre_interview_evidence` returnerar både `evidence_text` och `question_text`. I vissa Efter intervju-promptar används *bara* `evidence_text`, medan frågor och svar också kan komma via ett separat frågespecifikt källflöde. Lista därför inte en sparad frågebank som automatiskt skickad i alla anrop.

### Efter intervju: separat sektion (`stream_post_interview_content_block`)

- Källor: processändamål och process-/rollkontext från `build_shared_ai_context`; **allmänna intervjuanteckningar**; frågespecifika svar/noteringar **ihop med exakt frågetext** från `get_post_interview_note_evidence`; global och sektionens särskilda adminprompt.
- För `overall_picture` och andra relevanta sektioner används `build_pre_interview_evidence(...)["evidence_text"]` med tidigare tolkningar och testunderlag.
- För `interview_summary` **utesluts tidigare bedömningstolkningar uttryckligen ur sektionens ASSESSMENT INDICATIONS**, så att intervjusammanfattningen fokuserar på intervjumaterialet. Process-/rollkontext och intervjuunderlag finns fortfarande.
- Slutprompten passerar först `redact_candidate_name` för kända namn/mejl och därefter `PrivacySafeOpenAI` för lokal PII-sanering. Enkeluppgifter och indirekt identifiering kan fortfarande missas av regelbaserad sanering.
- De gamla `build_post_interview_decision_support_prompt`-/`stream_post_interview_decision_support`-flödena lever också kvar för kompatibilitet. Ett funktionsnamn definieras dessutom två gånger i källfilen; en tidigare definition är överlagrad. Fält- och körningsaudit måste skilja aktiv rutin från legacy.

## B. Chefsrapport: personlighet, vad AI faktiskt får

Chefsrapportens personlighetstexter genereras enligt granskad kod i `apps/core/ai/personality_interpretation.py` via `stream_personality_interpretation` och `build_personality_interpretation_prompt`. Samma generering hanterar fältet `manager_report_personality` med sex separata admininstruktioner:

| Tema | AI-delar |
|---|---|
| Leda och arbeta med andra | `manager_personality_leading_and_working_with_others_testbild` och `..._candidate_describes` |
| Organisering och tankemönster | `manager_personality_organising_and_thinking_patterns_testbild` och `..._candidate_describes` |
| Interaktion och känslohantering | `manager_personality_interaction_and_emotion_management_testbild` och `..._candidate_describes` |

Indata i den **gemensamma personlighetsgeneratorn**: personlighetstestresultat, valfria motivationsresultat, statiska indikatorbeskrivningar per tema, processkontext, allmänna intervjuanteckningar och frågespecifika sparade svar med frågetext. Admininstruktioner och språkinstruktioner tillkommer.

**Tolkning för administratörer:** Testbild och Kandidaten beskriver får därmed tillgång till det material som sätts samman i den gemensamma personlighets-prompten. De är inte sex separata OpenAI-API-anrop enligt denna källa. Enskilda instruktioner begränsar hur respektive del *ska användas*, men tekniken begränsar inte automatiskt hela payloadens innehåll till en enda temarad. Det är viktigt för dataminimering och juridisk granskning.

Färdighetsboxar och motivationsboxar i chefsrapportens UI kan även bestå av statiska beräkningar/definitioner; **allt som visas i rapporten skickas inte nödvändigtvis till OpenAI**. Den exakta rapportens övriga flöden inventeras separat.

## C. Teaminsikter: fält som skickas kontra lokalt metadata

I `apps/teams/ai_insights.py` bygger `build_team_insight_input` ett `prompt_context`. Generatorn `generate_team_insight` skickar följande via Chat Completions:

| Fält i `prompt_context` | Kategori |
|---|---|
| `team_goals` | Valda teammål |
| `team_description` | Användarskriven fri text (PII-risk) |
| `team_context` | Användarskriven fri text (PII-risk) |
| `team_member_count` | Antal personer |
| `members_with_usable_assessment_results` | Antal med tillgängliga testresultat |
| `members_missing_usable_assessment_results` | Antal utan användbara resultat |
| `team_style_summary[]` | `style`, `team_average`, `members_with_score`: aggregerade resultat, inte direkt person-ID |

**Skickas inte i denna AI-text enligt nuvarande kod:** `member_ids`, `candidate_id`, enskilda personers testvektorer, Sova-inbjudnings-ID:n, `source_metadata`, `signature_data` och `source_signature`. Dessa används i Talena för lokal beräkning/versionering och lagring.

**Integritetsrisk:** Även aggregerade teamdata kan indirekt röja individer i små team, särskilt tillsammans med fri text. Skyddet i `PrivacySafeOpenAI` maskerar vissa namn/kontaktuppgifter men gör inte sådana aggregat anonyma. Kundens lagliga ändamål, behörigheter och eventuell minsta teamstorlek kräver egen bedömning.

## D. Testbevis och begränsningar

Nya syntetiska regressionstester i `apps/core/test_ai_payload_interview_team.py`:

- Verifierar selektiva tidigare AI-textfält i `build_pre_interview_evidence` och att ett påhittat ovidkommande internt fält inte automatiskt inkluderas.
- Kör verklig Efter intervju-generator på sv/en för `overall_picture` respektive `interview_summary`, med mockad underlagsinsamling och **verklig central saneringsadapter**; kontrollerar skickade `messages` efter sanering samt sektionsskillnaden i evidens.
- Kör personlighetsgeneratorns slutliga SDK-gräns med påhittad chefstext och kända identifierare. Detta verifierar **sändningsmaskering**, inte hela chefsrapportens underlagsbyggare med alla sex verkliga adminpromptar.
- Kör teaminsiktsgeneratorn med mockat aggregerat underlag och riktiga SDK-wrappern; kontrollerar att PII i teamfri text maskeras och att lokalt signatur-/ID-metadata inte skickas till mock-SDK. Det verifierar **generatorns gräns**, inte hela databasaggregeringen eller tenantbehörigheter.
- Inga riktiga API-nycklar eller kandidater, inga nätverksanrop.

### Fortsatt att göra innan #301 stängs

- [ ] Final-payloadtester för samtliga återstående aktiva generatorer, JSON-reparationer/retry och adminprompt-overrides.
- [ ] Mer omfattande end-to-end med syntetiska äkta Django-objekt och källdata för Chefsrapportens sex adminprompter, fråga/svar och teamets dataaggregering.
- [ ] Kontroll av vem som faktiskt får generera/omgenerera team- och kandidatrapporter över olika kundföretag (#309).
- [ ] Dataminimeringsbeslut för återanvända AI-texter, minsta teamstorlek och onödig fritext/metadata.
- [ ] Verifiering av Pinecone/extern loggning och OpenAI:s region, retention/DPA (#303/#304, inväntar chefens kontobeslut).
- [ ] Verifierad körning av CI och relevant dev-/stage-test. Ticket #301 stängs **inte** av denna delkartläggning.
