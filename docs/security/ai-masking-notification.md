# Talena: bekräftelse när AI-underlag maskeras

**Ny feature-branch:** `feature/ai-privacy-masking-notice-20261020` från `main`. Inga ändringar i användarens lokala branch eller `db.sqlite3`.

## Önskat beteende

- Befintliga statiska personuppgiftspåminnelser vid intervjuanteckningar och annan fritext (#299) ligger kvar.
- När en identifierande uppgift **faktiskt maskeras** och det maskerade OpenAI-anropet påbörjats utan SDK-fel visas en diskret informationsruta: `Personuppgifter har maskats`.
- Förklarande text: `Identifierande uppgifter har maskats i underlaget till AI. Dina sparade anteckningar har inte ändrats.`.
- På engelska: `Personal data has been masked` samt motsvarande hjälprad.
- Om ingen maskering skedde ska **inget** meddelande visas. Det är inte en varning när användaren skriver och den ska inte blockera AI-genereringen.
- Ingen råtext, kandidat-ID, telefonnummer, e-postadress, maskeringsdetaljer eller prompt skickas till frontend i telemetry. Bara `1` i en response-header eller en fast NDJSON-händelse utan andra fält.
- UI-bekräftelsen är **inte** bevis för att alla personuppgifter har upptäckts. Den är information om en faktiskt utförd maskering. Inga anteckningar redigeras i databasen.

## Teknisk implementation

1. `apps/core/ai/privacy_notice.py` använder `ContextVar` och små requestlokala booleans. En temporär masking-attempt används under sanering av varje outbound OpenAI-förfrågan.
2. `apps/core/ai/pii_sanitizer.py` registrerar ändring först när text verkligen förändrats. Den befintliga `candidate_name_privacy.py` registrerar också maskering av kandidatens kända namn som sker tidigare i promptkedjan.
3. `openai_client.py` markerar masking som *sent* först efter att OpenAI SDK-anropet accepterats. Vid undantag i sanitizer eller SDK markeras inget lyckat anrop.
4. Django-middleware sänder header `X-Talena-AI-PII-Masked: 1` för vanliga svar, eller en **enda** fast `{"type":"ai_privacy_masked"}`-rad i streaming NDJSON efter att maskering skett. Ingen annan response payload ändras.
5. `static/js/talena/ai-privacy-notice.js` återanvänder Fetch och läser just denna header/NDJSON-händelse. NDJSON-strömmens originalbytes vidarebefordras oförändrade till respektive befintlig rapportvy. En enda icke-blockerande, stängbar toast visas i kundvyn; meddelandet försvinner automatiskt efter tolv sekunder.
6. Ingen separat databas-/cachetabell, migrering, serverlogg av utgående text, eller extern analytics krävs.

## Testning

- `apps/core/test_ai_privacy_notice.py`: icke-maskerade payloads; kända kandidatnamn; maskerande chat-, embedding- och Responses-anrop; SDK-fel; strömmande NDJSON-händelse; booleansk signal utan originaltext; isolering mellan förfrågningar; UI-svenska/engelska.
- `scripts/test_ai_privacy_notice.js`: faktisk JS-smoke för Fetch-hook och NDJSON-bytes.
- Testsuite körs både i en separat Actions-workflow och i Django QA.

### Manuell dev-test efter merge

1. Använd en kandidat med redan genererad testdata, öppna **Efter intervju** i Talena.
2. Skriv syntetisk text som `Jag intervjuade Anna Svensson. Mejla anna@example.se.` i intervjuanteckningarna. Anteckningen ska sparas som förut, och den vanliga hjälpraden ska synas.
3. Generera AI-innehåll med fungerande lokal OpenAI-konfiguration. Efter att backend maskerat och skickat underlaget ska en diskret informationsruta visas (SV/EN).
4. Testa utan några identifierare. Inget nytt meddelande ska visas.
5. Kontrollera att AI-rapporter fortsätter genereras, även strömmande flikar och regenerering.
6. Testa ett OpenAI-fel: ingen falsk maskeringsbekräftelse ska visas.
7. Kontrollera webbläsarens Network-flik: innehåll i header/NDJSON-event ska bara vara boolean/fasta eventtypen, aldrig originalpersonuppgifter.

**Begränsning:** Detta visar *att Talena har maskerat något*, inte att texten är helt anonym eller att alla personidentifierare togs bort. Den lokala NER-modellen är fortfarande **inte aktiverad i Azure**; detta UI-stöd fungerar redan med den regelbaserade saneringen. Backend-notifikationen täcker bara anrop via Talenas gemensamma OpenAI-klient och avsedda NDJSON-/JSON-responser.

**Avgränsning:** UI-komponenten är i det gemensamma kundgränssnittet. Admins separata prompt-playground-vyer får fortsatt server-sidig sanering, men inte automatiskt samma toast förrän den separata adminlayouten integreras.
