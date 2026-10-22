# Talena – AI-dataflöden v0.2: källkod, SDK-gräns och testbevis

**Datum:** 2026-10-22  
**Ärende:** [#301](https://github.com/fridalannerstrom/talena-platform/issues/301)  
**Status:** **DELLEVERANS. Inte ett slutligt intyg om alla payloads eller om produktionsmiljön.**  
**Utgångspunkt:** Kodgranskning på `main` efter #298, #299, #300 och #302. Endast syntetiska/maskerade testdata. Inga produktionskandidater, riktiga OpenAI-anrop eller API-nycklar används.

## 1. Vad är säkert verifierat?

1. Den gemensamma OpenAI-klienten i `apps/core/ai/openai_client.py` passerar genom `PrivacySafeOpenAI`. Chat Completions, Responses och Embeddings har central sanering före SDK-anrop. En felaktig/saknad payload blockeras före sändning.
2. Det finns **22 syntaktiska OpenAI-SDK-anrop i 16 Python-moduler** under `apps/`, inklusive ett **inaktivt legacy-chat-anrop**, JSON-reparationsanrop och en gammal överlagrad funktionsdefinition. Dessa är **källkodsanrop, inte 22 separata aktiva slutanvändarfunktioner**.
3. Maskinläsbar källkodslista finns i [`301-openai-callsites.json`](./301-openai-callsites.json). Testet `apps/core/test_ai_payload_inventory.py` skannar faktiska Python-AST:er, jämför samtliga kodvägar med listan och fångar oanmälda nya/ändrade anrop i CI.
4. Samma test anropar **faktiska Talena-genereringsfunktioner med syntetiska data**, men ersätter OpenAI-klienten med en SDK-mock. Det kontrollerar argumenten **efter** Talenas gemensamma sanerare och **före** den simulerade OpenAI-sändningen. Ingen nätverkstrafik genereras.
5. Varken den här kontrollen eller regex/NER är bevis på att indirekt identifierbar eller känslig information aldrig kan överföras. **Pseudonymisering är inte anonymisering.**

## 2. Sammanfattning av källkodsvägar och möjliga uppgifter

| Funktion / anropsgrupp | Indata som kan nå byggaren före sanering | Gräns och särskilda risker |
|---|---|---|
| Personlighets-, motivations- och färdighetstolkning | Sova-personlighetsdrag, motivationsfaktorer, testskalor/poäng, ibland roll- eller processkontext, admininstruktioner | Kända kandidatnamn maskeras vid källa på flera vägar; prompten passerar sedan central sanerare |
| Intervjufrågor för personlighet/motivation/färdighet | Testunderlag, valda teman, frågekontext, admininstruktioner | JSON-reparationsförsök har **egna SDK-anrop** och ska ingå i payloadtestningen |
| Övergripande kandidatsammanfattning, syftesanalys och beslutsstöd | Testresultat, roll/process, tillgängliga tidigare tolkningar, eventuellt intervjusvar/anteckningar | Många olika generatorer; särskilt kontroll av vilka sparade AI-texter som ingår behövs |
| Efter intervju, helhetsbild, rapportdelar och chefsrapport | Tillgängliga resultat, intervjuanteckningar/-svar, rollkontext och andra evidenskategorier | Sektionernas faktiska råfält, äldre överlagrad funktion och återgenerering behöver separata testspecifikationer |
| Kandidatens egen resultatsida | Kanonisk bedömningsdata, tillgängliga kandidatvänliga sammanfattningar, administrationsinstruktioner | Kontrollera att privata processanteckningar inte råkar ingå även om de instrueras att inte visas i svaret |
| Generella insikter vid flexibel process | Bedömningsinput från backend, inklusive möjlig fritext | Genererad prompt använder `CANDIDATE_A`; innehållet i inputdict måste ändå saneras |
| Teaminsikter | **Aggregat** av teamets stilar, storlek och antalet med resultat, teamets mål, beskrivning och kontext, admininstruktioner | Råa medlems-ID:n används enligt koden för **lokal** signaturberäkning; de är inte avsedda att skickas i användarpromptens `prompt_context`. Fritext i beskrivning/kontext är en PII-risk |
| Admins promptverktyg | Admininstruktion, syntetiskt exempelunderlag, valfri fritextkontext | Admin kan skriva/klistra in personuppgifter trots varning; central sanering gäller även här |
| Embeddings och RAG | Godtycklig text/fråga som anroparen levererar | Embedding-texten saneras före OpenAI; Pinecone är **en separat dataöverföring** som inte täcks av OpenAI-sanitizern |
| Legacy AI-chatt | Historiskt fri fråga, ev. RAG-kontext | **Ingen aktiv HTTP-väg**: `/chat/`, `/chat/api/`, `/chat/api/stream/` returnerar 404 enligt #302. Källkoden räknas med för framtida regressionskontroll |

**Viktigt:** Tabellen beskriver granskade **datakategorier från kod** och risker, inte ett fullständigt fält-för-fält-sändningskontrakt för varje prompt. En del byggare har flera lager av dynamiska instruktioner och läser sparade sammanfattningar, så de måste granskas i turordning. Använd inte tabellen för att hävda att inga personuppgifter någonsin skickas.

## 3. Vad kontrollerar det nya testet?

`apps/core/test_ai_payload_inventory.py`:

- Läser alla Pythonfiler under `apps/`, undantar tester/migrationer och kontrollerar att varje modul som använder `get_openai_client()` eller gör SDK-`create()` är inventerad.
- Räknar och identifierar de exakta funktionsnamnen där SDK-anrop görs, även reparationsanrop som annars lätt missas.
- Kör flexibel kandidattolkning på **svenska och engelska** med påhittad intervjutext som innehåller namn, mejl, telefon och psykometriska termer. Kontrollerar **rå-SDK-mockens** mottagna `messages` efter sanering.
- Kör kandidatens sammanfattningsström med simulerat namn, inklusive **ensamt förnamn**, och kontrollerar källredaktion + sanering i slutliga `messages` på båda språken.
- Kör den verkliga embeddinghjälpen med syntetisk text och verifierar att `input` till mockade SDK:n saknar namn och mejl men bevarar psykometriska termer.
- Ger **ingen extern AI-kommunikation** och sparar **ingen kandidatdata**. Testningen är inte bevis för produktionsprojektets lagringsregion, modell eller retention.

Alla framtida nya Pythonanrop ska läggas in i `301-openai-callsites.json` **och få sitt specifika payloadtest granskat**. Manifestet är en förändringsspärr, inte en garanti mot nya bibliotek eller obevakade datakällor.

**Ny delkartläggning:** [Efter intervju, Chefsrapport och Teaminsikter](./301-efter-intervju-chefsrapport-team-ai-underlag.md) beskriver exakt vilka tidigare AI-tolkningsfält som återanvänds, skillnaden mellan intervjusammanfattning och helhetsbild, de sex chefspromptarna och vilka team-aggregat kontra lokala ID:n som används. Syntetiska SDK-slutpayloadtester finns i `apps/core/test_ai_payload_interview_team.py`.\n\n## 4. Tydliga kvarvarande arbetsuppgifter innan #301 stängs

- [ ] Bygg en **fält-för-fält-matris per aktiv funktion**: användarklick, serverfunktion, råa fält/JSON-nycklar, backendfiltrering, känd namnredaktion, slutlig SDK-payload, eventuell sparning, kund/tenant och legalt ändamål.
- [ ] Mock-baserade final-payload-tester för **alla aktiva generatorer**, även strömmar, svenska/engelska, adminpromptöverskrivningar, regeneration, cache och JSON-repair paths. Dagens automatiska tester täcker **tre representativa vägar**.
- [ ] Dokumentera exakt när **tidigare sparade AI-tolkningar** ingår som evidens och när det bara är testpoäng/statisk rapportinformation. Varje sådan källa måste ha dataminimering och juridiskt motiverat syfte.
- [ ] Kontrollera att inbyggda fält som innehåller URL:er, interna kandidat-/Sova-ID:n, rollkontext, intervjuanteckningar och andra identifierare inte förs vidare i onödan, även om vanliga namn maskeras.
- [ ] Säkerställ att diagnostik, fel/repair, serverloggar, `print` och exporter inte lagrar rå prompttext.
- [ ] Separat kontroll av Pinecone-upload/query/metadata och andra mottagare, jfr #310.
- [ ] Verifiera produktionens OpenAI-modeller, endpoints, organisationsregion, avtal/DPA och retention i #303/#304. **Blockerat av företags-/kontoinnehavarens OpenAI-beslut**, inte av detta kodarbete.
- [ ] Juridisk/dataskyddsmässig granskning och slutligt godkännande före kundextern användning.

## 5. Versionsinformation

[Den tidigare v0.1-inventeringen](./talena-openai-datafloden.md) skapades före de senaste säkerhetsförändringarna och innehåller därför *historiska råpromptuppgifter*. Den får inte användas som bekräftelse på vilka namn som skickas ut i dagens system. Den här v0.2-inventeringen och den maskinläsbara matrisen är en **uppdaterad teknisk grund**, men kan ännu inte intyga fullständiga slutliga nyttolaster.

### Relaterade ärenden

- [#298](https://github.com/fridalannerstrom/talena-platform/issues/298) – kända kandidatnamn vid källan (stängd)
- [#299](https://github.com/fridalannerstrom/talena-platform/issues/299) – tydliga varningar i AI-fritextfält (stängd)
- [#300](https://github.com/fridalannerstrom/talena-platform/issues/300) – lokal PII/NER (teknik delvis klar, produktionsutvärdering kvar)
- [#301](https://github.com/fridalannerstrom/talena-platform/issues/301) – komplett AI-payloadinventering (öppen)
- [#302](https://github.com/fridalannerstrom/talena-platform/issues/302) – personchatt avstängd (stängd)
- [#303](https://github.com/fridalannerstrom/talena-platform/issues/303), [#304](https://github.com/fridalannerstrom/talena-platform/issues/304) – OpenAI region, DPA och retention (väntar på konto-/avtalsbeslut)
