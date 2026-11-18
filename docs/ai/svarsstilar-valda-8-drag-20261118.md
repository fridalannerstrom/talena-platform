# Svarsstilar utifrån åtta utvalda personlighetsdrag · 2026-11-18

## Omfattning

Den deterministiska texten **Situationsbaserad profil** / **Tydlig profil** i
**Personlighet → Svarsstilar** och **Inför intervju** bygger nu **endast på de
exakt åtta personlighetsdrag som valts för projektets rollkontext**. Båda
flikarna använder samma urvalsfunktion och samma statiska vägledning, även när
Inför intervju laddas om separat. Social önskvärdhet är en **separat
Sova-indikator**; den är oförändrad och kan fortfarande visas oberoende av
profilbedömningen.

### Beräkningsregel (STEN 1–10)

- **I mitten:** STEN **4–7**.
- **Tydligt:** STEN **1–3 eller 8–10**.
- **Situationsbaserad profil:** minst **4 av 8** utvalda drag i mitten.
- **Tydlig profil:** minst **5 av 8** utvalda drag tydliga.
- Med åtta giltiga resultat täcker dessa kriterier samtliga möjliga
  kombinationer. Exempelvis **4 mitten + 4 tydliga** → situationsbaserad;
  **3 mitten + 5 tydliga** → tydlig.

De **övriga tio** personlighetsdragen får aldrig förändra denna
klassificering. Vi skapar ingen profilbedömning om urvalet innehåller färre än
åtta *unika* godkända drag eller om poäng saknas för ett av de åtta. Vi
gissar inte poäng från AI-insikter eller social önskvärdhet.

## Projekturval

- Rollkontextens manuella val kan sparas först med **exakt åtta** unika
  godkända drag. Tomt val betyder uttryckligen *Talena väljer*, och
  Talena måste då rekommendera **exakt åtta** godkända unika drag.
- Defaultprompt och kodens modellinstruktioner är uppdaterade från 3–5 till 8.
  Cacheversionen höjs så gamla automatiska 3–5-urval inte fortsätter gälla.
  Om modellen inte levererar åtta giltiga drag sparas inget partiellt urval.
- Äldre projekt med manuellt sparade 3–7 drag **behålls** som historiska
  inställningar tills administratören ändrar dem. De ger **ingen**
  profilklassificering förrän urvalet uppdaterats till åtta. Att bara redigera
  rollkontexttexten ska inte krascha för dessa projekt.
- Äldre projekt med automatiskt 3–5-val kan generera ett nytt 8-val genom
  att öppna/spara rollkontexten när kontext finns.
- Projekt utan rollkontext eller utan giltiga åtta valda drag får en tydlig
  förklaring i både Svarsstilar och Inför intervju i stället för en
  missvisande klassificering.
- Ingen databas- eller Sova-migration krävs. Ändringar gäller endast
  feature-branchen tills den testats och godkänts.

## Testa

```bash
python manage.py test apps.reports.test_response_style_selected_eight_20261118 apps.processes.test_pre_interview_response_styles_504 apps.processes.test_response_styles_ui_366 --noinput
python manage.py check
```

Testerna täcker trösklarna, svenska/engelska etiketter, selektionens
isolering från de andra tio dragen, saknade poäng, social önskvärdhet,
projekturval med åtta, formulärvalidering och simulering av AI:s urval
utan riktiga OpenAI/Sova-anrop.
