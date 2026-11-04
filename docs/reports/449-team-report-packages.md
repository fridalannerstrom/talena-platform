# #449 – Skapa teamrapportpaket

Första utvecklingsetappen 2026-11-04. **Draft, inte produktionsgodkänd.**

## Var i Talena?

På befintliga **teamets detaljsida**, bland teamets huvudåtgärder, visas
`Skapa teamrapportpaket` när aggregerade teamresultat finns.
De befintliga knapparna för **Ladda ner teamrapport**, **Ladda ner alla teamprofiler (ZIP)**
och nedladdning av en enda medlems profil behålls oförändrade.

## Vilka rapporter kan väljas?

- **Sammansatt teamrapport** om den befintliga #180-exporten har data.
- **Individuell teamprofil: [medlem]** för varje teammedlem vars profil är
  fullständig och renderad i den aktuellt behöriga teamvyn.
- Saknade/ej färdiga profiler räknas och förklaras; de exporteras inte.
- **Ingen automatisk AI-generering**. Endast de redan tillgängliga rapporterna används.

Välj alla/avmarkera, drag-and-drop och tangentbordets flytta-upp/ned.
Två nedladdningsformat: **en gemensam PDF** eller **separata PDF-filer i ZIP**.
Den ordning som visas i väljaren används också vid export. ZIP-namnen får
ordningsprefix (01, 02, …) så att filhanterare inte tappar sorteringen.

## Exakt samma rapporter som idag

`TalenaTeamProfilesExport.exportProfileForPackage(id)` återanvänder
den befintliga `createPdf(profile)` från #181, inklusive branding, canvas,
sidbrytningar och sparad profil.

`TalenaTeamReportExport.exportReportForPackage()` återanvänder den befintliga
`renderPdf()` för den sammansatta rapporten från #180.

`TalenaReportPackageCore` är en **gemensam** PDF/ZIP-motor som extraherats från
kandidatväljaren i #360. Den används av både #360 och #449.
Vid sammanslagning läggs först ett brandat teamomslag och en klickbar
innehållsförteckning (interna PDF-destinationer). De individuella PDF-sidorna
kopieras intakta med befintliga omslag. ZIP innehåller separata PDF-Blobar.

## Integritet och behörighet

- Detta är **ett enda team i en redan auktoriserad teamvy**. Ingen ny
  backend-route läser kandidater eller rapporter. Medlems-ID:n måste matcha
  befintliga, kompletta profiler som faktiskt renderats på den sidan.
- I anonymiserat läge är hela identifierande teamrapportpaketsfunktionen
  blockerad, i stället för att riskera identifierande individuella rapporter.
  Befintlig separat **anonymiserad sammansatt teamrapport** från #180 är kvar.
- Anonymitetsswitchen kontrolleras vid öppning, före varje rapport, efter
  varje async PDF, och direkt före nedladdning. Växling till anonymt läge
  stänger omedelbart dialogen och **avbryter** även en export som pågår.
  Växling tillbaka under samma export återupptar den inte.
- Knappen visas inte förrän sessionens anonymitet har återställts.
  Endast initialt behörig medlemsdata används och filnamn/mellandata
  sparas inte på servern eller skickas till AI/Sova.
- Team-/medlemsnamn i filer tillåts **endast när anonymisering är av**.
  Filnamn saneras från sökvägs- och styrtecken, utan att å/ä/ö förstörs.
  Dessa PDF:er och ZIP är personuppgifter och ska hanteras/gallras som övrig
  nedladdad kandidatdata.

## Gränser och säkerhet

Högst 40 PDF:er, totalt högst 100 MB och högst 450 sidor i sammanslagning.
Progress och tydliga fel visas i dialogen och teamvyn. Inget nytt AI-anrop,
inget nytt HTTP-endpoint, ingen databasändring/migration.

## Beroenden och QA

PR #450 riktas nu mot `main` för full CI. PR #446 (#359) är redan mergad,
medan PR #448 (#360) måste passera full QA och mergas **före** denna PR.
Branchens historik omfattar fortfarande båda tidigare funktionsgrenarna,
men GitHub jämför automatiskt bort redan mergade commits. Inga ändringar
skickas till produktion innan respektive PR mergas till `main`.

Kod- och anonymitetskontrakten körs i
`scripts/test_team_report_packages_contract.js` via Django QA.
#180/#181:s befintliga exportkontroller och #360:s PDF-registertest fortsätter
också köras.

**Manuell QA kvar:**
- Vanligt team med 2, 5 och 20+ medlemmar: en PDF/ZIP med rätt filer,
  namn, ordning och branding, inklusive transparent PNG-logotyp.
- PDF-länkar i Chrome, Edge och Adobe Reader, längre rapporters sidbrytning,
  bild-/canvasinnehåll, storleksgränser och tomma/ofärdiga profiler.
- Aktivt anonymt läge och växling mitt under PDF-rendering (absolut ingen
  identifierande nedladdning), även när sessionen startar anonymiserad.
- Olika kunder, roller, teammedlemskap och byten mellan team. Inga andra
  kunders eller kandidaters data ska kunna exporteras.
- Responsivt läge, drag-and-drop, tangentbordsflytt och skärmläsare.

**Kopplat till** #449, #181, #180, #182, #359, #360.

## Buggrättning 2026-11-04: tom rapportväljare trots teamresultat

Orsak som identifierades i koden: de två befintliga exportskripten
`team-profile-export.js` och `team-report-export.js` hade uppdaterats med
#449-adaptrar men låg fortfarande i teammallen **utan versionsparameter**.
Webbläsaren kunde därför använda en tidigare cachad version utan
`window.TalenaTeamProfilesExport` respektive `window.TalenaTeamReportExport`.
Rapportväljaren tolkade dessa saknade funktioner som noll färdiga rapporter.

- Nya explicita cacheversioner för båda exportadaptrarna och rapportväljaren
  i `team_detail.html`, i korrekt skriptordning.
- Väljaren skiljer nu på **inga färdiga rapporter** och **saknade exportfunktioner**.
  Den senare situationen visar en tydlig svensk/engelsk feltext och skapar
  ingen missvisande tom dialog.
- Nytt kört regressionstest verifierar att en sammansatt rapport och två
  färdiga individuella profiler verkligen blir **tre valbara rapporter**.
  Saknad adapter och anonymt läge kontrolleras separat.
- Fortfarande krävs lokal webbläsarverifiering på ett riktigt team.

## Teamheader / UX-förbättring (2026-11-04)

Efter visuell granskning gjordes teamets toppsektion om till en diskret vit
rubrikkort-yta med mer utrymme för teamnamnet och en kompakt åtgärdsrad.
Följande åtgärder finns direkt i headern:

- **Skapa teamrapportpaket** (primärknapp när resultat finns, respekterar anonymisering).
- **Redigera medlemmar** (sekundärknapp).
- **Anonymisera** (synlig switch med oförändrat beteende).
- **Fler åtgärder**: gruppering Rapporter (Ladda ner teamrapport, Ladda ner individuella teamprofiler) och Hantera team (Redigera team, samt Ta bort team om `can_edit_team`).

Fler-menyn bygger på semantisk `details/summary` så den fungerar även utan
JavaScript; med JS stängs den på Escape (fokus åter till trigger), klick
utanför, när en åtgärd väljs eller när fokus flyttas ut.
Exporternas **ursprungliga knappar/data-attribut**, länkar och permissionsvillkor
behålls. Alla tre statusfält för nedladdning ligger **utanför dropdownen** för
att kunna visa export-progress och fel även när menyn stängs. Anpassningar
för desktop, tablet, mobil och reducerad animation.

`scripts/test_team_header_actions_contract.js` kontrollerar dessa avtal,
inklusive tangentbords-/dropdownbeteende och att äldre knappar finns kvar.
Manuell layoutgranskning i riktig webbläsare och kontroll av PDF-/ZIP-export
återstår före merge.
