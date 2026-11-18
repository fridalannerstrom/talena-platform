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

## Aktivitetsloggens två flikar (2026-11-18)

Admin → Aktivitetslogg öppnar nu **Kundaktivitet** som standard och har en
separat **Admin**-flik. Detta är två serverfiltrerade vyer över samma
ActivityEvent-tabell, inte nya datakällor eller nytt bakgrundsspårningssystem.

- **Kundaktivitet:** händelser knutna till ett kundföretag, utförda av en
  kundanvändare eller registrerade automatiskt/av kandidatportalen utan aktör.
  Plattformadmins handlingar hos en kund visas **inte** här när aktören är
  känd. Användare som tagits bort går inte att klassificera i efterhand;
  sådana händelser med kundkoppling behandlas som kundrelaterade och märks
  fortfarande som okänd/tidigare aktör.
- **Admin:** interna loggåtkomster/exporter och plattformshändelser utan
  kundkoppling, plus händelser som initierats av plattformsadmin,
  inklusive adminåtgärder kopplade till ett kundprojekt.
- Tabbyte behåller ett eventuellt datumintervall men återställer övriga
  filter så att kundfilter inte gömmer plattformsloggar av misstag.
  Datum-, organisations-, aktörs- och händelsefilter, paginering och
  **CSV-exporten** använder alla samma serverbestämda flikgräns.
- `admin_log_accessed` och `admin_log_exported` fortsätter att
  registreras som säkerhetsspårbarhet, men finns enbart i fliken Admin.
  De exkluderas fortfarande från verksamhets-KPI:erna.

Delningen beskriver händelsens registrerade sammanhang och ursprung,
inte en fullständig klassificering av användarbeteende. Aktör som
saknas kan inte rekonstrueras säkert i efterhand.

## Etapp 3: Rapportexporter per typ (2026-11-18)

Admin → Statistik visar nu ett eget block **Rapportexporter** med total,
PDF, ZIP och uppdelning per kodägd rapporttyp. Siffrorna kommer från två
säkra, metadata-only eventkällor:

- `manager_report_pdf_generated`: befintlig Chefsrapport-historik
  efter klientbekräftad PDF-generering (#429/#430).
- `report_export_generated`: nytt klientrapporterat **färdigskapande**
  av en PDF eller ZIP. Endast när den aktuella webbläsaren har producerat
  filen och startat sparandet. Inga felaktiga/avbrutna exporter eller
  mellanliggande PDF-blobbar för rapportpaket ska räknas.

Rapporttyper: personlighet, motivation, färdighet (resultat, tolkning,
frågor, reflektioner), överblick, individuella teamprofiler, ledarskap,
urspårning, inför/efter intervju, interna kandidatrapports-PDF,
teamrapporter, samtliga teamprofiler som ZIP, kandidaters och teams
sammanslagna PDF:er respektive ZIP-paket.

**Viktiga begränsningar:**

- PDF och ZIP skapas huvudsakligen **i webbläsaren**. Talena kan inte
  garantera att användaren verkligen sparade en lokal fil eller läste
  innehållet. KPI:n är webbläsarrapporterad, inte en Sova-faktureringslogg.
- Ett färdigskapat ZIP-/PDF-paket räknas som **en** exporthändelse.
  Dess ingående PDF-filer räknas inte som separata nedladdningar.
  För Chefsrapportens befintliga PDF-kvitto skapar en mellanliggande
  package-blob inte ett separat `manager_report_pdf_generated` event.
  Historiska Chefsrapport-event kan ha andra villkor.
- Export-POST tar endast **statisk rapportkod** och ett slumpgenererat
  **UUIDv4-kvitto** för idempotens. På serversidan härleds företag, kandidat,
  projekt och aktör från autentiserad, åtkomstskyddad URL/ORM-data.
  Inga rapporttitlar, fria filnamn, AI-texter, personuppgifter i JSON
  eller PDF-blobbar skickas till statistikendpointen.
- Process- och teamåtkomst verifieras mot befintlig behörighetsmodell.
  CSRF, POST-only och en idempotent replay-check gäller även för team.
  Teamrapporter loggas mot företaget utan kandidat-/projektidentitet.
- Offentliga kandidatportalen är **inte** instrumenterad: endast behörig
  intern förhandsvisning av kandidatrapporten loggar PDF-kvitton.
- Detaljerad individuell logg finns för plattformsadmin, men aggregerad
  exportstatistik har prioritet. Event följer ActivityEvents gallring.
  Nyretentionbeslutet för AI- och rapporttelemetri kvarstår innan prod.

Test: `python manage.py test apps.activity.test_report_exports_435 --noinput`
och `node scripts/test_report_export_tracking_435.js`. Kontrollera även
`python manage.py makemigrations activity --check --dry-run`.

## Migreringskedja

`activity.0008_platform_admin_audit_access`
→ `activity.0009_manager_report_pdf_prepared`
→ `activity.0010_ai_usage_verbs`
→ `activity.0011_report_export_generated`.

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
3. Fortsatt täckning för produkt-/projektaktivitet och uttrycklig
   mänsklig granskningskvittens. PDF/ZIP-instrumentering för kandidat- och
   teamrapporter är införd; verifiera ytterligare fristående rapportflöden
   separat om sådana upptäcks vid produktgenomgång.
4. Meningsfulla kandidatvisningar, prompt-/rapportversionskedja och fler
   integrationsfel enligt #433/#434, först efter inventering.
5. Manuell webbläsarkontroll svenska/engelska och CI i korrekt miljö.

**Ingen merge eller ändring i main/production ingår i denna etapp.**
