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
- Ingen `candidate`, `invitation`, `actor`, prompts, svar, råa fel,
  kandidatnamn, testpoäng, fritext, IP, URL eller tokens/secret.

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
Event som aldrig loggats kan inte räknas som noll faktisk användning.
Loggåtkomst/export markeras med befintliga `admin_log_accessed` /
`admin_log_exported` och statiska scopes.

CSV innehåller bara period, featurekod, antal per providerutfall och
rapporterade tokens. Inga namn, aktörer eller kandidat-/projekt-ID:n.
Separat detaljerad audit-CSV fortsätter att tillhöra #434.

## Migreringskedja

`activity.0008_platform_admin_audit_access`
→ `activity.0009_manager_report_pdf_prepared_in_activity`
→ `activity.0010_ai_usage_verbs`.

Den tidigare parallella `activity.0009_ai_usage_verbs` har tagits bort.
Vid utveckling kan `0009_manager_report_pdf_prepared_in_activity.py`
redan ha genererats lokalt utan att ha versionshanterats. Säkerhetskopiera
den lokala filen utanför migreringsmappen före `git pull` om den är
untracked, så att den nya spårade migrationsfilen kan hämtas.

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
saneringsblockering, separata tenant, otillåten adminåtkomst,
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
