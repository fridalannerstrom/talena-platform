# Ticket #359 – gemensamt register för kandidatens PDF-rapporter

## Första implementationsetappen (2026-11-04)

- Nya `static/js/talena/candidate-report-export.js` registrerar endast rapporter
  vars *redan renderade* innehåll tillhör den auktoriserade kandidatvyn.
- `window.TalenaCandidateReports.getAvailableReports()` lämnar enbart
  identifierare, lokaliserad rubrik och generiskt filnamn. Saknade och
  ogenererade rapporter tas inte med i listan.
- `window.TalenaCandidateReports.exportReport(id, {returnBlob:true})` skapar
  samma PDF som en användares enskilda PDF-knapp, utan nedladdning. #360 kan
  återanvända filen i PDF-paket eller ZIP, men ingen packfunktion byggs här.
- Varje tillgänglig resultats-/rapportflik får en liten PDF-knapp. För
  ogenererade AI-flikar är knappen inaktiv med förklaring.
- Kundens befintliga branding (omslag, logotyp, färg) och den befintliga
  `TalenaPdfExport`-motorn används. Ingen AI-generering, inga anrop till Sova,
  inga PDF-filer lagras på servern.
- Färdiga AI-resultat hämtas från den sida användaren redan ser. Dold
  bakomliggande JSON-data, formulär och interaktiva knappar kopieras inte till
  PDF-snapshoten.
- Chefsrapportens befintliga PDF-knapp behålls. Registret exponerar även
  Chefsrapporten som Blob-baserad rapport när dess befintliga PDF-knapp är redo.
- Enhetligt SV/EN-gränssnitt. Saknade rapporter kan inte exporteras.

## Rapporter som registreras

| Nyckel | Källa | Villkor |
| --- | --- | --- |
| overview | Överblick | Renderad resultatsida |
| personality-results / interpretation / questions / candidate-reflection | Personlighet | Resultat finns, respektive AI-block sparat eller reflektion tillgänglig |
| motivation-results / interpretation / questions / candidate-reflection | Motivation | Motsvarande |
| cognitive-results / interpretation / questions / candidate-reflection | Färdighet | Motsvarande |
| team-report | Individuell teamprofil under Rapporter | Faktisk teamstilprofil finns |
| leadership-report | Ledarskapsrapport | Faktiskt rapportinnehåll finns |
| derailment-report | Urspårningsrapport | Faktiskt rapportinnehåll finns |
| prepare-interview | Inför intervju | Sparad/genererad förberedelse finns |
| after-overview | Efter intervju / Helhetsbild | Strukturerad syntes finns utan läckt teknisk källtext |
| after-interview | Efter intervju / Intervjusammanfattning | Sparat/genererat innehåll finns |
| after-explore | Efter intervju / Undersök vidare | Sparat/genererat innehåll finns |
| manager-report | Efter intervju / Chefsrapport | Befintlig PDF-knapp är aktiv; ingen dubbel knapp |

Rapporten kan innehålla fler än en sida; varje export får ett eget varumärkesomslag
och innehållet pagineras av Talenas befintliga motor.

## Säkerhet och begränsningar
- Rapportregistret ger **inte en ny server-URL för att läsa kandidatdata**.
  Det fungerar enbart inom det redan inloggade kandidatkortets befintliga
  behörighetskontroll. Ingen klientstyrd `candidate_id` eller `project_id`
  skickas till servern.
- Endast de uttryckligen registrerade DOM-sektionerna exporteras; externa
  Sova-PDF-länkar och andra kandidat-/projektvyer ingår inte automatiskt.
- Redaktionella ändringar i Chefsrapporten måste vara färdigladdade innan
  rapporten anses klar i registret. Export kopierar den synliga, sparade vyn.
- Innehåll som endast existerar som dold/gammal AI-data ska **inte** exporteras.
  Textytor i intervjuformulär exporteras inte som råa `textarea`-element.
- PDF-kroppen är ett bildbaserat snapshot (den befintliga Talena-motorn):
  brödtexten är alltså inte sökbar eller markerbar. #360 kräver en
  separat klickbar innehållsförteckning i sammanslagen PDF.
- När ett resultat innehåller en canvas krävs att grafen verkligen renderats;
  exporten avbryts i stället för att skapa en rapport med tom graf.

## Fortsatt verifiering innan #359 stängs
1. Kör Django QA, Node-källkontrakt och test av pdf-export-kärnan.
2. Kontrollera i webbläsare med syntetiska kandidatdata: SV/EN, alla registrerade
   flikar, data som saknas, ogenererade AI-avsnitt, omslagsbilder, transparent
   PNG-logo, långa rapporter, SVG- och canvasgrafer, sidbrytningar.
3. Kontrollera att knapparna finns även efter att Efter intervju-flikarna
   uppdaterats utan sidomladdning.
4. Testa att export från Chefsrapporten använder senast *sparade* manuella
   ändringar; PDF-formatet ska vara likvärdigt med existerande export.
5. Säkerställ att kandidatens egna portalrapporter och eventuella externa
   Sova-originalfiler fortsatt hanteras separat, utan oavsiktlig åtkomst.
6. Bygg därefter #360: valt urval/ordning, PDF-sammanslagning och ZIP samt
   länkad innehållsförteckning. Behörighets- och testdataisolering måste
   fortsätta gälla även för flera rapporter i ett paket.

Det här är en **första etapp** av #359 och ska inte stängas innan full
browser-/rapportmatris är verifierad.
