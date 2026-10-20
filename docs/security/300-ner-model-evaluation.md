# NER-modeller för Talena: teknisk utvärdering (#300)

**Status:** Endast *utvärdering*, inga lokala NER-modeller aktiveras i Talenas produktion av denna PR.

## Kandidater till första CPU-testet

| Språk | Modell | Version att prova | Modellspecifik etikett | Licens | Rekommendation |
|---|---|---|---|---|---|
| Svenska | spaCy sv_core_news_sm | 3.8.0 | PRS | CC BY-SA 4.0 | Utvärdera i syntetisk CI först; juridisk licensgranskning innan kommersiell distribution/drift |
| Engelska | spaCy en_core_web_sm | 3.8.0 | PERSON | MIT | Utvärdera i syntetisk CI först |

Modellerna är valda som **lätta, CPU-orienterade startpunkter**; de är inte automatiskt de bästa på rekryteringsanteckningar. Officiella spaCy-kompatibilitetslistan anger båda modellerna som kompatibla med spaCy 3.8, och benchmark-körningen använder spaCy 3.8.11 med exakt modellversion.

Källor: https://spacy.io/models/sv , https://spacy.io/models/en , https://github.com/explosion/spacy-models/blob/master/compatibility.json , https://huggingface.co/spacy/sv_core_news_sm , https://huggingface.co/spacy/en_core_web_sm .

### Licens och användning

Den engelska modellen är MIT-licensierad. Den svenska är märkt **CC BY-SA 4.0** och kan ha krav kring erkännande och eventuell delning av bearbetat modellmaterial. Detta är **inte ett juridiskt klartecken**. Be Talent Qodes ansvariga granska om och hur modellen får byggas in i er kommersiella Azure-tjänst och vad som behöver anges i licens-/tredjepartsförteckningen. En källkodsreferens ensam ersätter inte licenskrav. Överväg en annan svensk NER-modell om villkoren inte passar.

## Identifierad kompatibilitetsbugg

Tidigare stöddes personetiketterna \`PERSON\` och \`PER\`, men spaCys svenska modeller använder **\`PRS\`**. Nu maskeras även \`PRS\`. Vid konfiguration av en lokal modell som saknar \`ner\`-komponent eller saknar personetikett **avbryts alla berörda OpenAI-anrop** istället för att sanering kringgås tyst.

## Vad benchmarken faktiskt mäter

Filen \`scripts/benchmark_ner.py\` använder enbart påhittad svensk/engelsk fritext och testar:

- Tio personnamn per språk (blandade ensamma förnamn och hela namn).
- Modellens egna identifieringar, separat från det tidigare regexbaserade skyddet.
- Sammanlagt maskerade namn med regex och NER aktiverat.
- Om åtta korta exempel på psykometriska uttryck och JSON-format lämnas oförändrade.
- Medianlatens vid sanering på dessa syntetiska meningar.

Workflow: \`.github/workflows/ner-model-evaluation.yml\`. Båda modellernas hjul installeras **enbart i en tillfällig CI-runner** och använder ingen extern inference-tjänst. Modellerna checkas inte in i GitHub och laddas inte automatiskt på Talenas servrar. CI-resultatet skrivs som summerad statistik utan att logga individuell inputtext.

Därutöver finns \`apps/core/test_ai_local_ner_contract.py\` med deterministiska, modellfria tester för personetiketter och *fail-closed* beteende i ordinarie Django QA.

## Första verkliga modellkörningen (GitHub Actions, 2026-10-20)

Jobb: https://github.com/fridalannerstrom/talena-platform/actions/runs/39431301460

Båda *riktiga* modellerna installerades på en tillfällig CI-runner och användes på enbart påhittade exempel. Resultat efter fix för modellernas falska träffar på SOVA-/Talena-terminologi:

| Mätpunkt | Svenska | Engelska |
|---|---:|---:|
| Syntetiska namn | 10 | 10 |
| NER-fångade namn | 10 | 9 |
| Endast regex (jämförelse) | 4 | 4 |
| Sammanlagt maskerade namn (regler + NER) | 10 | 9 |
| Avsiktligt oförändrad kontext med modellen | 4/4 | 4/4 |
| Samma kontext när både sv+en körs samtidigt | 4/4 | 4/4 |
| Medianlatens för kort text med en modell | 5,2 ms | 5,5 ms |

Vi hittade och åtgärdade faktiska falska träffar: modellen misstolkade **Social Desirability**, **Qode** och den tekniska rubriken **Resultat** som personer. Kodskyddet undantar nu områden i känd psykometrisk terminologi, varumärken, rubriker och JSON-fältnamn från NER-masking. Dessa skydd är avvägningar som också kan skapa falska negativa för ovanliga personnamn.

**Tolkning:** Mycket liten, specialkonstruerad testmängd. 10/10 eller 9/10 är *inte* generaliserbar recall och 4/4 är *inte* bevis på att modellerna aldrig skadar rapportunderlag. Mät verklig minnesåtgång, kontextändringar, modell-precision/recall och latenstid på representativt men syntetiskt, längre Talena-material före produktion. Engelskan missade minst ett personnamn redan i denna begränsade körning.

## Kriterier före produktionsaktivering

1. **Kör benchmark och läs faktiskt utfall.** Resultaten på uppdiktade meningar är bara en första indikator, inte ett precision/recall-bevis i produktion.
2. Kontrollera risken för falskt positiva i faktiska Talena-prompter: personlighet, motivation, färdighet, teams och Efter intervju. Testa särskilt STEN/STIVE, kompetensnamn, roll- och arbetsmiljöbegrepp, JSON-struktur, svenska namn i olika böjningar och endast förnamn.
3. Kvalitetsgranska svåra edge cases som telefonnummer, namn med bindestreck, organisationsnamn, befattningsnamn, indirekta identifierare och personer som inte är kandidaten.
4. Kör prestanda-/minnestest med realistiska (syntetiska) långa sammanställningar. Kontrollera Azure App Service-planens RAM, uppstartstid och responstid, särskilt när båda modellerna laddas.
5. Besluta och dokumentera licensuppfyllnad och modellförvaltning (version, säkerhetsuppdateringar, tredjepartskomponenter, återställningsplan).
6. Versionslås spaCy och modellpaketen i en **separat release-/deployplan**. Installera modellen på servern innan \`TALENA_PII_NER_SV_MODEL\` och \`TALENA_PII_NER_EN_MODEL\` sätts till \`sv_core_news_sm\` respektive \`en_core_web_sm\`.
7. Verifiera med regressionstest och dev/stage E2E att promptar verkligen maskeras och att framtida OpenAI-anrop inte kan gå runt den centrala klienten.

**Beslut:** #300 hålls öppen tills produktionsinstallation, juridik, modelltest och dataminimeringsgranskning är klara. Varken regex eller NER gör testresultat och intervjunoteringar juridiskt anonyma.
