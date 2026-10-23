# Säkerhetskontroll inför aktivering: äldre Sova-webhook (#309)

**Datum:** 2026-10-23  
**Status:** Kod och syntetiska tester i PR, **INTE säker att automatiskt produktionsmerga utan kontroll av Sova-konfigurationen**.

## Fynd

`core:sova_webhook` i `apps/core/webhooks.py` nås på core-webhookrouten i `apps/core/urls.py` och har historiskt tillåtit osignerade/anonyma HTTP POST-meddelanden som kan påverka `TestInvitation`-status och sparade resultat. CSRF-undantag utan annan avsändarautentisering är inte tillräckligt. Den nyare `integrations:sova_ingest` har redan en delad-hemlighetskontroll.

## Implementering

Äldre routen verifierar nu `X-Talena-Webhook-Secret` mot konfigurerad `SOVA_WEBHOOK_TEST_SECRET`, `SOVA_WEBHOOK_PROD_SECRET` eller `SOVA_WEBHOOK_SHARED_SECRET` med `secrets.compare_digest`. Saknad, fel eller helt okonfigurerad hemlighet ger HTTP 401 **före payloadtolkning och databasändringar**; andra HTTP-metoder ger 405.

Syntetiska HTTP-tester i `apps/core/test_sova_webhook_security.py` ingår uttryckligen i Django QA. Testerna använder en okänd påhittad `request_id` och kontaktar inte Sova.

## Obligatoriska driftsättningskontroller före merge

1. Ta reda på **exakt callback-URL** som finns registrerad för Sova test och produktion och om den använder den gamla routen eller `integrations:sova_ingest`. Ändra inte någon webhook-URL utan plan.
2. Verifiera att Sova faktiskt skickar `X-Talena-Webhook-Secret` till alla aktiva callback-URL:er, med **rätt konfigurerat värde i Azure**. **Dela inte sekret i GitHub, chatt, dokument, logg eller screenshots.**
3. Om någon aktiv integration använder den äldre routen **utan** den headern: koordinera först en leverantörsändring till autentiserad callback, annars börjar Talena neka 401 efter produktionsdeploy.
4. Efter godkänd driftsättning: testa med **syntetiska** payloads, verifiera 401 för felaktig header samt fungerande auktoriserad statusuppdatering med ett syntetiskt testobjekt. Följ webhook-status och larm vid ökade 401.
5. Dokumentera datum, ansvarig, callback-variant och resultat av test. Först därefter betrakta denna del av #309 som åtgärdad.

Tidigare lagrade data och andra tenant-behörigheter omfattas inte av denna specifika ändring. #309 i sin helhet förblir öppen för resterande endpoint- och nedladdningstester.
