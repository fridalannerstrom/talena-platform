# #309 – Åtkomstgranskning (pågår)

## Granskat och åtgärdat i denna PR

Talena har en befintlig central behörighetsmodell i
`apps/processes/access_control.py` och `apps/accounts/utils/org_access.py`:
- Global Talena-admin undantas avsiktligt från kundbegränsningarna.
- Övriga användare måste tillhöra rätt företag och ha rättigheter till
  processens organisationsenhet, med behörigheterna own/viewer/editor.
- Kandidatvyer, frågeanteckningar och de flesta AI-genereringsvägar skyddas
  redan genom de centrala URL-wrappers i `apps/processes/urls.py`.

### Fynd och korrigeringar

1. `process_invitation_statuses` hade en lokal kontroll för företag men saknade
   org-unit-/own-behörighetskontroll. En användare i samma företag kunde
   därför efterfråga status för en process hen inte fått tilldelad. Nu går
   endpointen genom `process_view_access_required`.
2. `process_role_context` saknade kontroll av organisationsenhet och
   tillät POST utan kontroll av redigeringsbehörighet. Nu:
   - GET skyddas centralt med view-behörighet.
   - POST kräver dessutom `user_can_edit_process` innan databasen påverkas.
3. Frågeanteckningarnas endpoints var **redan skyddade** genom URL-wrappers,
   trots att motsvarande kontroll inte ligger i själva vyfunktionerna.
   Vi lämnar därför deras logik oförändrad.

### Regressionstest på verkliga Django-URL:er

`apps/processes/test_tenant_authorization.py` testar bland annat:
- annan kund/tenant avvisas från kandidatvyn, slutunderlag, noteringar,
  inbjudningsstatus och rollkontext,
- användare i samma kund utan rätt org-unit-åtkomst och own-only mot kollegas
  process nekas,
- viewer kan läsa tillåten status/notering men inte ändra noterad data eller
  rollkontext,
- editor kan spara tillåtna frågeanteckningar,
- own-only kan läsa egen process,
- kandidat-ID kan inte kombineras med fel process-ID.

Django QA kör nu dessa tester automatiskt på PR:er.

## Återstår för att stänga hela #309

Detta är **ett första begränsat revisionssteg**, inte ett fullständigt godkännande
av åtkomstskyddet för samtliga Talena-funktioner.

- [ ] Fullständig genomgång av alla kandidat-/process-/AI-endpoints utanför
      `apps/processes/urls.py`, inklusive adminendpoints.
- [ ] Negativa tester för PDF-/rapportnedladdning, import- och export-API:er.
- [ ] Historiska kandidater, rapportbilagor och externa resurslänkar.
- [ ] Teamflöden och resultatförhandsvisning med både tillåtna och otillåtna
      användare och representativa uppgifter.
- [ ] Fullständig rättighetspolicy för användare med medlemskap i flera bolag
      (nuvarande `get_company_for_user` väljer en första medlemskapspost).
- [ ] Kör testfallen mot stage med syntetiska två-kundskonton före lansering.
- [ ] Dokumentera och fastställ Viewer/Editor/Own-semantik tillsammans med
      produktansvarig, särskilt vilka aktiviteter som räknas som ändring.
