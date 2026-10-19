# Talena: legacy AI-chatt avstängd inför lansering (#302)

**Status:** Implementerad på en separat branch, inväntar CI och granskning  
**Ärende:** [#302](https://github.com/fridalannerstrom/talena-platform/issues/302)

## Beslut

Det finns **ingen godkänd generell/personorienterad AI-chatt vid lansering**.
Äldre chattkomponenter får varken presenteras i UI eller skicka data till
OpenAI. Detta är en avsiktlig funktionsspärr, inte endast en frontendändring.

## Åtkomstvägar

| Funktion | UI | HTTP-endpoint |
|---|---|---|
| Kandidat-chatt i kundens kandidatvy | Borttagen | `/chat/api/stream/` returnerar 404 |
| Kandidat-chatt i adminvy | Borttagen | Samma endpoint returnerar 404 |
| Fristående AI-chatt | Chattvyn renderas inte | `/chat/` returnerar 404 |
| Allmän chatt (ej streaming) | Ingen tillgänglig inmatning | `/chat/api/` returnerar 404 |
| Fristående streaming-API även utan kandidat-ID | Ingen tillgänglig inmatning | `/chat/api/stream/` returnerar 404 |

Route-namnen behålls för bakåtkompatibilitet och för att gamla länkar ska
avvisas i backend. Alla handlers returnerar 404 innan de tolkar inkommande
data, laddar kandidatuppgifter eller skapar en OpenAI-klient.

Inga modell-, rapport-, assessment- eller kandidatresultat-endpoints har
ändrats. AI-sammanfattningar, tolkningar, AI-genererade intervjufrågor och
rapporter ska fortfarande fungera.

### Behålls i källkod för framtida referens

`apps/core/ai/chat.py` och
`apps/ai_chat/services/candidate_chat_context.py` ligger kvar som
icke-exponerad äldre kod. Ingen aktiverad HTTP-handler använder dem.
Tidigare implementation går också att återfinna i Git-historiken.

## Eventuell framtida systemhjälpschatt

En ny chatt måste utformas **endast för produkt- och systemhjälp**, exempelvis:

- Hur skickar jag en testinbjudan?
- Hur lägger jag till en kollega?
- Var hittar jag mina teamrapporter?

Följande får inte vara möjligt via hjälpchatten:

- Frågor om en kandidat, anställd eller annan identifierbar person.
- Inhämtning eller analys av Sova-testresultat, kompetenser, intervjuanteckningar
  eller andra personuppgifter.
- Att godtycklig fritext eller dokument hämtas från kandidat-, team- och
  processdatabaser och förs över till AI.

**Implementationskrav för eventuell återintroduktion:** ett separat
help-endpoint, restriktiv datakälla med godkända supportartiklar,
personuppgiftsminimering, teknisk åtkomstkontroll, kontroller av utgående
payload, svenska/engelska tester och GDPR-granskning. Använd inte den gamla
kandidat-chatthandlern som genväg.

## Testning och avgränsning

- [x] Kandidatens flytande chatt och adminvyns chattmarkup borttagen.
- [x] Javascript-initiering och kandidat-chattens eventhandlers borttagna.
- [x] Båda API-endpoints och chattsidan returnerar 404.
- [x] Regressionstester för direkt åtkomst, chatt-payloads och synligt UI.
- [x] Testerna inkluderade i Django QA.
- [ ] Django QA-resultat godkänt.
- [ ] Visuell kontroll i kundvy och adminvy.
- [ ] Bekräftat på deployad miljö innan lansering.

**Obs:** #298 och #300 hanterar sanering av personuppgifter vid andra AI-anrop.
Att chattfunktionen stängs av löser inte dessa separata dataskyddskrav.

**Sammanslagning med pågående PR #299:** den PR:n innehåller tidigare hjälprader
inne i chattfälten. Om #302 mergas först kan konflikt uppstå i samma
HTML-templates; behåll hjälprader för kvarvarande fritextfält och låt
chattfälten vara borttagna när konflikten löses.
