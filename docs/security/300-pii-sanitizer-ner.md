# #300: Lokal PII-sanering och NER före AI-anrop

**Status:** Första implementation för granskning. **Inte godkänd som full GDPR-anonymisering.**  
**Påverkar:** OpenAI Chat Completions, Responses och Embeddings; därmed kandidatrapporter, AI-tolkningar, teaminsikter, admin-prompttest och RAG-embeddings som använder Talenas gemensamma SDK-klient.

## Vad som faktiskt görs i kod

All befintlig kod som använder `get_openai_client()` går nu via en central server-side adapter i `apps/core/ai/openai_client.py`. Den kör `sanitize_ai_payload()` *innan* SDK-anropet. Den avbryter anropet utan nätverkstrafik om saneringen kraschar, saknar meddelande/input eller får en okänd typ. Detta gäller även streaminganrop: saneringen sker före att streamen öppnas.

Saneraren finns i `apps/core/ai/pii_sanitizer.py` och körs lokalt inom Talenas backend:

| Entitet | Standard | Exempel | Ersättning |
|---|---|---|---|
| E-postadress | Regex, på | `anna.svensson@example.se` | `[EMAIL]` |
| Svenska personnummer, sex-/åttasiffrigt datum med suffix | Regex, på | `19900101-1234` | `[PERSONAL_ID]` |
| Svenska telefonnummer inklusive +46 | Regex, på | `070-123 45 67` | `[PHONE]` |
| Vissa internationella telefonnummer | Regex, på | `+1 415 555 2671` | `[PHONE]` |
| Namn i formen två/tre versal-inledda ord | Heuristik, på | `Anna Svensson` | `[PERSON]` |
| Personnamn upptäckta av lokal NER | Valfri spaCy-modell per språk | `Freja Norrström` | `[PERSON]` |
| Organisationer och platser upptäckta av NER | Valfria per inställning, **av** i standardläge | `Acme Technologies` / `Sundsvall` | `[ORGANIZATION]` / `[LOCATION]` |

Det befintliga skyddet som ersätter **aktuell kandidats kända namn/mejl** med `CANDIDATE_A` ligger också kvar (#298).

Saneraren kopierar JSON-strukturen utan att ändra fältnamn, numeriska testresultat eller booleska värden. Textsträngar som innehåller en **giltig JSON-lista eller JSON-objekt** parsas först; endast textvärden saneras. Exempelvis `STEN 8`, `Customer Service STIVE 4`, `Social Desirability` och `Talent Qode` skyddas i regexheuristiken. Varningar i UI finns separat (#299), medan kandidat-/personchatten förblir stängd (#302).

## Lokal NER: installation och drift

Det finns **ingen automatisk nedladdning eller moln-API** för namndetektion. spaCy-modeller laddas enbart från filer installerade på Talenas backend. Detta är avsiktligt så kandidatuppgifter inte skickas till en fjärde part.

Den statistiska NER-delen **är valfri och inte aktiv enbart genom denna PR**, eftersom nuvarande `requirements.txt` inte innehåller spaCy eller modellpaket. För aktivering behöver vi:

1. Välja, utvärdera och godkänna svensk och engelsk lokal spaCy-pipeline med faktiska `PER`/`PERSON`-entiteter.
2. Installera `spacy` och respektive **versionlåst språkmodell som en del av det reproducerbara deploybygget** (t.ex. interna wheel-filer) och testa kompatibilitet med Python på Azure. Kör inte nedladdningskommandon i varje request.
3. Ställa in `TALENA_PII_NER_SV_MODEL` och `TALENA_PII_NER_EN_MODEL` till lokala modellnamn. Båda kan vara aktiva samtidigt. Varning: att bara sätta miljövariabeln **utan att modellen finns lokalt gör att AI-anrop stoppas**, vilket är avsikten.
4. Om organisationer eller platser bedöms vara onödiga i en viss funktion, aktivera `TALENA_PII_MASK_ORGANIZATIONS=1` respektive `TALENA_PII_MASK_LOCATIONS=1`. Detta kan annars ta bort relevant roll- eller teamkontext.
5. Mäta precision/recall på svensk och engelsk, anonymt skapad testdata (t.ex. vanliga och ovanliga namn, kombinationer med testtermer), belastning, minnesanvändning och latens; därefter göra en dataskydds-/lanseringsbedömning.

Den deterministiska regexdelen fungerar **utan modellinstallation**. Den kompletterar NER men har lägre träffsäkerhet.

## Risker och begränsningar

- **Pseudonymisering, inte juridisk anonymisering.** En kandidat kan fortfarande identifieras indirekt genom en unik befattning, händelse, arbetsgivare, datum, strukturerade testresultat eller andra uppgifter.
- **Reglerna missar** exempelvis ensamma förnamn, vissa namn i gemener, ovanliga telefonformat, gatuadresser, personal-/ärendenummer och indirekta identifierare. Heuristiken kan också av misstag maskera två versal-inledda ord som inte är personnamn.
- Namn i JSON-**nycklar** eller andra tekniska metadata maskeras inte avsiktligt för att inte bryta kontrakt. Även t.ex. numeriska interna ID:n skickas vidare om de redan finns i AI-underlag. Minska sådana fält vid källan (#301).
- Ingenting är en garanti för att alla namn eller känsliga uppgifter stoppas. Man behöver både dataminimering, varningar, backend-spärrar, testning och avtal/retention/EU-hantering (#303, #304).
- Övriga tredjepartstjänster, däribland Pinecone-metadata vid dokumentimport, hanteras inte av OpenAI-adaptern. Kartlägg och minimera dessa i separat underlag (#301/#310).
- `sanitize_ai_payload` accepterar bara vanliga JSON-typer för OpenAI-payload; nya SDK-metoder, verktygsanrop och multimodala objekt måste granskas och få explicit stöd. Koda inte en direkt `OpenAI()`-genväg.
- Text över 2 miljoner tecken per fält stoppas för att begränsa belastning. Sanitizer-fel returnerar generiska meddelanden utan att logga rå prompttext.

## Testning och lanseringsgrind

Testfil: `apps/core/test_ai_pii_sanitizer.py`. Den täcker sv/en, namn/e-post/telefon/personnummer, oförändrade STEN/STIVE-värden, strukturerad JSON, de tre OpenAI-API-typerna, lokalt NER-stubtest och **fail-closed vid fel**. En kodkontroll söker efter andra direkta `OpenAI()`-instanser i appkoden.

- [x] Gemensam central adapter för nuvarande OpenAI-klientanrop.
- [x] Regelbaserad lokal sanering.
- [x] Kodstöd för lokala svenska och engelska NER-modeller.
- [x] Regressionstester skrivna.
- [ ] GitHub Actions grönt.
- [ ] Svensk och engelsk modell vald, installerad, utvärderad och aktiverad i målmiljö, eller formellt dokumenterat avsteg/riskacceptans.
- [ ] QA med representativa kandidattestfall och behörighets-/rapportfunktioner i dev/stage.
- [ ] Kontroll att ingen viktig testdefinition/poäng förändras; inventera även framtida API-klienter.
- [ ] Uppföljning av Pinecone-upserts och källpayloads i #301/#310.

**Slutsats:** Detta är en säkerhetsförbättring och kodgrund för lokal NER, men #300 bör inte markeras som helt slutlevererad för lansering förrän modellval och uppföljande dataskyddstester är beslutade och utförda.
