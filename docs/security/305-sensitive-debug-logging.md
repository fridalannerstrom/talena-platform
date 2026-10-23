# Talena: känsliga debugloggar i Sova- och AI-flöden

**Datum:** 2026-10-23  
**Ticket:** [#305](https://github.com/fridalannerstrom/talena-platform/issues/305)  
**Status:** Delåtgärd i kod, **inte** komplett auditloggning eller logg-retention.

## Identifierad dataläckagerisk och åtgärd

Granskning av aktuell Django-kod hittade tidigare oavsiktliga utskrifter av:

- Rå Sova order-assessment-svar och projektkandidatlistor i `apps/core/integrations/sova.py`.
- Kompletta webhook-JSON/headers, inklusive **del av webhook-hemlighet** i `apps/core/webhooks.py`. En valfri debugfil-rutin skrev även kompletta request bodies och HTTP-headers till serverns filsystem.
- Kompletta mottagna Sova-webhook-payloads i `apps/core/integrations/views.py`.
- URL och querystring med potentiella access-token i `AuthTraceMiddleware`.
- Rå AI-genererad intervjufrågetext vid formatfel i motivations- och färdighetsfrågegeneratorerna.

Den här PR:en stoppar ovanstående råa debugutskrifter och tar bort webhookens filbaserade request/headers-dumpar. Det bevarade informativa webhook-meddelandet innehåller endast HTTP-metod och antal bytes, inte payload eller headers. All annan verksamhetslogik (Sova statuslagring, testbeställningar, AI-formatfel, middleware-respons) lämnas oförändrad.

Regressionskontrollen `apps/core/test_sensitive_debug_logging.py` förbjuder `print()` i dessa sex kritiska kodfiler samt några kända osäkra felsökningsmönster. Den exekverar inga externa API-anrop och använder inga riktiga kandidatdata.

## Separat fynd: äldre Sova-webhook behöver autentisering (#309)

Under säkerhetsgranskningen hittades en äldre Sova-webhook utan en verifierad delad hemlighet. Skyddet behandlas i **en separat PR** för att kunna kontrollera leverantörens callback-URL och headerkonfiguration **innan** driftsättning. Den här logg-PR:en ändrar inte webhookautentiseringen. Ingen säkerhet kan antas för äldre routen förrän separat fix är mergad och verifierad.

## Viktig begränsning

Ändringen **raderar inte gamla loggar eller debugfiler** på Azure, och gör inte automatiskt all Talenas loggning säker. Ticket #305 förblir öppen eftersom följande fortfarande saknas:

1. Granskning av **andra** `print`, `logger`, `logger.exception`, stacktraces, HTTP-klienters feltexter och andra loggmottagare, samt dataminimering där.
2. Säker inventering av eventuella redan skrivna `debug_webhooks/`-filer, Azure App Service-loggar, Application Insights och lagringstider. Ingen automatisk radering utan godkänd gallring enligt #310.
3. Struktur för AI-händelselogg med user/company/subject ID, funktion, modell, promptversion, sanitizering, utfall, version/lagring och separata events för granskning (#306). Auditloggen får inte innehålla råa promptar eller svar.
4. Verifiering av rättigheter/tenant-isolering och konfigurering av lagringstid och gallringsschema, godkänt av ansvarig.
5. Produktionens drift, telemetri och hur undantag hos OpenAI/Sova/Azure eventuellt serialiseras i loggar måste granskas separat.

Detta är **riskreduktion**, inte en slutattestering av GDPR eller AI Act.

## Ytterligare dataminimering i efterföljande PR, 2026-10-23

En separat uppföljning tar bort `print()` i `apps/accounts/views.py`, `apps/reports/services/candidate_insights.py`, `apps/processes/services/candidate_insights.py`, `apps/processes/services/historical_assessment_import.py` och `apps/core/ai/ingest.py`. Tidigare kunde felsökningsutskrifter innehålla processkontext, AI-genererade områdestexter, uppladdade filnamn och Pinecone-ID/metadata. Ersatt med tyst hantering där loggningen inte är nödvändig; fel i flexible-insights behåller sitt tidigare fallbackbeteende utan rå undantagslogg. `apps/core/test_candidate_debug_logging.py` gör detta till en CI-spärr.

Även efter detta återstår en fullständig granskning av alla externa loggmottagare, provider-headers, molntelemetri, exception traces och hela AI-auditschemat enligt #305. Äldre logginnehåll raderas inte automatiskt.
