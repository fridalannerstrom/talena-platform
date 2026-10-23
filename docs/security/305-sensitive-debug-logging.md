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

## Separat fynd under granskning: äldre webhook utan auth (#309)

Den äldre, publikt routade `core:sova_webhook` (`/webhooks/sova/` under core-urlprefixet) hade en `@csrf_exempt`-funktion som behandlade kandidatstatus utan att verifiera `X-Talena-Webhook-Secret`. Detta är **en separat säkerhetsrisk** utöver loggningen: en obehörig avsändare kunde försöka uppdatera resultatstatus för kända interna/Sova-request-ID:n.

PR #345 lägger därför till en fail-closed, timing-safe sekretkontroll som använder konfigurerade `SOVA_WEBHOOK_TEST_SECRET`, `SOVA_WEBHOOK_PROD_SECRET` och tillfälligt `SOVA_WEBHOOK_SHARED_SECRET`, precis som den andra Sova-ingest-vägen. Saknat, felaktigt eller okonfigurerat sekret returnerar HTTP 401 innan någon teststatus hanteras. Syntetiska HTTP-tester finns i `apps/core/test_sova_webhook_security.py` och körs i Django QA.

**Driftskrav:** före produktionsgodkännande måste ansvarig kontrollera vilken callback-URL Sova faktiskt använder och att den konfigurerade avsändaren skickar rätt hemliga headern. En gammal webhook utan header kommer med rätta att nekas efter ändringen. Dela aldrig hemligheten i issue/chat/loggar. Efter deploy, testa ett syntetiskt matchande callback-flöde och kontrollera 401 för obehöriga anrop.

## Viktig begränsning

Ändringen **raderar inte gamla loggar eller debugfiler** på Azure, och gör inte automatiskt all Talenas loggning säker. Ticket #305 förblir öppen eftersom följande fortfarande saknas:

1. Granskning av **andra** `print`, `logger`, `logger.exception`, stacktraces, HTTP-klienters feltexter och andra loggmottagare, samt dataminimering där.
2. Säker inventering av eventuella redan skrivna `debug_webhooks/`-filer, Azure App Service-loggar, Application Insights och lagringstider. Ingen automatisk radering utan godkänd gallring enligt #310.
3. Struktur för AI-händelselogg med user/company/subject ID, funktion, modell, promptversion, sanitizering, utfall, version/lagring och separata events för granskning (#306). Auditloggen får inte innehålla råa promptar eller svar.
4. Verifiering av rättigheter/tenant-isolering och konfigurering av lagringstid och gallringsschema, godkänt av ansvarig.
5. Produktionens drift, telemetri och hur undantag hos OpenAI/Sova/Azure eventuellt serialiseras i loggar måste granskas separat.

Detta är **riskreduktion**, inte en slutattestering av GDPR eller AI Act.
