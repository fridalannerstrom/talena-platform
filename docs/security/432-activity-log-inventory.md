# #432 Talena loggcenter · inventering och första leverans (2026-11-05)

## Syfte och status

Första leveransen av #432/#434 återanvänder **befintliga**
`activity.ActivityEvent` och `apps.activity.services.log_event`.
Ingen ny allmän beteendespårning har aktiverats. Tillgänglig sida:
`/admin-activity/` (endast Talenas plattformsadmin/superuser).
Filter: företag, projekt-ID, kandidat-ID, aktör-ID, kategori, händelse,
namn- och datumintervall. Serverbaserad paginering och minimerad CSV (max
1 000 rader, **endast ID, UTC-tid och verb**). Denna första sida visar inga
råa `ActivityEvent.meta`-fält.

**Detta är en delleverans, inte en färdig EPIC.** #432, #433, #434, #435,
#305, #306, #429 och #430 behöver fortfarande avstämning. Frånvaron
av en eventrad är aldrig evidens för att ingen användare gjort handlingen.

## Inventering, uppmätt i kodbasen

| Händelsekategori | Källa och status | Nästa steg |
|---|---|---|
| Företag, konton, användarroller, plattformsinloggning | `ActivityEvent.Verb`, befintliga serverflöden i `apps/accounts`, `apps/core`; *befintlig* instrumentering, inte nödvändigtvis alla varianter | Granska full täckning och gap per endpoint |
| Projekt, kandidat tillagd/borttagen, inbjudan, teststatus | `ActivityEvent`, bland annat `apps/processes` och webhook/integrationsflöden; befintliga verbs | Verifiera framgångssemantik/dubbletter |
| Kandidatens resultatportal (öppnad länk, kod, feedback, återkallad) | `apps/candidate_results/audit.py` och `ActivityEvent` enligt #227; återanvänds | Testa persondataretention och fall där länk återkallas |
| Kundens öppning av kandidat- eller resultatsida | **Saknas som komplett serververifierad, deduplicerad auditspårning** | #433: definiera besöks-/resultatkategorier och legitimt behov |
| AI-genererat, omgenererat, misslyckat, exakt prompt-/modellversion | **Inte komplett strukturerat i gemensam logg** | #305/#433: annotera sparade versioner, saneringsstatus, metadata |
| AI-visning kontra explicit mänsklig granskning | **Saknas komplett**, visning kan inte likställas med godkännande | #306: explicit UI och separata event |
| Sparade manuella AI-/chefsrapportändringar | `ManagerReportTextEditEvent` finns för vissa edits, inte ännu fullständigt normaliserat med `ActivityEvent` | #430/#433: säkra versionsreferenser, läsadaptrar utan dubbellogg |
| PDF/ZIP-rapporter: leveransförsök/export | **Saknas komplett serververifierad exportinstrumentering**, vissa exportflöden går via klient-JS | #429/#430/#433: skilj förberedd generering, HTTP svar och faktisk nedladdning (den senare kan ej bevisas) |
| Auditloggens egen åtkomst/export | **Ny från denna PR**: `admin_log_accessed` och `admin_log_exported` i samma `ActivityEvent` med company=NULL för global adminåtkomst, serverhärledd aktör, och endast statisk allowlistad `meta` | Följ upp retention, accessgranskning och drift/monitorering |
| GDPR-radering, integrationfel och återförsök, fler teamflöden | **Inte verifierat heltäckande** | Fortsatt endpointinventering och behovsanalys före bred insamling |

## Behörighet och integritet

- Bara aktiva plattformsadminanvändare (global `User.role=admin`) och
  superusers får åtkomst. Django-staffstatus eller kundadmin räcker **inte**.
- Behörighet kontrolleras **server-side även på CSV**. Fälten i `meta` visas
  inte i listan eller exporten; gamla loggar kan dock redan innehålla metadata
  som behöver separat inventering/gallring.
- Den globala loggåtkomsten saknar tenant och loggas därför med `company=NULL`
  snarare än felaktig företagskoppling. Inga söktermer, kandidatnamn eller IP
  sparas i nya accesshändelser.
- Det som kallas CSV-export innebär bara att svaret **förberetts på servern**,
  inte att en fil faktiskt sparats på enheten.
- En filtrerad kandidathistorik via admin är bara händelser som finns i
  `ActivityEvent`; den inkluderar inte historiska händelser som aldrig loggats.
- Autorizations-/retentiondesign ska dokumenteras och godkännas med ansvarig
  innan nya kategorier med detaljerad individspårning aktiveras i prod.

## Retention och migrering

Migreringskedja: `activity.0007_alter_activityevent_verb` (befintlig lokal migration, nu versionshanterad) följs av schemaändringen `activity.0008_platform_admin_audit_access`, som tillåter
`company=NULL` för platform events och registrerar två nya kontrollerade
verb. **`python manage.py migrate` krävs** efter merge och före driftstart.
Kundens befintliga events är oförändrade; ingen backfill av historik.

Det finns **ännu inget godkänt retentionbeslut** för dessa loggkategorier.
Leveransen raderar därför inte historiska events automatiskt och är **inte**
ett påstående om GDPR-/AI-Act-compliance. Ta beslut om ändamål, åtkomst,
gallring, information och eventuell DPIA (#310) innan bredare
produktionsinsamling och inför kontrollerad retention.

## Test

`python manage.py test apps.activity.test_admin_activity_log_432 --noinput`

Plus befintlig Django QA, inklusive makemigrations-kontroll för `activity`.
Syntetiska tester omfattar staff-/kundnekad åtkomst, multi-tenant,
serverbaserade filter, CSV-dataminimering, säker adminattribution,
tomma tillstånd och två språk.

## Plan för resterande EPIC

1. #433: fastställ och godkänn eventkatalog + retention; implementera prioriterad serverinstrumentering enligt faktiska flöden och säkra korsreferenser till AI/rapportversioner
2. #434: utöka kandidat-/rapporttidslinjer, begränsad metadata-detalj och audit-adaptrar; förfina svensk/engelsk UI och mobil efter lokalt test
3. #435: aggregerade KPI:er och trendgraf från verifierat loggade händelser, utan individrankning och med korrekt täckningsstart
