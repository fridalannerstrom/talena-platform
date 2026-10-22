# Historiska PDF-rapporter avvecklade 2026-10-22

Produktbeslut: historiska kandidater ska använda strukturerad importerad
testdata, **inte** separata uppladdade PDF-rapporter.

- PDF-upload och visning tas bort från admin- och kundvyerna.
- Den tidigare skyddade download-endpointen i #326 tas bort; gamla
  Talena-URL:er ska inte längre kunna användas.
- Django admin registrerar inte längre den gamla PDF-modellen.
- Vanliga Sova-kandidaters rapporter och historiskt importerade Excel-data
  behålls.
- **Inga befintliga Blob-filer eller databasposter raderas i denna ändring.**
  Radering av lagrade filer måste först inventeras och beslutas inom #310,
  inklusive säkra backuper, loggar och verifierad datakoppling.
- Tidigare utgivna SAS-URL:er kan finnas kvar till utgångstid.

## Tidigare säkerhetsgranskning (#326)

# #309 – Historiska rapporter: skyddad PDF-åtkomst

Datum: 2026-10-21. Kodgranskning + automatiska tester (syntetiska filer).
Denna åtgärd är ett **delsteg**. Det är inte ett påstående att hela #309 eller Talenas filhantering är säkerhetsgranskad.

## Fynd

I två mallar länkades uppladdade historiska SOVA-rapporter direkt via
`{{ report.file.url }}`:
- `templates/customer/processes/partials/candidate_insights/_workspace.html`
- `templates/admin/accounts/companies/company_candidate_sheet.html`

Dessa länkar kan vara direkta lagrings-URL:er (eller signerade SAS-URL:er
när Azure Storage är aktivt). Då görs ingen ny användar-/tenantkontroll av
Talena när fil-URL:en återanvänds eller sprids. Om containern är publik
kan filen eventuellt läsas direkt utan autentisering. Vi har **inte**
verifierat aktuell containerns public access eller SAS-policy i Azure.

## Åtgärd i denna PR

- `historical_candidate_report_download` under
  `apps/processes/historical_report_downloads.py`.
- Kräver inloggning samt den redan centrala
  `process_view_access_required`: rätt företag, process och org-unit
  (Own, Viewer eller Editor); plattformsadministratörer kan se samtliga.
- Rapporten måste höra till **exakt samma process och kandidat** som URL:en
  hänvisar till. Felaktigt eller tillhörighetsmässigt mismatchande ID ger 404.
- PDF:en levereras av Django via `FileResponse`, utan att exponera
  storage-backendens direkta URL. `Cache-Control: private, no-store`,
  `X-Content-Type-Options: nosniff`.
- Båda mallarna använder den skyddade Django-URL:en.
- Regressionskontroller för anonym, fel kund, otillåten org-unit,
  own-only på annans process, auktoriserad viewer/editor/admin och
  fel rapport-/kandidat-ID. Inga riktiga dokument används.

## Viktig begränsning: Azure och redan utdelade länkar

Den skyddade Django-endpointen kan **inte** automatiskt dra tillbaka
tidigare utlämnade direkt-URL:er eller påverka Azure Blob Storage:s
eventuella publika container-åtkomst. SAS-URL:er kan vara giltiga tills
deras utgångstid. Ingen automatisk globallåsning av lagring genomförs här.

Före lanseringssignoff behövs en separat driftkontroll:
- [ ] Verifiera att Azure Blob-containern som lagrar kandidatrapporter
      har **Private** access, inklusive storage account-behörigheter
      och att anonymous blob access är avstängd.
- [ ] Granska SAS-URL-livslängd, signering, nyckelrotation samt historiska
      redan delade URL:er. `AZURE_URL_EXPIRATION_SECS` är förvalt till 3600,
      men faktiskt driftläge måste kontrolleras.
- [ ] Kontrollera att även andra uppladdade känsliga objekt
      (exempelvis historiska importfiler) inte exponeras via direkta länkar.
- [ ] Testa nedladdning från Azure i stage med syntetiska PDF:er;
      säkra att storage-backenden stöder streaming och att ingen
      oavsiktlig fullbuffring sker vid stora dokument.
- [ ] Testa gamla länkar efter utloggning och eventuell spärrning.
- [ ] Verifiera multi-company-åtkomstpolicyn och samtliga adminendpoints.
