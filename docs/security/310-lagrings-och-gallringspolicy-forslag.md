# Talena – förslag till lagrings- och gallringspolicy v0.2

**Status:** BESLUTSUNDERLAG v0.2, INTE JURIDISKT GODKÄND ELLER AKTIVERAD POLICY  
**Datum:** 2026-10-22  
**Ägare för tekniskt förslag:** Talena / Talent Qode  
**Produktbeslut 2026-10-22:** Föreslagen privat rekryteringsmall med **0–90 dagar normal åtkomst**, därefter **begränsad åtkomst endast för motiverat bevarande**, och **12 månader som föreslagen yttersta standardgräns**. Detta är ett produkt- och dokumentationsbeslut, **inte ett godkännande av rättslig grund för att lagra samtliga uppgifter i 12 månader**.  
**För godkännande:** behörig verksamhetsansvarig, ansvarig för personuppgiftsbehandling, respektive kunds personuppgiftsansvariga och jurist/dataskyddskompetens vid behov.  
**Ärenden:** [#310](https://github.com/fridalannerstrom/talena-platform/issues/310), [#307](https://github.com/fridalannerstrom/talena-platform/issues/307), [#308](https://github.com/fridalannerstrom/talena-platform/issues/308), [#311](https://github.com/fridalannerstrom/talena-platform/issues/311).

> **Driftsäker spärr:** Detta dokument får inte aktivera massradering i produktionsdatabasen. Ingen schemalagd radering, filgallring, databasändring eller ändring av Azure-backuper ingår här. De föreslagna tiderna är designval och måste valideras mot ändamål, rättslig grund, biträdesavtal och kundens dokumenterade instruktioner innan faktisk gallring.

## 1. Beslutsprinciper

1. **Ändamålet bestämmer tiden.** Arkivering i Talenas UI är inte samma sak som att avsluta rekrytering, och inaktivitet i sig är inte ett juridiskt skäl för omedelbar radering.
2. **Kunden styr sina personuppgifter** när Talent Qode/Talena agerar personuppgiftsbiträde. En kund kan vara privat arbetsgivare, offentlig arbetsgivare eller annan personuppgiftsansvarig; det går inte att hårdkoda exakt samma lagringstid för samtliga. Talena ska föreslå rimliga standardvärden och dokumentera godkända undantag.
3. **Ingen generell ett- eller tvåårsregel.** IMY säger att rekryteringsuppgifter som huvudregel ska raderas eller avidentifieras när de inte längre behövs, men att nödvändigt underlag ibland får sparas för rättsliga anspråk. Talenas **12-månadersstandard är ett föreslaget yttertak för prövat bevarande**, inte en generell lagringstid som automatiskt berättigar lagring i ett år eller ett frikort att behålla hela testprofiler.
4. **Minsta möjliga kvarvarande underlag.** Rättsliga anspråk, bokföring, revision och säkerhet kan ha skilda rättsliga ändamål. Behåll då bara vad som behövs, med separat åtkomst och slutdatum. Pseudonymiserade data är fortfarande personuppgifter om återidentifiering är möjlig.
5. **Fysiska kopior ingår.** Databas, Azure Blob, äldre importer/PDF:er, resultatdelningslänkar, Sova, eventuell Pinecone, driftloggar och säkerhetskopior ska inventeras och hanteras med dokumenterade instruktioner. Radering i Talena innebär inte automatiskt radering hos Sova.
6. **DPIA före lansering.** Rekrytering, profilering och AI-stöd kan medföra hög risk; resultat och datakategorier ska ingå i konsekvensbedömning, registerförteckning och kundinformation.

## 2. Föreslagen standard för vanlig privat rekrytering

Dessa tidsperioder är **produktförslag**, inte föreskrivna GDPR-tidsfrister.

| Datakategori / fas | Förslag Talena standard | När perioden startar | Hantering |
|---|---|---|---|
| Aktiv kandidat i aktiv rekrytering | Så länge ändamålet faktiskt pågår; granska långvarigt öppna processer | När kandidat går in i processen | Kundåtkomst enligt behörighet. Öppet projekt får inte ge oändlig retention; påminn om avslut efter 12 månaders inaktivitet och begär aktivt beslut |
| Operativ åtkomst efter avslutad rekrytering | **90 dagar** | Dokumenterat `closed_at` för aktuell process/kandidat (inte `archived_at`) | Under en kort avslutsperiod kan behöriga användare färdigställa dokumentation eller export. En begäran om radering ska behandlas enligt rättighetsrutinen, inte automatiskt vänta 90 dagar |
| Intervjuanteckningar, råtestdata, AI-genererade tolkningar, kandidatfeedback och resultatdelningsuppgifter | **Efter 90 dagar: granska och gallra/avidentifiera allt som inte längre behövs.** För återstående uppgifter krävs separat dokumenterat giltigt bevarandeändamål, snäva behörigheter och ett granskningsdatum; **föreslagen övre produktstandard 12 månader** efter avslut | Dokumenterat `closed_at` | Vid 90 dagar avslutas normal åtkomst och kvarvarande uppgifter skiljs från dagligt rekryteringsarbete. Återkalla länkar senast vid respektive datakategoris gallring. Hela testprofiler och AI-texter får inte automatiskt följa 12-månadersfönstret |
| Minimerat bevisunderlag för ett faktiskt motiverat behov att försvara rättsligt anspråk | **Högst 12 månader som föreslagen produktstandard**, *endast om rättslig grund, nödvändighet och kundinstruktion har dokumenterats*. Längre lagkrav/aktiv tvist kräver en särskilt beslutad avvikelse | Relevant dokumenterat avslut/beslut | Endast nödvändiga fakta och motiveringar, inte fulla personlighetsprofiler, rådata eller samtliga AI-texter som standard. Tidsbegränsad åtkomst, motivering, ansvarig och omprövningsdatum krävs |
| Kandidatpool/framtida rekryteringar | **Inte automatiskt inkluderat** | Separat dokumenterat och tillåtet ändamål | Kräver egen laglig grund och information; IMY anger att samtycke kan behövas för framtida rekrytering, men samtycke i arbetslivet är ofta problematiskt. Ingen tyst återanvändning av testresultat i nya processer |
| Kandidatens egna resultatsida och åtkomstkoder/tokens | Åtkomst under aktiva ändamålet och enligt avtal; **senast vid gallring återkallas den** | Utfärdande och/eller avslut | Resultatfilerna/snapshots följer relevant retention; tokens ska kunna återkallas tidigare och inte återaktiveras från backup |
| E-postlogg för drift/felsökning | **30 dagar efter utskick** för detaljsnapshot som föreslagen driftstandard, om inget legitimt behov av annat | `sent_at` | Undvik full `body_snapshot` för längre retention; minimera leveransmetadata. Avtalad incident- eller rättslig logg bevaras endast vid uttryckligt ändamål |
| Loggar för säkerhet/incidentutredning | **90 dagar** som föreslagen operativ standard, justeras efter hotbild/risk och avtal | Logghändelse | Skilj från kandidatens rekryteringsinnehåll; minimera PII och dokumentera avgränsad legal hold vid incident. Separata Azure-logginställningar måste verifieras |
| Originalfiler från historisk Excel-import | **Ta bort råoriginal senast 30 dagar efter verifierad, framgångsrik import** som designförslag; gemensamma filer måste hanteras separat | Importen har validerats och godkänts | Behåll normaliserad data enligt eget ändamål; tillämpa inte per-kandidat filradering på fil med flera kandidater |
| Föråldrade historiska PDF-filer | Inventera och besluta separat gallring | Efter kartläggning och godkännande | Funktion avvecklad i PR #331, men gamla DB-poster/Blob-filer kan finnas; ingen blind radering av container/prefix |
| Fakturaunderlag / räkenskapsinformation | **Lagstadgat bevarande för faktisk räkenskapsinformation: till och med sjunde året efter utgången av kalenderåret då räkenskapsåret avslutades** | Enligt bokföringslagen, inte `closed_at` | Detta gäller **inte automatiskt varje `AssessmentUsage`-fält**. Bevara minimum för redovisning, skilj från kandidatnamn/mejl, och utred PROTECT-relationerna före implementering |
| Azure Blob soft delete / PostgreSQL backup | **7 dagar** enligt nu verifierade Azure-inställningar | När objekt raderats / respektive återställningsfönster | Backupfönstret är inte tillstånd att lagra aktiva kandidatdata i sju extra dagar. Efter restore ska tidigare godkända raderingar återtillämpas och återställda tokens fortsätta vara spärrade |

### Beslutad produktriktning: 90 dagar normal åtkomst + upp till 12 månader prövat bevarande

**Talenas föreslagna standard för vanliga privata rekryteringar, version 0.2:**

| Tid efter dokumenterat rekryteringsavslut | Standardbeteende | Vad måste vara kontrollerat? |
|---|---|---|
| **Dag 0–90** | Normal åtkomst för slutförande av processen, men bara så länge uppgifterna faktiskt behövs. Tidigare gallring vid upphört ändamål eller giltig raderingsbegäran. | Kundens ändamål och dokumenterade instruktion; ingen generell rätt till 90 dagars extra lagring. |
| **Efter dag 90 till högst 12 månader** | Ordinarie åtkomst avslutas. **Enbart de specifika uppgifter** som fortfarande får och måste bevaras hålls separat med begränsad åtkomst. Övriga uppgifter gallras/avidentifieras. | Rättslig grund, proportionalitetsbedömning, dataminimering, ansvarig, angivet slutdatum och kundinstruktion. Ingen automatisk förlängning för alla resultat. |
| **Senast 12 månader** | Granska och gallra/avidentifiera återstående personuppgifter enligt godkänd policy. Undantag får bara tillämpas när annat lagkrav, arkivregel, aktivt rättsligt anspråk eller särskilt ändamål faktiskt är dokumenterat. | Separat beslut, åtkomstkontroll och omprövning för varje undantag. |

**Viktigt:** Ett år är här en **föreslagen maximal normalperiod för prövat bevarande**, inte ett löfte om att kundens kandidatuppgifter lagras exakt ett år. Om ett enskilt underlag inte längre behövs ska det gallras tidigare. GDPR kräver nödvändighet per ändamål, inte ett fast antal månader. Offentliga arbetsgivare kan ha avvikande skyldigheter enligt arkivregler.

**Tidigare förslag ersatt:** Version 0.1 föreslog generell gallring efter 90 dagar och prövat begränsat anspråksunderlag upp till 24 månader. **Version 0.2 ersätter dessa två föreslagna standardgränser**; 90 dagar är nu en gräns för normal åtkomst och manuell granskning, och 12 månader är den föreslagna övre gränsen för minimerat och berättigat bevarande. Det är fortfarande ett förslag som ska granskas juridiskt.

## 3. Andra processer får inte ärva rekryteringens klocka

- **Medarbetarutveckling, ledarskap och teaminsikter:** behandlingsändamål, dokumenterad rättslig grund, förnyelse-/granskningsdatum och separat raderingsregel per kund, exempelvis **årlig behovsprövning (12 månader)**. Detta är ett granskningsintervall, inte automatisk rätt att lagra eller ett generellt automatiskt raderingsdatum.
- **Flexibla testprocesser:** kräver att kunden anger ett faktiskt ändamål innan automatisk gallring kan planeras. Undvik att skapa eviga kandidatprofiler bara för att ett processyfte inte heter `hiring`.
- **Kommuner/offentliga arbetsgivare:** tillämpa kundens arkiv- och gallringsföreskrifter, krav på allmänna handlingar och dokumenterade instruktioner. Föreslagen privat rekryteringsstandard **får inte vara automatisk för offentlig sektor**.
- **Talena-kunder med egna personuppgiftsroller:** avtalet ska beskriva ansvar och instruktioner. Vid uppsägning ska data returneras eller raderas enligt godkända instruktioner och tillämpliga lagkrav.

## 4. Tekniskt föreslagen livscykel

```text
ACTIVE
  ├─ dokumenterat rekryteringsavslut → CLOSED_GRACE (max 90 dagars normal åtkomst, om nödvändigt)
  ├─ dataskyddsbegäran → PRIVACY_REVIEW (omedelbar triage)
  └─ lång inaktivitet → REVIEW_REQUIRED (ingen oövervakad evig lagring)

CLOSED_GRACE
  ├─ dag 90 (eller tidigare om behovet upphör) → REVIEW_AND_MINIMISE
  ├─ myndighets-/arkivinstruktion → CONTROLLER_SPECIFIC_HOLD
  └─ ingen giltig grund för fortsatt lagring → PURGE_QUEUED

REVIEW_AND_MINIMISE
  ├─ godkänt, dokumenterat bevarande → RESTRICTED_RETENTION (max 12 mån som förslag)
  └─ onödiga personuppgifter → PURGE_QUEUED

RESTRICTED_RETENTION
  ├─ nödvändighet upphör/senast föreslaget 12-månadersdatum → PURGE_QUEUED
  └─ separat styrkt lagkrav/aktiv tvist → LEGAL_HOLD (ansvarig + omprövning)

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
- Visa kundanvändaren `Avsluta kandidatprocess` (rekrytering kan ha flera kandidater), `Lagring och gallring`, `Planerat granskningsdatum`, `Begränsad åtkomst/undantag` och `Begär export/radering`. Ett projekt kan få separat `Avsluta rekrytering` när alla är färdiga. Förklara att **arkivering inte fastställer avslutsdatum och Talena-radering inte automatiskt gäller hos Sova**. Visa 90 dagar som åtkomstgranskning och 12 månader som föreslaget yttersta granskningsdatum, inte en automatisk raderingsrätt.
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
- [ ] Juridiskt signerad policyversion och eventuella kundspecifika instruktioner. **Särskilt: pröva om den föreslagna 12-månadersgränsen är motiverad för respektive datakategori**, och skilj den från arkiv- och preskriptionsregler.
- [ ] Explicit produktionsflagga för automatisk exekvering, **avstängd tills allt ovan är godkänt**.

## 7. Källor och avgränsningar

- IMY, Rekryteringssystem och kompetensdatabaser: https://www.imy.se/verksamhet/dataskydd/dataskydd-pa-olika-omraden/arbetsliv/rekryteringssystem-och-kompetensdatabaser/
- IMY, Personuppgiftsbiträdesavtal (artikel 28): https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/personuppgiftsansvariga-och-personuppgiftsbitraden/personuppgiftsbitradesavtal/
- IMY, Tidsfrister: https://www.imy.se/privatperson/dataskydd/dina-rattigheter/galler-for-alla-rattigheterna/tidsfrister/
- IMY, Konsekvensbedömning: https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/konsekvensbedomning/nar-ska-en-konsekvensbedomning-genomforas/
- Bokföringsnämnden, Arkivering: https://www.bfn.se/fragor-och-svar/arkivering/
- Svenska exempel (inte generell rättsregel): https://www.mio.se/om-mio/jobba-pa-mio/personuppgiftsbehandling-vid-rekrytering och https://www.forsakringskassan.se/om-forsakringskassan/behandling-av-personuppgifter/behandling-av-personuppgifter-nar-du-soker-jobb-hos-oss
- Kod-/datakarta: [310-kandidatdata-register-och-radering.md](./310-kandidatdata-register-och-radering.md) samt [310-readonly-kandidatinventering.md](./310-readonly-kandidatinventering.md).
