# #435 · AI-användningsstatistik, första etappen (2026-11-18)

## Status och avgränsning

Detta är **första etappen av #435**, inte en stängd ticket. Admin får en
aggregerad, organisationsfiltrerbar sida `/admin-ai-statistics/`, med period,
funktion, status, tokenantal när provider rapporterar dem, en trend och
aggregerad CSV. Källan är samma `activity.ActivityEvent` som #432/#434,
inte en parallell användar- eller kandidatlogg.

**Ny produktionstelemetri är inaktiverad som standard.** För explicit opt-in
sätts `TALENA_AI_USAGE_LOGGING_ENABLED=1`. Beslut om ändamål, information
och gallring enligt #310/#433 måste godkännas innan produktionsaktivering.
Ingen bakåtfyllnad av äldre OpenAI-anrop är möjlig.

## Vad mäts

En post per faktiskt initierat provideranrop genom Talenas privacy-screenade
OpenAI-klient, bara för kodägda och godkända funktioner.

- `ai_call_succeeded`: provider-request avslutades, eller provider-stream
  konsumerades till slut. **Ingen garanti för att genererad text validerades
  eller att en rapport sparades.**
- `ai_call_failed`: OpenAI SDK/request eller streamkastning, **inte**
  applikationsvalidering efter provider-svar.
- `ai_call_incomplete`: stream lämnades/avbröts innan den konsumerats helt;
  kan exempelvis bero på att användaren stänger sidan.
- `meta`: `schema=1`, allowlistad `feature`, `operation`,
  sanerat modell-ID, `usage_available`, eventuellt provider-returnerade
  heltal `prompt_tokens`, `completion_tokens` och `total_tokens`.
- `company/process` endast om godkänd server-side owner/process/team
  finns i aktuell funktion; annars plattformsnivå, ej falskt kundattribuerat.
- För nya opt-in-anrop länkas `actor` till inloggad serverautentiserad
  användare, och `candidate` endast när anropskoden har en sparad
  `TestInvitation` som hör till samma projekt. Det är en intern
  audit-referens, inte metadata från AI-modellen eller klienten.
- Ingen `invitation`-FK, prompt, AI-svar, råa fel, kandidatnamn i `meta`,
  testpoäng, fritext, IP, URL eller hemligheter sparas i AI-händelsen.

### Streaming

När opt-in är aktivt lägger den centrala klienten till det fasta interna SDK-
argumentet `stream_options={"include_usage": True}` för Chat Completions.
OpenAI skickar då eventuellt en usage-only slut-chunk. Den **filtreras bort**
innan anropskoden får chunken, eftersom flera befintliga Talena-funktioner
förväntar sig `choices[0]`. Provider-text läses inte av metern.

Om usage saknas är `usage_available=False`. Ingen uppskattning av tokens
eller USD/SEK-kostnad görs. Vissa funktioner (t.ex. fristående adminprompt,
RAG och intern AI-chatt) saknar legitim projektkoppling.

### UI och datatäckning

Endast plattformsadmin/superuser, serverkontroll på både HTML och CSV.
Datumintervallet begränsas till 366 dagar för förutsägbar prestanda;
SQL-aggregat används för KPI:er, funktioner och dagsserie. Grafen använder
högst 32 datum-buckets. Endast kategorier som faktiskt loggats visas.

En ny tabell **Enskilda AI-anrop** visar högst 25 händelser per sida med
funktion, tidpunkt, företag, inloggad användare, kandidat, projekt, utfall
och tillgängligt tokenantal. Sidan kan bläddras med de befintliga
period-, företags- och funktionsfiltren. Urvalsbaserade relationer läses från
FK-kolumner och förmedlas aldrig till kundvyn eller vanlig CSV-export.
När gamla händelser saknar användare/kandidat visas streck, utan backfill
eller felaktig attribution. Radering av kandidat rensar relevant FK-historik
enligt den befintliga ActivityEvent-modellens relationspolicy.
Event som aldrig loggats kan inte räknas som noll faktisk användning.
Loggåtkomst/export markeras med befintliga `admin_log_accessed` /
`admin_log_exported` och statiska scopes.

CSV innehåller bara period, featurekod, antal per providerutfall och
rapporterade tokens. Inga namn, aktörer eller kandidat-/projekt-ID:n.
Separat detaljerad audit-CSV fortsätter att tillhöra #434.

## Etapp 2: Verksamhetsaktivitet från befintlig logg

Samma adminvy visar nu **Verksamhetsaktivitet** ovanför AI-avsnittet.
Ingen ny spårning eller migration krävs för dessa mått. Endast registrerade
händelser som redan finns används, och tid/organisation följer sidans filter.
AI-funktionsfiltret berör endast AI-delarna.

Definitioner:

- **Företag/projekt med aktivitet:** antal distinkta företag respektive
  projekt med minst en befintlig verksamhetshändelse under perioden. Detta
  är **inte** totala antal befintliga kunder/öppna projekt.
- **Skickade inbjudningar:** antal `invite_sent`-händelser, inte unika
  personer och inte antal Sova-ordrar.
- **Slutförda tester:** antal `test_completed`-händelser, inte bekräftat
  antal unika kandidater.
- **Öppnade kandidatrapporter:** antal `candidate_result_link_opened`,
  inte bevis att någon läst eller granskat innehållet.
- **Chefsrapport PDF:** antal `manager_report_pdf_generated` (webbläsaren
  rapporterade generering); `manager_report_pdf_prepared` räknas **inte**
  som en färdig export eller garanterad lokal nedladdning.
- **Sparade mänskliga textredigeringar:** antal `ManagerReportTextEditEvent`
  med `action=saved`; återställning till AI-text räknas inte som en
  mänsklig redigering och avsaknad av redigering säger inget om granskning.
- **Verksamhetshändelser per kategori:** endast tillåtna typer i
  ActivityEvent för organisation, kandidat/test, kandidatportal och
  webbläsarbekräftad chefsrapport-PDF. Allt räknas som händelser,
  inte unika sessioner.

`admin_log_accessed` och `admin_log_exported` är särskilda
**säkerhetshändelser** och visas fortsatt i aktivitetsloggen, men **ingår
inte i någon verksamhets-KPI**. Inte heller AI-anrop, generell användar-
inloggning eller bara förberedda PDF:er ingår. Öppning av statistikvyn ska
därmed inte kunna öka måtten. Aktivitetsloggen innehåller nu en tydlig
svensk/engelsk förklaring av detta samt rätt kategori på AI- och
rapporthändelser.

Sova-integrationsfel, explicita granskningar och övriga exporttyper
har **inte** tillräcklig registrering för rättvisande KPI:er. Dessa
ska inte visas som noll utfall utan som ej färdigmätta.

**Datatäckning:** Datumet för första kända händelse är inte ett löfte
om att alla händelsetyper instrumenterats sedan dess. Gamla, oregistrerade
handlingar kan inte räknas i efterhand.

## Migreringskedja

`activity.0008_platform_admin_audit_access`
→ `activity.0009_manager_report_pdf_prepared`
→ `activity.0010_ai_usage_verbs`.

De felaktiga parallella migrationerna `0009_ai_usage_verbs` och
`0009_manager_report_pdf_prepared_in_activity` har tagits bort från
branchen. Vi återanvänder den ursprungliga chefsrapportmigrationen
`0009_manager_report_pdf_prepared` som redan finns i repo.

## Säkerhet, tester och kontroll

Först med lokal flagga:

```bash
# När nya migrationen är hämtad
python manage.py migrate
# Kör syntetiska regressioner och befintliga privacy-guards
python manage.py test apps.activity.test_ai_statistics_435 apps.core.test_ai_pii_sanitizer apps.core.test_ai_privacy_notice --noinput
```

Syntetiska regressioner provar: avstängd insamling, stream-events och
usage-only chunk, avbruten stream, SDK-fel utan feltextläckage,
saneringsblockering, verifierat kandidat- och aktörsursprung även för
uppskjutna HTTP-strömmar, inget läckage mellan förfrågningar,
paginering, separata tenant, otillåten adminåtkomst,
aggregerad CSV och tomma/ogiltiga filter. Ingen extern OpenAI/Sova-anropning.

## Kvar på #435, #433 och #305

1. Godkänt lagringstidsbeslut, automatiserad gallring och information före
   prodaktivering. Utvärdera äldre ActivityEvent-meta separat.
2. Verifierad per-modell tokenprissättning och faktisk kostnad, om önskvärt.
3. Produkt-/projektaktivitets-KPI med säkra definitioner, redigerings- och
   explicit granskningsdata samt bredare PDF/ZIP-exportinstrumentering.
4. Meningsfulla kandidatvisningar, prompt-/rapportversionskedja och fler
   integrationsfel enligt #433/#434, först efter inventering.
5. Manuell webbläsarkontroll svenska/engelska och CI i korrekt miljö.

**Ingen merge eller ändring i main/production ingår i denna etapp.**
