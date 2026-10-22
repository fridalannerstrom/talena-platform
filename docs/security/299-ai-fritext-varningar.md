# Talena: personuppgiftspåminnelser vid AI-anknutna fritextfält

**Ärende:** [#299](https://github.com/fridalannerstrom/talena-platform/issues/299)  
**Datum:** 2026-10-19  
**Status:** Implementerad i `main`, kod- och CI-verifierad; [#299 avslutad](https://github.com/fridalannerstrom/talena-platform/issues/299). Visuellt sluttest på mobil och i båda språken ingår fortfarande i lanseringskontrollen (#311).

## Syfte

När en användare skriver fritext som kan följa med till OpenAI ska användaren få en kort, synlig påminnelse direkt vid fältet. **Intervjuanteckningar ska uttryckligen be användaren undvika kandidatens namn.** Varningen fungerar på både svenska och engelska.

Varningar är **inte** pseudonymisering eller anonymisering. Backend-kontroller, dataminimering och fritt-textsanering byggs separat i [#298](https://github.com/fridalannerstrom/talena-platform/issues/298), [#300](https://github.com/fridalannerstrom/talena-platform/issues/300) och [#301](https://github.com/fridalannerstrom/talena-platform/issues/301).

## Förteckning över användarinmatning som omfattas

| Fält | Varför kan uppgiften nå AI? | Placering | Typ av varning |
|---|---|---|---|
| Generella intervjuanteckningar och exempel | Kan ingå i Efter intervju, chefsrapport och personlighetsrelaterade AI-texter | `templates/customer/processes/partials/candidate_insights/tabs/_final_output.html` | **Intervju** |
| Svar/anteckningar på enskilda intervjufrågor (personlighet, motivation, färdighet) | Sparade frågor och tillhörande svar används som AI-evidens | `static/js/talena/interview-question-notes.js` | **Intervju** |
| Redigera sparat frågesvar från sammanställningen | Samma fält och API-väg som övriga frågeanteckningar; fältet skapas dynamiskt | `static/js/talena/interview-question-notes.js` | **Intervju** |
| Process- eller rollkontext | Inkluderas i kandidattolkning, frågor och beslutsstöd | `templates/customer/processes/process_role_context.html` | Generell |
| Teamets korta beskrivning | Följer med i `prompt_context.team_description` för teaminsikter | `templates/customer/teams/team_form.html` | Generell |
| Teamets fritextkontext | Följer med i `prompt_context.team_context` för teaminsikter | `templates/customer/teams/team_form.html` | Generell |
| Allmän chattfråga till AI | Skickas till OpenAI och kan användas vid embeddings/RAG | `templates/customer/chat/chat.html` | Generell |
| Kandidatanknuten AI-chatt (kundvy) | Chattfrågor kan innehålla personuppgifter | `templates/customer/processes/_candidate_detail_sheet.html` | **Intervju** |
| Kandidatanknuten AI-chatt (adminvy) | Samma typ av risk som kundvyn | `templates/admin/accounts/companies/company_candidate_sheet.html` | **Intervju** |
| Admininstruktioner till AI | Administratören kan råka klistra in verkliga uppgifter i systemprompten | `templates/admin/core/ai_prompts/prompt_edit.html` | Generell |
| Processkontext för AI Prompt Playground | Fri testkontext skickas till AI vid prompttest | `templates/admin/core/ai_prompts/prompt_edit.html` | Generell |

Befintliga fält för kandidatens egna namn och kontaktuppgifter ingår **inte**. De behöver kunna sparas lokalt och användas för exempelvis Sova-kopplingen, men ska inte skickas till AI. Kandidatens egna feedback-/reflektionsfält i kandidatportalen har inte identifierats som direkta AI-promptfält i denna genomgång, och får inte automatiskt likställas med intervjuanteckningar.

## Exakt text

**Intervju (svenska):**  
> Obs: Skriv inte kandidatens namn eller andra personuppgifter i detta fält.

**Interview (English):**  
> Note: Do not enter the candidate's name or other personal data in this field.

**Allmän fritext (svenska):**  
> Obs: Ange inte namn, kontaktuppgifter eller andra personuppgifter i detta fält.

**General free text (English):**  
> Note: Do not enter names, contact details or other personal data in this field.

## Implementation

- Gemensam Django-partial: `templates/shared/ai_pii_notice.html`, med `kind=interview|general`. Svensk/engelsk text baseras på aktiv Django-språkinställning.
- Dynamiska intervjufält använder samma budskap i befintlig JS-språkhantering. Där skapas påminnelsen tillsammans med varje `textarea`, även när en sparad anteckning redigeras.
- Helfälts- och frågenotiser har `aria-describedby` för tillgänglighet där de dynamiskt eller direkt kopplas till motsvarande fält.
- Inga migrationsändringar, databasändringar, spar-endpoints eller AI-promptar ändras av denna ticket.

## Kontroller och kvarvarande arbete

- [x] Kända, direkt AI-anknutna fritextfält kartlagda.
- [x] Anvisningar vid både generella intervjuanteckningar och frågesvar.
- [x] Samma hjälpinformation vid redigering av sparade frågesvar.
- [x] Process- och teamkontext samt allmän chatt/promptverktyg inkluderade.
- [x] Svenska och engelska texter.
- [x] Automatiska Django-tester tillagda (templaterendering och omfattningskontroller).
- [x] GitHub Actions-tester godkända (Django QA / privata fritextnotiser).
- [ ] Snabb UI-kontroll i både svenska och engelska i riktig browser.
- [x] Kodgranskad och mergad i `main`.

**Viktigt:** Den kandidatanknutna AI-chatten och dess backend är nu **avstängda** enligt avslutade [#302](https://github.com/fridalannerstrom/talena-platform/issues/302). De äldre chattraderna ovan dokumenterar den ursprungliga fältinventeringen, inte aktiva inmatningsfält. Nya AI-anknutna fritextfält måste fortfarande följa samma mönster.
