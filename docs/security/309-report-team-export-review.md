# #309 – Rapport-, team- och exportåtkomst (andra granskningssteget)

**Omfattning:** kodgranskning och automatiska regressionsprov. All testdata är påhittad. Detta är **inte** en fullständig produktionspenetrationstestning eller slutligt godkännande av #309.

## Kodgranskade flöden

- `candidate_results:preview`: endast inloggade användare och globala Talena-administratörer får använda förhandsvisning; icke-admin måste få träff i `get_accessible_processes_for_user` för resultatets process, annars 404.
- `candidate_results:result`: kandidatens externa resultatsida kräver giltig token samt engångskod/sessionsverifiering; separat åtkomstmodell som behöver fortsatta livscykeltester.
- `teams:team_detail`: hämtar team med `_team_visibility_queryset` begränsat av företag/enhet/own. Begränsar därefter medlemslistan till kandidater i nåbara processer och begränsar teamstilarnas underlag med process-ID.
- `teams:team_insight_generate`: tillåter bara POST för användare med redigeringsrätt till synligt team. Otillåtna AJAX-anrop returnerar 403/404 innan AI genereras.
- `accounts:admin_usage_billing?export=csv`: skyddat av `admin_required`, inte av vanlig kundinloggning.
- Chefsrapportens PDF-knapp använder klientbaserad export från den redan behörighetsskyddade kandidaten i webbläsaren. En framtida servergenererad PDF/download-route måste ha motsvarande åtkomstkontroll.

## Nytt testpaket

`apps/processes/test_report_team_tenant_access.py` provar via Django HTTP client:
- annan kund, oåtkomlig organisationsenhet och own-only användare nekas visning av andra användares snapshots och team,
- godkända Viewer/Editor/Own-användare kan se endast tillåtna snapshots och team,
- teammedlemmar som inte kan nås genom några tillåtna processer syns inte även om en felaktig medlemskoppling finns,
- otillåten generering av team-AI når aldrig genereringsfunktionen,
- vanlig kundanvändare får inte hämta adminens fakturerings-CSV.

Dessa tester ingår i ordinarie Django QA-workflow på PR.

## Kvarvarande risker och uppföljning

- [ ] Systematisk inventering av alla bilagor, historiska rapporter, mediadownloads och externlagrade rapport-URL:er.
- [ ] Testa kandidatens publika token/kod-livscykel, spärr efter flera fel, länkrevo­kering samt delning/timeout; kandidatsidan har avsiktligt annan åtkomstmodell.
- [ ] Säkerställa att framtida PDF-exporter inte skapar egna oskyddade endpoints.
- [ ] Direkt-HTTP-verifiering av samtliga admin-endpoints och roller.
- [ ] Se över multi-company-medlemskap och val av aktiv kundkontext.
- [ ] Stage-verifiering med syntetiska kundkonton, även användare med flera organisationsenheter.
- [ ] Riskbedömning, loggning och åtgärdsförslag för eventuella kryss-scope-medlemskap i team och historiska importdata.

Full #309 bör fortfarande vara öppen tills kontrollpunkterna är avslutade.
