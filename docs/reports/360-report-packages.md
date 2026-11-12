# #360 Rapportpaket – första fungerande utvecklingsetappen (2026-11-04)

## Beroenden
Beroendet #359 (PR #446) mergades till `main` den 2026-11-04. Denna PR har nu `main` som bas för slutlig QA och merge. Ingen migration eller server-endpoint behövs.

## Gränssnitt
- Knappen **Skapa rapportpaket / Create report package** visas i **kandidatkortets övre högra hörn, i samma översta rad som namnet** (i befintlig `.candidate-profile-actions`), inte i insight-navigationens flikrad. Den följer det behöriga kandidatkort som öppnas dynamiskt via AJAX och återskapas inte dubbelt vid flikbyten.
- Ett modal-dialogfönster visar bara rapporter som är klara i det **aktuella auktoriserade kandidatkortets** PDF-register.
- Kryssrutor, välj/avmarkera alla, drag-and-drop och tangentbordstillgängliga upp/ned-knappar. Den visade ordningen styr PDF/ZIP.
- Välj **en sammanslagen PDF** eller **separata PDF:er i ZIP**. Ingen AI genereras vid export.
- Engelska och svenska texter. Progress och fel i dialogen.

## Export
- Samma `TalenaCandidateReports.exportReport(id,{returnBlob:true})` som enskilda PDF-knappar.
- ZIP: JSZip, en redan skapad PDF per valt id och stabilt filnamn.
- Merge: pdf-lib kopierar samtliga sidor från varje vald PDF i den ordning som valts, **utan att rendera om** dem. Först ett separat kundbrandat omslag från `exportCover()`, därefter vektorbaserad innehållsförteckning där varje rad har en intern PDF-länk (`/Dest` till första sidan i respektive rapport), sedan samtliga ursprungliga PDF-sidor. För närvarande ingår de individuella rapporternas egna omslag i sammanslagningen för att inga sidor ska tas bort.
- PDF/ZIP genereras lokalt i webbläsaren. Endast JavaScript-bibliotek hämtas vid behov via CDN, inga kandidatresultat laddas upp.
- Högst 20 rapporter, 100 MB resultat och 450 PDF-sidor vid sammanslagning. Felmeddelande vid överskridning.

## Kvar före merge/acceptans
- Automatiska tester i Django QA ska passera på sammanslagningen med #359.
- Faktiska webbläsartester med syntetiska kandidater, inklusive nya kandidatkort utan omstart, frånvarande/ogenererade/utdaterade rapporter, svenska/engelska, stora rapporter, canvas/SVG och transparent kundlogo.
- Kontrollera att internlänkar fungerar i Adobe Reader och vanliga webbläsar-PDF-läsare (Chrome/Edge), att ZIP öppnas och att exakt rätt filer ingår.
- Behörighet: testa olika kunder, behörigheter och två samtidigt öppnade kandidater. Samma kandidat och samma aktuella projekt är avsiktligt enda tillåtna paket.
- Stäm av Chefsrapport med senaste sparade manuella ändringar: den är beroende av #359:s färdiga/korrekta PDF-export och ska inte betraktas som verifierad ännu.
- Kontrollera tillgänglighet med tangentbord och skärmläsare; alla inbyggda ordningsknappar fungerar utan drag-and-drop.
- UX-justeringar och eventuellt snyggare slutligt rapportpaketsomslag efter visuell granskning.

**Ingen merge till main eller stängning av #359/#360 utan visuell QA.**


## Filnamn, kandidatidentifiering och integritet (2026-11-04)

- Enskilda PDF:er, PDF:er inuti ZIP, sammanslagen PDF och ZIP-filen får **förnamn och efternamn** före nuvarande rapportspecifika namn, till exempel `Anna Andersson - Personlighet - Resultat.pdf`, `Anna Andersson - Rapportpaket.pdf` och `Anna Andersson - Rapporter.zip`.
- Kandidatnamnet kommer från `data-report-export-name` i det **öppna och behöriga kandidatkortet**. Det attributet renderas med endast Django-fälten `first_name` och `last_name`. Rubrikens möjliga **e-postfallback används aldrig** som filnamn.
- Filnamn saneras från kontrolltecken, dubbelriktade styrtecken, sökvägsavgränsare och operativsystemets otillåtna filnamnstecken. Svenska och andra Unicode-bokstäver behålls. Namnet avgränsas till högst 90 Unicode-kodpunkter. Saknas namn används neutralt `talena-<rapport-id>.pdf`, `talena-rapportpaket.pdf` eller `talena-rapporter.zip`.
- För långvariga, asynkrona exporter låses filnamnet till kandidatkortets namn vid exportstart. Exportvalidering kontrollerar fortfarande att aktuellt kandidatkort finns kvar före nedladdning. Ingen kandidatidentitet läggs i URL:er, API-anrop eller felsökningsloggar och inga nya serverlagrade exportfiler skapas.
- **GDPR:** Namn i filnamn är personuppgifter. Namngivningen hjälper till att undvika förväxling i den redan behöriga rekryteringshanteringen, men nedladdade filer ska hanteras med samma åtkomstskydd, raderingsrutiner och säkerhet vid delning som själva rapportinnehållet. Talena kan inte automatiskt ta bort en fil som kunden laddat ner till sin egen enhet eller externa molntjänst.

## Team (separat ticket)

Teamets nuvarande ZIP-export av alla individuella teamprofiler ingår i #181 (stängd). Valbart urval av flera teammedlemmars profiler och en sammanslagen PDF/ZIP är **inte** scope för #360: se separat #449. Vid implementering av #449 måste teamets anonymitetsläge och användarbehörigheter styra både innehåll och filnamn.
