# Talena: gallringssimulering utan radering (ticket #336)

**Status:** Tekniskt underlag för granskning. **Inga lagringstider eller automatiska raderingar är aktiverade.**

## Vad som finns

Kommandot `preview_candidate_retention` utgår från:
- En **uttryckligen angiven** kund och kandidat.
- Ett **hypotetiskt** rekryteringsavslutsdatum som operatören matar in. Talena har ännu inget verifierat `closed_at`-fält för detta.
- Ett datum att jämföra med (eller dagens datum).
- Det **icke godkända** policyförslaget v0.2 för privat rekrytering med **90 dagar som gräns för normal åtkomst/manuell granskning**, och **12 månader som föreslagen yttersta standardgräns för särskilt motiverat, åtkomstbegränsat bevarande**. Detta kommando beräknar **bara 90-dagarsgranskningen**, inte 12-månadersgränsen och inte ett raderingsdatum.

Det räknar ut **när en första manuell granskning skulle bli aktuell (90 dagar)**. Det räknar **inte** ut ett juridiskt fastställt raderingsdatum, en slutlig 12-månadersfrist eller rätt att lagra data. En separat granskning av nödvändighet, rättslig grund, begränsad åtkomst och kundinstruktion behövs innan några uppgifter kan bevaras efter dag 90. Det tillåter aldrig radering.

Den återanvänder datakartan i `audit_candidate_data` och visar bara antal poster inom det angivna företaget samt riskflaggor som `AssessmentUsage`/`PROTECT`, globala kandidatkopplingar och delade underlag. Den läser inte eller visar kandidatnamn, e-postadresser eller testinnehåll.

## Lokalt test med enbart syntetiska uppgifter

```bash
python manage.py test apps.processes.test_retention_preview --noinput
python manage.py preview_candidate_retention \
  --company-id 12 \
  --candidate-id 34 \
  --purpose hiring \
  --closed-on 2026-01-01 \
  --as-of 2026-04-01
```

ID:n ovan är **påhittade**. Kör inte kommandot på en verklig kunds kandidatdata innan ett behörigt driftbeslut finns. Undvik att dela riktiga kandidat-ID:n i terminalhistorik, tickets eller supportärenden.

Om testscenariot behöver ändras kan `--grace-days 1..365` anges. `--legal-hold-scenario` markerar ett **hypotetiskt** bevarandeundantag; det kontrollerar inte om ett faktiskt rättsligt undantag finns. I en kommun eller annan offentlig rekrytering ska denna privata standard **inte** betraktas som tillämplig.

## Exempel på minimerad output (schema)

```json
{
  "mode": "READ_ONLY_RETENTION_SIMULATION",
  "policy_proposal": "private_hiring_v0.1_NOT_APPROVED",
  "policy_approved": false,
  "automatic_deletion_enabled": false,
  "candidate_global_delete_permitted": false,
  "input_is_hypothetical": true,
  "scenario": {
    "purpose": "hiring",
    "hypothetical_closed_on": "2026-01-01",
    "as_of": "2026-04-01",
    "grace_days": 90,
    "review_on": "2026-04-01",
    "legal_hold_assumed": false,
    "review_due_by_date": true,
    "status": "review_due_NOT_delete_authorized"
  },
  "scoped_data_inventory": {
    "mode": "read_only_dry_run",
    "counts": {}
  },
  "next_action": "human_policy_and_data_review_required"
}
```

Exemplet visar **endast ett förenklat schema** och är inte verkliga kandidatdata eller den fullständiga responsen. I körningen tillkommer aggregerade tal och förklarande begränsningar.

## Säkerhetsgränser

- **Inget kundgränssnitt eller API:** Enbart intern Django management command.
- **Ingen produktionsmasskörning:** En kandidat och ett kundföretag per körning.
- **Endast SELECT-frågor:** Testsviten verifierar att ingen SQL-skrivoperation görs vid simuleringen.
- **Ingen ändring av lagring:** Varken Django `save/delete`, filradering, schemaläggning, Sova/OpenAI-anrop eller Azure-konfiguration.
- **Åtkomst:** Management commands körs med driftkontots databasrättigheter och är inte automatiskt isolerade per inloggad användare. Endast särskilt behöriga operatörer med dokumenterat syfte ska köra dem. En eventuell framtida kund-UI måste ha egna backendbehörigheter och loggpolicy.
- **Godkännande saknas:** `review_due_by_date=true` innebär aldrig att uppgifter lagligen eller tekniskt får gallras.
- **Inget lagringsbeslut:** Lagringstid och rättslig grund ska godkännas av verksamheten/personuppgiftsansvarig, enligt biträdesinstruktioner och DPIA.

## Nästa steg för #336

1. Besluta faktisk lagringspolicy och registrera instruktioner per kund och ändamål.
2. Utöka den read-only beräkningen med ett **separat hypotetiskt 12-månaders granskningsdatum**, baserat på kalenderår och kundens godkända bevarandeändamål, utan att markera någon kandidat som raderingsklar.
3. Inför separat `closed_at`-händelse för en avslutad rekrytering. **Förväxla inte** med `archived_at` eller `TestInvitation.completed_at` (test klart betyder inte rekrytering klar).
4. Utred per modell/fält juridiskt bevarande, faktureringsuppgifter och eventuella legala spärrar.
5. Bygg en versionerad policy med strikt godkännandekedja och preview på konkreta poster.
6. Först därefter: planera separat idempotent radering, inklusive Sova, Azure Blob, loggar och backuper, som förblir AV i produktion tills verifierad.

**Relaterat:** [Policyförslag v0.1](./310-lagrings-och-gallringspolicy-forslag.md), [Datakarta](./310-kandidatdata-register-och-radering.md) och [Read-only-inventering](./310-readonly-kandidatinventering.md).
