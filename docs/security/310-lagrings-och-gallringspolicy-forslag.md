# Talena – förslag till lagrings- och gallringspolicy v0.1

**Status:** BESLUTSUNDERLAG, INTE GODKÄND ELLER AKTIVERAD POLICY  
**Datum:** 2026-10-22  
**Ägare för tekniskt förslag:** Talena / Talent Qode  
**För godkännande:** behörig verksamhetsansvarig, ansvarig för personuppgiftsbehandling, respektive kunds personuppgiftsansvariga och jurist/dataskyddskompetens vid behov.  
**Ärenden:** [#310](https://github.com/fridalannerstrom/talena-platform/issues/310), [#307](https://github.com/fridalannerstrom/talena-platform/issues/307), [#308](https://github.com/fridalannerstrom/talena-platform/issues/308), [#311](https://github.com/fridalannerstrom/talena-platform/issues/311).

> **Driftsäker spärr:** Detta dokument får inte aktivera massradering i produktionsdatabasen. Ingen schemalagd radering, filgallring, databasändring eller ändring av Azure-backuper ingår här. De föreslagna tiderna är designval och måste valideras mot ändamål, rättslig grund, biträdesavtal och kundens dokumenterade instruktioner innan faktisk gallring.

## 1. Beslutsprinciper

1. **Ändamålet bestämmer tiden.** Arkivering i Talenas UI är inte samma sak som att avsluta rekrytering, och inaktivitet i sig är inte ett juridiskt skäl för omedelbar radering.
2. **Kunden styr sina personuppgifter** när Talent Qode/Talena agerar personuppgiftsbiträde. En kund kan vara privat arbetsgivare, offentlig arbetsgivare eller annan personuppgiftsansvarig; det går inte att hårdkoda exakt samma lagringstid för samtliga. Talena ska föreslå rimliga standardvärden och dokumentera godkända undantag.
3. **Ingen automatisk tvåårsregel.** IMY säger att rekryteringsuppgifter som huvudregel ska tas bort efter behovet upphört, men att visst underlag kan få sparas för rättsliga anspråk. Ungefär 24 månader används av vissa svenska arbetsgivare, men är inte ett generellt krav eller ett frikort att spara samtliga tester, fritextfält och AI-rapporter i 24 månader.
4. **Minsta möjliga kvarvarande underlag.** Rättsliga anspråk, bokföring, revision och säkerhet kan ha skilda rättsliga ändamål. Behåll då bara vad som behövs, med separat åtkomst och slutdatum. Pseudonymiserade data är fortfarande personuppgifter om återidentifiering är möjlig.
5. **Fysiska kopior ingår.** Databas, Azure Blob, äldre importer/PDF:er, resultatdelningslänkar, Sova, eventuell Pinecone, driftloggar och säkerhetskopior ska inventeras och hanteras med dokumenterade instruktioner. Radering i Talena innebär inte automatiskt radering hos Sova.
6. **DPIA före lansering.** Rekrytering, profilering och AI-stöd kan medföra hög risk; resultat och datakategorier ska ingå i konsekvensbedömning, registerförteckning och kundinformation.

## 2. Föreslagen standard för vanlig privat rekrytering

Dessa tidsperioder är **produktförslag**, inte föreskrivna GDPR-tidsfrister.

| Datakategori / fas | Förslag Talena standard | När perioden startar | Hantering |
|---|---|---|---|
| Aktiv kandidat i aktiv rekrytering | Så länge ändamålet faktiskt pågår; granska långvarigt öppna processer | När kandidat går in i processen | Kundåtkomst enligt behörighet. Öppet projekt får inte ge oändlig retention; påminn om avslut efter 12 månaders inaktivitet och begär aktivt beslut |
| Operativ åtkomst efter avslutad rekrytering | **90 dagar** | Dokumenterat `closed_at` för aktuell process/kandidat (inte `archived_at`) | Under en kort avslutsperiod kan behöriga användare färdigställa dokumentation eller export. En begäran om radering ska behandlas enligt rättighetsrutinen, inte automatiskt vänta 90 dagar |
| Intervjuanteckningar, råtestdata, AI-genererade tolkningar, kandidatfeedback och tillfälliga resultatdelningsuppgifter | **Gallra eller anonymisera efter 90 dagar** från avslut, om inget särskilt dokumenterat lagligt bevarandeändamål finns | `closed_at` | Återkalla åtkomstlänkar. Särskilt integritetskänsliga underlag ska inte behållas bara av bekvämlighet. Separat granskningsbeslut krävs om något behöver bevaras |
| Minimerat bevisunderlag för ett faktiskt motiverat behov att försvara rättsligt anspråk | Föreslagen **övre produktstandard 24 månader**, endast efter dokumenterat beslut och med åtkomstbegränsning | Relevant rekryteringsbeslut/avslut, enligt kundens beslut | Endast nödvändiga fakta och motiveringar, inte automatiskt fulla personlighetsprofiler, rådata och alla AI-texter. Legal hold vid faktisk tvist hanteras separat med beslutsägare och omprövningsdatum |
| Kandidatpool/framtida rekryteringar | **Inte automatiskt inkluderat** | Separat dokumenterat och tillåtet ändamål | Kräver egen laglig grund och information; IMY anger att samtycke kan behövas för framtida rekrytering, men samtycke i arbetslivet är ofta problematiskt. Ingen tyst återanvändning av testresultat i nya processer |
| Kandidatens egna resultatsida och åtkomstkoder/tokens | Åtkomst under aktiva ändamålet och enligt avtal; **senast vid gallring återkallas den** | Utfärdande och/eller avslut | Resultatfilerna/snapshots följer relevant retention; tokens ska kunna återkallas tidigare och inte återaktiveras från backup |
| E-postlogg för drift/felsökning | **30 dagar efter utskick** för detaljsnapshot som föreslagen driftstandard, om inget legitimt behov av annat | `sent_at` | Undvik full `body_snapshot` för längre retention; minimera leveransmetadata. Avtalad incident- eller rättslig logg bevaras endast vid uttryckligt ändamål |
| Loggar för säkerhet/incidentutredning | **90 dagar** som föreslagen operativ standard, justeras efter hotbild/risk och avtal | Logghändelse | Skilj från kandidatens rekryteringsinnehåll; minimera PII och dokumentera avgränsad legal hold vid incident. Separata Azure-logginställningar måste verifieras |
| Originalfiler från historisk Excel-import | **Ta bort råoriginal senast 30 dagar efter verifierad, framgångsrik import** som designförslag; gemensamma filer måste hanteras separat | Importen har validerats och godkänts | Behåll normaliserad data enligt eget ändamål; tillämpa inte per-kandidat filradering på fil med flera kandidater |
| Föråldrade historiska PDF-filer | Inventera och besluta separat gallring | Efter kartläggning och godkännande | Funktion avvecklad i PR #331, men gamla DB-poster/Blob-filer kan finnas; ingen blind radering av container/prefix |
| Fakturaunderlag / räkenskapsinformation | **Lagstadgat bevarande för faktisk räkenskapsinformation: till och med sjunde året efter utgången av kalenderåret då räkenskapsåret avslutades** | Enligt bokföringslagen, inte `closed_at` | Detta gäller **inte automatiskt varje `AssessmentUsage`-fält**. Bevara minimum för redovisning, skilj från kandidatnamn/mejl, och utred PROTECT-relationerna före implementering |
| Azure Blob soft delete / PostgreSQL backup | **7 dagar** enligt nu verifierade Azure-inställningar | När objekt raderats / respektive återställningsfönster | Backupfönstret är inte tillstånd att lagra aktiva kandidatdata i sju extra dagar. Efter restore ska tidigare godkända raderingar återtillämpas och återställda tokens fortsätta vara spärrade |

### Varför 90 dagar + separat 24-månadersprövning?

Det ger ett tydligt operativt avslut och undviker att **alla** personlighets- och motivationsresultat, intervjucitat eller AI-texter lagras i två år av slentrian. Samtidigt kan en kund med dokumenterat behov bevara ett relevant och minimerat underlag för rättsliga anspråk. Om kunden faktiskt måste bevara mer kan det kräva andra regler, åtkomstkontroller och proportionalitetsbedömning. `24 månader` är en föreslagen övre standardkonfiguration, **inte automatisk lagringsrätt**.

## 3. Andra processer får inte ärva rekryteringens klocka

- **Medarbetarutveckling, ledarskap och teaminsikter:** behandlingsändamål, dokumenterad rättslig grund, förnyelse-/granskningsdatum och separat raderingsregel per kund, exempelvis **årlig behovsprövning (12 månader)**. Detta är ett granskningsintervall, inte automatisk rätt att lagra eller ett generellt automatiskt raderingsdatum.
- **Flexibla testprocesser:** kräver att kunden anger ett faktiskt ändamål innan automatisk gallring kan planeras. Undvik att skapa eviga kandidatprofiler bara för att ett processyfte inte heter `hiring`.
- **Kommuner/offentliga arbetsgivare:** tillämpa kundens arkiv- och gallringsföreskrifter, krav på allmänna handlingar och dokumenterade instruktioner. Föreslagen privat rekryteringsstandard **får inte vara automatisk för offentlig sektor**.
- **Talena-kunder med egna personuppgiftsroller:** avtalet ska beskriva ansvar och instruktioner. Vid uppsägning ska data returneras eller raderas enligt godkända instruktioner och tillämpliga lagkrav.

## 4. Tekniskt föreslagen livscykel

```text
ACTIVE
  ├─ dokumenterat rekryteringsavslut → CLOSED_GRACE (90 dagar föreslaget)
  ├─ dataskyddsbegäran → PRIVACY_REVIEW (omedelbar triage)
  └─ lång inaktivitet → REVIEW_REQUIRED (ingen oövervakad evig lagring)

CLOSED_GRACE
  ├─ dokumenterat, begränsat bevarandeändamål → RESTRICTED_RETENTION
  ├─ myndighets-/arkivinstruktion → CONTROLLER_SPECIFIC_HOLD
  └─ förfallen, godkänd åtgärd → PURGE_QUEUED → PURGED

RESTRICTED_RETENTION
  ├─ bevarandebehov slut/frist passerad → PURGE_QUEUED
  └─ aktiv tvist → LEGAL_HOLD (orsak, beslutsfattare, omprövningsdatum)

PURGE_QUEUED → REVOKE_ACCESS → DELETE_OR_MINIMISE_DB →
DELETE_OR_DETACH_BLOBS → SUBPROCESSOR_FOLLOWUP → VERIFIED
```

- **`archive` är bara UI-organisering.** En ny explicit åtgärd `Avsluta rekrytering` sätter `closed_at` och `closed_by`. Ett projekt med flera kandidater kan behöva kandidat-/projektvis beslut.
- Definiera en **versionsstyrd `RetentionPolicy`** per företag, ändamål, datakategori och eventuellt process. Dokumentera `approved_by`, `approved_at`, `legal_basis/reference`, giltighetsdatum och `revision_due`.
- Definiera en **`RetentionDecision/DeletionRequest`** per konkret kandidat-och-företag med status, åtgärdsorsak, beslut om minimering, spårbarhet och eventuella blockerare. Ingen lagring av rått testinnehåll i revisionsloggen.
- Bygg ett **dagligt, idempotent verktyg med dry-run som förval** som kan simulera vad som skulle hända, med aggregerade tal och blockerare. Sätt en explicit aktiveringsflagga först efter godkänd DPIA, juridik, tenant- och restoretest.
- Kräv **tvåstegsbekräftelse** och behörighetskontroller för manuella raderingsåtgärder. Ett kundföretag får inte ta bort andra kunders relationer till samma globala `Candidate`; dagens `Candidate.email` är unik globalt.
- Hantera `AssessmentUsage.candidate` och `.invitation` (`PROTECT`) genom godkänd design för fakturaunderlag och avidentifiering innan fysisk kandidat-/inbjudningsradering.
- Radera fysiska Azure Blob-objekt via separat säker, återupptagbar process (Django `FileField`-relation räcker inte). Historisk importfil kan innehålla flera kandidater.
- Revoke/resultatlänkar och sessioner tidigt. Vid backup-restore ska `tombstones`/minimal raderingsjournal kunna återspela raderingsbeslut utan att återintroducera personuppgifter eller gamla åtkomster.
- Visa kundanvändaren `Avsluta rekrytering`, `Lagring och gallring`, `Planerat gallringsdatum`, `Bevaras för annat ändamål` och `Begär export/radering`. Förklara att **arkivering inte stoppar klockan och radering inte gäller hos Sova automatiskt**.
- Skapa notifiering när avsluts-/retentionperiod närmar sig slutet, men **ingen klick-knapp som utan utredning förlänger retention**.

## 5. Registerutdrag och begärd radering

- Kandidatens begäran ska registreras säkert, identitet och berörd personuppgiftsansvarig verifieras och prövas utan onödigt dröjsmål. **Normalt ska svar lämnas inom en månad**, med förlängning i vissa fall enligt GDPR.
- Biträdet Talena ska stödja den personuppgiftsansvariges dokumenterade beslut, inte själv avslå eller godkänna alla juridiska grunder.
- Förklara exakt vad som har raderats, vad som måste/lagligen får bevaras och vad som finns i tidsbegränsade backuper; gör inte absoluta garantier om extern Sova-radering utan verifiering.
- Vid avslutad kundrelation erbjud återlämning eller radering enligt biträdesavtalet, med undantag när tillämplig rätt kräver lagring.

## 6. Säkerhetsgränser före någon automatisk gallring

- [ ] Dokumenterad ansvarsfördelning, rättslig grund, ändamål och kundinstruktion.
- [ ] DPIA/riskbedömning uppdaterad för Talenas testresultat, AI-tolkningar och automatisk gallring (#311).
- [ ] Dokumentera **verifierad** retention och raderingsväg för Sova (#91/#92), OpenAI (#303/#304), Pinecone, e-post och Azure-diagnostik.
- [ ] Syntetiska tester för delad `Candidate` över flera kunder, PROTECT, borttagna kandidatportallänkar, teaminsikter, uppladdad gemensam Excel, äldre PDF och filtrerad export.
- [ ] Restore-test med återtillämpning av raderingsjournal och spärr av återställda åtkomsttokens.
- [ ] Manuell förhandsgranskning av berörda objekt och aggregerade antal; no-PII auditlog.
- [ ] Juridiskt signerad policyversion och eventuella kundspecifika instruktioner.
- [ ] Explicit produktionsflagga för automatisk exekvering, **avstängd tills allt ovan är godkänt**.

## 7. Källor och avgränsningar

- IMY, Rekryteringssystem och kompetensdatabaser: https://www.imy.se/verksamhet/dataskydd/dataskydd-pa-olika-omraden/arbetsliv/rekryteringssystem-och-kompetensdatabaser/
- IMY, Personuppgiftsbiträdesavtal (artikel 28): https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/personuppgiftsansvariga-och-personuppgiftsbitraden/personuppgiftsbitradesavtal/
- IMY, Tidsfrister: https://www.imy.se/privatperson/dataskydd/dina-rattigheter/galler-for-alla-rattigheterna/tidsfrister/
- IMY, Konsekvensbedömning: https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/konsekvensbedomning/nar-ska-en-konsekvensbedomning-genomforas/
- Bokföringsnämnden, Arkivering: https://www.bfn.se/fragor-och-svar/arkivering/
- Svenska exempel (inte generell rättsregel): https://www.mio.se/om-mio/jobba-pa-mio/personuppgiftsbehandling-vid-rekrytering och https://www.forsakringskassan.se/om-forsakringskassan/behandling-av-personuppgifter/behandling-av-personuppgifter-nar-du-soker-jobb-hos-oss
- Kod-/datakarta: [310-kandidatdata-register-och-radering.md](./310-kandidatdata-register-och-radering.md) samt [310-readonly-kandidatinventering.md](./310-readonly-kandidatinventering.md).
