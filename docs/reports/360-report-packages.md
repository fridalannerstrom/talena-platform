# #360 Rapportpaket – första fungerande utvecklingsetappen (2026-11-04)

## Beroenden
Denna branch är medvetet **staplad på `feature/359-candidate-pdf-registry`** och ska inte mergas till main före att #359 granskats och mergats. Ingen migration eller server-endpoint behövs.

## Gränssnitt
- Knappen **Skapa rapportpaket / Create report package** visas i kandidatens befintliga insight-navigation, och följer det kandidatkort som öppnas dynamiskt via AJAX.
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
