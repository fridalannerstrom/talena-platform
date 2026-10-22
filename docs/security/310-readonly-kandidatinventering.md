# Internt verktyg: kandidatdata, read-only förhandsinventering

**Ärenden:** #310 (datakarta) och #307 (radering).  
**Status:** Kod + syntetiska regressionstester. **Ingen GDPR-radering är implementerad.**

## Syfte

Django-kommandot `audit_candidate_data` visar **antal relaterade poster** för en kandidat inom ett uttryckligen angivet kundföretag. Det är ett internt verktyg för en behörig Talena-operatör, **inte** ett kund-API eller en färdig registerexport.

- Kör **endast SELECT-frågor** via ORM: ingen `delete()`, `save()`, filåtkomst, Azure-anrop eller Sova-anrop.
- Kräver `--company-id` och `--candidate-id`. Validerar att kandidatens poster har koppling till företaget och svarar annars med en generisk feltext.
- Resultatet skrivs som JSON med **antal och säkerhetsflaggor**, utan namn, mejladress, testinnehåll, intervjunoteringar eller uppladdade filnamn.
- Detekterar möjlig delning av den globala Candidate-posten över företag utan att ange det andra företagets identitet eller några andra företags postantal.
- Identifierar `AssessmentUsage` som möjligt raderingshinder (`PROTECT`) samt markerar raderingsbehov i underlag som saknar direkta FK-relationer.

**Kommandoradsexempel med påhittade ID:n** (kör mot lokal databas med syntetiska uppgifter):

```bash
python manage.py audit_candidate_data --company-id 12 --candidate-id 34
python manage.py test apps.processes.test_candidate_data_audit --noinput
```

Använd inte riktiga kandidat-ID:n i delade shellhistoriker, ärenden eller skärmbilder. Produktionsanvändning förutsätter behörig operatör, säker tillgång och godkänd driftprocess. Råa JSON-svar ska inte publikt exponeras.

## Ingående räkningar

| Nyckel | Ingår |
|---|---|
| `test_invitations` | Inbjudningar under företagets processer |
| `assessment_usages` | Test-/faktureringsrader, möjliga `PROTECT`-beroenden |
| `candidate_result_*` | Snapshot, resultatdelningstoken och feedback |
| `historical_*` | Historiska processkopplingar, resultat, poäng och legacy-PDF-poster |
| `shared_historical_import_files_referenced` | **Delade** Excel-uppladdningar kopplade till resultat; ska inte raderas per person utan kontroll |
| `email_logs`, `activity_events` | Relaterade loggar inom aktuell kund |
| `team_memberships`, `shared_team_ai_insights_to_review` | Teamkopplingar och insikter som kan behöva omräknas |
| `self_registrations_email_match_unverified` | **Heuristik** utifrån e-post inom kundens processer, ingen säker kandidat-FK |
| `legacy_pdf_file_fields_on_invitations` | Gammal filreferens i TestInvitation, utan Blob-hämtning |

## Begränsningar som måste lösas innan radering

1. **Kandidatposten är global:** Samma person kan delta hos flera kunder. Flaggan `candidate_record_shared_outside_scope` betyder **inte** att en global radering är tillåten när den är falsk; alla indirekta datakällor måste granskas.
2. **`AssessmentUsage` använder PROTECT**, och testfakturering har personidentifierande snapshotfält. Besluta separat vad som får bevaras och hur.
3. **Fritext och JSON**: Alla omnämnanden av en person saknar inte en FK. Exempelvis processbeskrivningar, aktivitetsmetadata och lagrade AI-sammanfattningar kan behöva egen analys.
4. **Delade filer och teaminsikter:** En historisk Excel-import eller teaminsikt kan gälla flera kandidater.
5. **Fysiska filer/externa leverantörer:** Kommandot frågar endast PostgreSQL. Det granskar **inte** Azure Blob-innehåll, data hos Sova/OpenAI/Pinecone, e-postleverantör eller backuper.
6. **Detta är inte ett exportverktyg:** GDPR-registerexport kräver ytterligare rättighets-/fältgranskning.

## Säker testning

Regressionssviten skapar två separata kundföretag med samma (syntetiska) Candidate-post samt `AssessmentUsage`, resultatdelning, teamkoppling, aktivitet, e-post och historiska testresultat. Den verifierar:

- bara det begärda företagets antal visas
- inga namnfält, mejladresser, anteckningar eller testinnehåll skrivs ut
- endast SQL-`SELECT` körs under inventeringen
- `PROTECT`-beroenden rapporteras
- fel företag, saknad kandidat och ogiltiga ID:n avvisas

**Nästa steg:** gå igenom detta verktyg med GDPR-ansvarig/jurist, besluta vad som får raderas eller måste bevaras och utveckla ett separat säkert exekveringsflöde. Inga data har ändrats i Talenas produktion i detta arbete.
