# Talena: kandidatdata, lagringsplatser och raderingsberoenden

**Status:** Kodgranskad teknisk inventering v0.1; ej verifierad mot produktionsdatabas.  
**Datum:** 2026-10-22  
**Källa:** `main`, commit `f93d001c57d3f459cc3724d664bcf87e55d0a9c5`.  
**Kopplade ärenden:** [#310](https://github.com/fridalannerstrom/talena-platform/issues/310), [#307](https://github.com/fridalannerstrom/talena-platform/issues/307), [#308](https://github.com/fridalannerstrom/talena-platform/issues/308), [#309](https://github.com/fridalannerstrom/talena-platform/issues/309), [#301](https://github.com/fridalannerstrom/talena-platform/issues/301).

> **Omfattning:** Kartan visar möjliga datakategorier och relationer i Django-modeller, inte att varje rad verkligen finns i drift. Ingen riktig kandidatdata har lästs, exporterats eller raderats. Juridiska lagringstider, rättslig grund och ansvar mellan personuppgiftsansvarig/biträde behöver beslutas av verksamheten och jurist. Ändra inte data utifrån denna inventering utan testad och godkänd rutin.

## 1. Översikt över datakategorier

| Data och exempel | Huvudsakliga modeller / lagringsplats | Radering/export: teknisk konsekvens |
|---|---|---|
| Kandidatprofil: namn, mejl, skapat datum | [`processes.Candidate`](../../apps/processes/models.py) | **Global** kandidatpost, `email` är unik i hela databasen, inte inom varje `Company`. Kartlägg samtliga relationer och kunder före global radering. |
| Projektanknytning, testorder, genomförandestatus, Sova-ID, råa resultat, rapport-URL:er | [`TestInvitation`](../../apps/processes/models.py) | `process` och `candidate` är CASCADE. Stora JSON-fält: `project_results`, `result_payload`, `sova_payload`, `sova_activities`, `sova_phases`, `sova_reports`. |
| AI-texter, frågor, anteckningar, beslutsstöd | [`TestInvitation`, `HistoricalProcessCandidate`](../../apps/processes/models.py) | Flera `ai_*` JSON/TextField samt `interview_notes` och tidigare `historical_notes`. Även genererat innehåll är potentiellt personuppgifter. |
| Kandidatens egna resultat, inloggnings-/delningsuppgifter och återkoppling | [`candidate_results`-modeller](../../apps/candidate_results/models.py) | `CandidateResultSnapshot.content` (JSON), `CandidateResultAccess` (hashat token/kod, access/expiry), `CandidateResultFeedback.comment`, `CandidateTestExperienceFeedback.comment`. Kopplade med CASCADE. Åtkomst ska återkallas vid radering. |
| Testanvändning, debitering och identitetskopior | [`AssessmentUsage`](../../apps/processes/models.py) | **PROTECT** till `candidate`, `invitation`, `process` m.fl. Fälten `candidate_name_snapshot` och `candidate_email_snapshot` kopierar identifierare. Kräver separat policy för eventuellt bevarande och avidentifiering innan full radering. |
| Historiska importerade resultat från Excel | [`HistoricalProcessCandidate`, `HistoricalAssessmentResult`, `HistoricalAssessmentScore`, `HistoricalAssessmentImport`](../../apps/processes/models.py) | Innehåller rådata (`raw_data`), poäng, ID samt uppladdad Excel-fil i Azure Blob via `HistoricalAssessmentImport.file`. Kontrollera om originalfil får/bör behållas. |
| Gamla historiska PDF-rapporter | [`HistoricalCandidateReport`](../../apps/processes/models.py); äldre `TestInvitation.historical_report_file`/`historical_report_url` | **Legacy:** funktionerna avvecklades i PR #331, men modell/fält och eventuella gamla DB-poster och Azure-filer finns kvar tills separat gallring genomförts. **Radera inte hela blob-prefixet utan inventering.** |
| E-posthistorik | [`emails.EmailLog`](../../apps/emails/models.py) | Kopplad till inbjudan (CASCADE), innehåller `to_email`, `subject`, `body_snapshot`, fel och provider-ID. Separat e-postleverantör kan ha egna loggar. |
| Aktivitetslogg | [`activity.ActivityEvent`](../../apps/activity/models.py) | Kopplad till kandidat, inbjudan, projekt och företag; `actor_name` och `meta` kan innehålla personuppgifter. CASCADE för kandidat/inbjudan. Bestäm minsta nödvändiga auditspår. |
| Teammedlemskap och indirekta profiler | [`teams.TeamMembership`, `teams.TeamAIInsight`](../../apps/teams/models.py) | Medlemskap refererar till kandidat (CASCADE). Genererade teaminsikter/metadata är kopplade till **team**, inte direkt till kandidat: bedöm behov att uppdatera/invalidera efter medlemsradering. |
| Självregistrering | [`processes.SelfRegistration`](../../apps/processes/models.py) | Lagrar namn, mejl, Sova-ID och process **utan `Candidate`-FK**. Kräver identifiering via säker matchning (e-post, Sova-ID, process), annars kan uppgifter bli kvar. |
| Roll- och processfritext | [`ProcessRoleContext`, `TestProcess`](../../apps/processes/models.py) | Är processgemensamt, kan innehålla kandidatens namn/uppgifter i fritext. Ska inte raderas automatiskt om andra kandidater berörs; kontrollera/minimera vid begäran. |
| Användarkonton och användarprofilbilder | [`accounts.User`, `Profile`, `CompanyMember`](../../apps/accounts/models.py) | Separat rättssubjekt/personkategori. En kandidat kan också ha ett konto; identifiera korrekt och avgränsa raderingsåtgärd mot kundanvändare. `Profile.image` kan skapa blob-fil. |
| Kunskapsindex/embeddings (om i bruk) | [`knowledge.KnowledgeEntry`](../../apps/knowledge/models.py), Pinecone/integration | Referenser till Pinecone namespace/IDs finns. Fastställ om någon kandidattext faktiskt indexeras, och hantera extern radering där den används. |

## 2. Kritiska raderingsrisker, verifierade i koden

### A. Kandidatposten är gemensam över projekt och kunder
`Candidate.email` har en global unik constraint `uniq_candidate_email`. `Candidate` saknar `company`-FK, medan `TestInvitation` och `HistoricalProcessCandidate` länkar kandidaten till olika projekt och företag. **Dra inte slutsatsen att en kunds begäran alltid ska radera hela Candidate-raden**; kontrollera samtliga relevanta relationer, behörigheter och vem som är personuppgiftsansvarig per behandling. Skydda andra kunders data och säkerställ korrekt hantering av registerutdrag.

### B. `AssessmentUsage` blockerar en okritisk delete
`AssessmentUsage.candidate` **och** `AssessmentUsage.invitation` har `on_delete=models.PROTECT`. Existerande användningsposter kan därför orsaka `ProtectedError` när man kör `Candidate.delete()` **eller** `TestInvitation.delete()`. Debiteringsposterna innehåller dessutom snapshot av namn/mejl; radering av `Candidate` skulle inte automatiskt tömma dessa fält även om relationer senare ändras. Gör ett separat designbeslut för lagstadgad/avtalad lagringstid, dataminimering och säkert genomförande.

### C. “Ta bort från projekt” är inte GDPR-radering
[`processes.views.remove_candidate_from_process`](../../apps/processes/views.py) och [`accounts.views.admin_remove_candidate_from_process`](../../apps/accounts/views.py) använder `invitation.delete()`. Det avser projektkopplingen, inte alla uppgifter om personen. Flödet kan dessutom påverkas av PROTECT-beroendet ovan. Undersök CASCADE-effekter (exempelvis kandidatens resultat-snapshot och e-postlogg) och besluta om uppgifterna borde bevaras enligt separat tidsplan; tydliggör i UI vad respektive åtgärd gör.

### D. Fritext, kopior och externa system kan överleva en enkel FK-delete
- `SelfRegistration` lagrar identitet utan kandidat-FK.
- `AssessmentUsage` innehåller personidentifierande snapshots.
- `ActivityEvent.meta`, e-post-`body_snapshot`, `ProcessRoleContext`, teaminsikter och JSON-kolumner kan innehålla fler uppgifter än deras direkta FK-relationer visar.
- Sova, OpenAI, e-posttjänst, Pinecone samt Azure-loggar och backuper ska hanteras utifrån faktisk konfiguration och leverantörsavtal. Se [AI-dataflöden](./talena-openai-datafloden.md), som är en **äldre v0.1-kodgranskning** och måste uppdateras för senare anonymiseringsfixar.
- Django `FileField` bör inte antas ta bort den fysiska filen i Azure när databasposten tas bort. Ingen central filstädning har verifierats i kodgranskningen; definiera kontrollerad blob-gallring och kontrollera kvarvarande filer.

## 3. Infrastruktur: tidigare verifierad Azure-konfiguration

| Resurs | Verifierat från Azure Portal 2026-10-22 |
|---|---|
| Primär PostgreSQL | `talena-prod-db`, **Sweden Central**, automatisk backup med **7 dagar** retention, `geoRedundantBackup=Disabled`. |
| Azure Blob | `talenaprodstorage` / `media`, **Sweden Central**, **LRS**, container privat, anonym åtkomst av, HTTPS krävs/TLS minst 1.2. |
| Blob-gallring/återställning | Mjuk borttagning av blob/container **7 dagar**; **inga** Blob Lifecycle Management-regler. SAS-URL:er från storage-backend är konfigurerade till **3600 sekunder**. |
| Kvar att granska | Externa tjänster, app-/diagnostikloggar, backuprestore, eventuella andra kopior, aktuell retention för *aktiv* data och kundavtal. |

**Notera:** 7 dagar för raderade blobbar eller databasbackuper är **inte** en lagringstid för aktiva kandidatposter.

## 4. Förslag till tekniskt säkert GDPR-arbetsflöde

1. **Kartlägg och simulera (read-only):** Ge ett kandidat-ID en sammanställning med per-tenant/process kopplingar, modeller, antal poster, flagga PROTECT-beroenden och en förhandsgranskning av externa/matchade uppgifter, utan rådata i loggar.
2. **Besluta omfattning:** Skilj `remove from project`, `delete personal data for one controller/company` och `delete all permissible data for candidate`. Kräv backend-objektbehörighet och dokumenterade undantag. Ingen delad kandidatrad får raderas innan andra kopplingar bedömts.
3. **Designa bevarande/minimering:** Regler för `AssessmentUsage` (fakturerings-/revisionshistorik), auditlogg och backup-återställning. Undvik att behålla namn/mejl i snapshots när de inte behövs.
4. **Implementera transaktionssäker radering:** Separera beslut/planering från exekvering, återkalla delningstokens, hantera lämpliga DB-relationer och sätt upp säkert, idempotent cleanup-jobb för externa filer/tjänster. Filradering är inte atomär med DB-radering; spåra fel och tillåt säker retry.
5. **Exporterbar datakarta:** Bygg #308 från samma identifierade datakällor, exkludera andra personers och kunders konfidentiella information.
6. **Automatiska tester:** Två kunder delar samma `Candidate.email`; aktivt `AssessmentUsage` med PROTECT; kvarvarande `SelfRegistration`/e-postloggar; historisk Excel-blob; resultattoken; teaminsikt; backup-/restore-rutin. Använd enbart syntetiska data.

## 5. Ännu ej verifierat / ansvar

- [ ] Produktionsinventering av **antal poster per modell** genom ett read-only verktyg, endast aggregerade antal utan personuppgifter i utskriften.
- [ ] Omfattning av samtliga kvarvarande relationer/JSON-dokument och eventuella överföringar, inklusive aktiva scheduler-/cleanup-jobb.
- [ ] Detaljerad fältlista med ändamål och faktisk ägare per behandling (personuppgiftsansvarig / biträde / underbiträde).
- [ ] Beslutade retentionperioder per datakategori och skriftligt godkännande från verksamheten/jurist.
- [ ] Hantering av historiska PDF-blobbar och original-Excel; testad gallringsrutin.
- [ ] Verifierad Sova-raderingsmöjlighet/API, OpenAI-region/retention, och backup-/restoreprocedur.
- [ ] Särskilt utreda dataminimering för `EmailLog.body_snapshot`, `ActivityEvent.meta`, `SelfRegistration`, `AssessmentUsage` och teamgenererade insikter.

**Nästa lämpliga koduppgift:** ett **read-only inventory/dry-run management command** som kan sammanställa kandidatens relationer per kund utan att exportera persondata eller utföra delete, följt av tester för PROTECT-beroende och shared Candidate-scenariot.
