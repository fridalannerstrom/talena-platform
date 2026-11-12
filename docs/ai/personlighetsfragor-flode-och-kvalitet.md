# Talena | Så fungerar AI-genererade personlighetsfrågor

**Teknisk och verksamhetsinriktad dokumentation**  
**Datum:** 5 november 2026  
**Branch:** feature/personality-question-context-quality-20261105

Det här dokumentet beskriver vad Talena skickar till OpenAI, hur personlighetsresultat och processkontext kombineras, vad den nya kvalitetsgranskningen gör och vilka delar som styrs av kod respektive adminpromptar. **Kvalitetsgranskningen är stödjande, inte blockerande:** om en redan tekniskt giltig uppsättning frågor inte kan kvalitetsförbättras ska användaren fortfarande få sina frågor.

> **Avgränsning:** Adminprompten och globalprompten är oförändrade i detta arbete. Deras aktuella innehåll hämtas fortfarande dynamiskt från Talenas admin. Dokumentet beskriver den tekniska sammansättningen, inte ett löfte om att adminpromptens text är statisk.

## 1. Vad personlighetsfrågorna ska åstadkomma

Talena ska ge intervjuaren öppna, beteendeinriktade frågor som undersöker hur en person fungerar i konkreta situationer. Personlighetsresultaten används för att välja **vilket beteende som är relevant att utforska**. Processkontexten används för att välja **vilken faktisk arbetsuppgift eller situation** som gör beteendet relevant.

Resultatet ska inte vara en bedömning av personens lämplighet. En testindikation är en hypotes om beteendepreferenser, inte ett bevis för vad en person kan eller inte kan göra.

Exempel: I CPF:s UX-roll blir användartester, analys av användartestresultat och koordinering av utvecklingsarbete relevanta. I Verisures rekryteringsroll blir kandidatdialog, parallella rekryteringsprocesser och samarbete med säljchefer relevanta. En fråga om att bara ”samarbeta i ett projekt” är för allmän när mer konkret processkontext finns.

## 2. Översikt över flödet

~~~text
Kandidatens färdiga tester och process
                |
                v
Valda personlighetsdrag + översatt Result Summary
                |
                v
Rätt processkontext + aktuella adminpromptar
                |
                v
OpenAI genererar åtta frågor
                |
                v
Befintlig teknisk kontroll och normalisering
                |
                v
NYTT: valfri kvalitetsgranskning av rollkoppling per fråga
          /                            \
     Godkänd                       Kan förbättras
          |                            |
          |                 Omarbeta underkända (högst två rundor)
          |                            |
          |                     Granska igen om möjligt
          |                            |
          +----------------------------+
                       |
                       v
    Spara de bästa tillgängliga tekniskt giltiga frågorna
    (ursprungliga vid fel i granskning eller omarbetning)
                       |
                       v
               Visa frågorna i UI
~~~

## 3. Vilka uppgifter hämtas från Talena?

| Källa | Kod | Vad skickas/används? |
| --- | --- | --- |
| Processens syfte | apps/core/ai/shared_context.py | Aktivt processyfte, till exempel rekrytering |
| Processkontext | get_process_context(process) | Full sparad kontexttext för **aktivt** syfte |
| Testresultat | personality_results | Tillgängliga drag och underliggande bedömningsunderlag |
| Översatt personlighetsunderlag | personality_question_definition_grounding_policy.py | Kandidatspecifika Result Summary-texter från samma tolkningsunderlag som resultatvyn |
| Användarens val av fokus | selected_personality_traits | Valda drag eller instruktion för AI-urval |
| Adminvägledning | prompt_templates.py | Aktuell global AI-vägledning och aktuell funktionsprompt för personlighetsfrågor |
| Urvalsvägledning | personality_trait_selection | Särskild prompt för urval om användaren inte valt drag själv |
| Språk | language.py / anropet | Svenska eller engelska beroende på inställning |

### Rätt version av processkontexten

Processkontext hämtas genom get_process_context() och därefter get_context_for_purpose() för det aktuella processyftet. Om separata kontexter finns för flera syften ska Talena inte av misstag plocka text från ett annat syfte. Historiska profiler kan sakna originalkontext.

Det är den **sparade texten** som skickas vidare, inte en automatisk sammanfattning av en webbsida. Därför blir frågornas kvalitet beroende av vilken rolltext som faktiskt sparats.

## 4. Första OpenAI-anropet: generera frågorna

Teknisk ingång: apps/core/ai/personality_questions.py, funktionen stream_personality_questions(), som bygger prompt via build_personality_questions_prompt().

**Anropstyp:** chat.completions.create via Talenas integritetskontrollerade OpenAI-klient.  
**Modell:** den som get_chat_model() hämtar från Talenas konfiguration.  
**Temperatur:** 0.2.  
**Streaming:** ja.

### Den sammansatta promptens delar

Den slutliga genereringsprompten består logiskt av:

1. Talena-data med pseudonymiserad kandidatreferens (CANDIDATE_A).
2. Valet av processyfte och den fulla sparade processkontexten.
3. Personlighetsunderlaget, tillgängliga tekniska dragnamn och valda drag.
4. Eventuell separat adminvägledning för AI-urval av drag.
5. **Global adminprompt + funktionsspecifik adminprompt för personlighetsfrågor**, hämtade från den aktiva databaskonfigurationen.
6. Tekniska krav för valda drag, språk, NDJSON-format och utdatafält.
7. Slutlig personlighetsevidens från kandidatens **översatta Result Summary**, samt processkontexten igen och Talenas evidensregler.

Den sista delen tillkommer genom runtime-policyn personality_question_definition_grounding_policy.py, som för vanliga personlighetsdrag tar bort äldre råpoängs-/skalriktningslager ur prompten och gör den färdigöversatta personlighetsbeskrivningen till primär källa. Därför ska man studera den **slutliga, sammansatta prompten** om man granskar exakt vad OpenAI fick, inte bara grundmallen.

### Förväntad teknisk output

Modellen svarar med NDJSON-händelser av typerna meta, suggested_traits, selected_traits, questions, context_note och done. En fråga har exakt följande fyra fält:

~~~json
{
  "question": "Öppen, konkret intervjufråga",
  "traits": ["Samverkande"],
  "why": "Neutral förklaring av varför beteendet ska utforskas i denna roll",
  "listen_for": "Handlingar, exempel och strategier att uppmärksamma"
}
~~~

- **question:** det intervjuaren ska fråga personen.
- **traits:** exakt vald teknisk karaktärsdragsetikett, utan översättningsfel i metadata.
- **why:** texten under ”Varför detta är viktigt”.
- **listen_for:** texten under ”Vad du ska lyssna efter”.

Talena kräver **8 personlighetsfrågor** genom interview_config.py och question_count_policy.py. Tidigare tekniska skydd hanterar även felaktigt antal och felaktig JSON-struktur, men garanterade inte konkret rollförankring per fråga.

## 5. Nytt AI-anrop: kvalitetsgranskning av varje fråga

Ny kodfil: apps/core/ai/personality_question_context_quality_policy.py.

När vanlig personlighetsfrågegenerering är klar och det finns meningsfull processkontext gör Talena ett separat granskningsanrop. Det skickar:

~~~json
{
  "selected_traits": ["Cooperative"],
  "personality_result_summaries": "Kandidatspecifika, översatta tolkningstexter",
  "process_context": "Full roll-/processkontext för rätt syfte",
  "questions": [
    {
      "question": "En redan genererad fråga",
      "traits": ["Cooperative"],
      "why": "Varför viktig",
      "listen_for": "Vad lyssna efter"
    }
  ]
}
~~~

**Anrop:** chat.completions.create via samma säkra klient.  
**Temperatur:** 0.  
**Svar:** JSON-objekt (inte streaming).

Granskaren ska bedöma var och en av frågorna:

1. Utforskar frågan det angivna personlighetsdraget och en kandidatförankrad beteendehypotes?
2. Innehåller **själva frågetexten** en konkret uppgift, situation eller ansvar för den aktuella rollen?
3. Finns denna arbetsuppgift på riktigt i processkontexten?
4. Är frågan neutral, går den att ställa i intervju och har den konsekvent motivering/lyssnarguide?
5. Skulle frågan vara lika generisk även om processkontexten byttes? I så fall ska den underkännas.

Modellen svarar för varje fråga med index, godkänd/underkänd, dragetikett och ett **ordagrant citat från processkontexten** som stöder rollkopplingen. Koden verifierar att citatet återfinns i **den maskerade version av processkontexten som modellen fick**, att frågan har minst ett korrekt valt personlighetsdrag och att fråga/motivering/lyssnarguide inte är tomma. Citatkontrollen accepterar källans skiljetecken och radbrytningar samt korta distinkta svenska sammansättningar som ”användartester”. Granskarens extra dragetikett får inte underkänna en fråga där Talenas egen tekniska etikett redan är korrekt.

**Viktig begränsning:** citerad text bevisar att en källpassage finns. Den semantiska bedömningen av om frågan verkligen motsvarar passagen görs av en språkmodell och är därför inte en absolut garanti. Om granskaren underkänner alla frågor även efter omarbetning innebär det inte att användaren får en röd felruta: Talena fortsätter med de bästa tekniskt giltiga frågorna.

## 6. Nytt AI-anrop vid behov: reparera bara svaga frågor

Om granskningen underkänner en eller flera frågor gör Talena ett reparationsanrop med:

- Nuvarande språk och valda drag.
- Kandidatens Result Summary.
- **Fullständig sparad processkontext.**
- Alla ursprungliga frågor.
- Indexen för just de underkända frågorna.
- **Aktuell global och funktionsspecifik adminvägledning** från Talenas admin, utan att ändra dem.

Modellen returnerar ett JSON-objekt med replacements, ett objekt per underkänt frågeindex, med samma fyra frågefält. Talena ersätter endast dessa objekt. Övriga, redan godkända frågor behålls exakt.

Därefter görs om möjligt **en ny kvalitetsgranskning på hela frågeuppsättningen**. Om något fortfarande underkänns får endast återstående underkända frågor **en andra riktad omarbetning** och efterföljande omgranskning. Om AI-granskaren fortfarande inte är nöjd eller om ett gransknings-/reparationsanrop misslyckas används de **bästa redan tekniskt giltiga frågorna** utan att användaren får ett blockerande fel. En strukturellt giltig ersättning kan behållas även om granskarens omdöme är osäkert. Om reparationssvaret däremot är trasigt behålls de ursprungliga/vidareförda frågorna. Det finns ingen kvalitetsgaranti efter denna reservväg. Loggarna innehåller endast skede, feltyp och antal, inte kandidat- eller processkontext.

### Vad kostar det?

När granskningen är aktiv tillkommer normalt **ett extra OpenAI-anrop** för godkända frågor. Om någon fråga underkänns kan **ett reparationsanrop och en andra granskning** tillkomma. I svårare fall kan detta upprepas ytterligare en gång (totalt högst två reparationsrundor), men vid fel faller Talena tillbaka till de redan genererade frågorna. Befintliga reparationsanrop för antal/format kan också förekomma. Därmed ökar tokenkostnad och genereringstid. Faktiska tider och kostnader behöver mätas i dev/stage.

## 7. Vad händer om processkontexten ändras?

Talena sparar nu ett internt fält, context_fingerprint, i JSON-resultatet för personlighetens intervjufrågor. Det är SHA-256 av **processyfte + sparad processkontexttext**. Fältet är inte en ny AI-utdataegenskap och innehåller inte råtext.

När Talena hämtar sparade frågor jämförs fingeravtrycket med aktuell processkontext:

- Om syfte och text är oförändrade kvarstår tidigare status.
- Om kontexten eller syftet ändrats markeras tidigare genererade frågor som **outdated**.
- Äldre frågor utan fingeravtryck markeras inaktuella när en aktiv kontext finns.
- Tidigare godkända frågor raderas inte automatiskt.

**Notera:** Talenas befintliga cache kan visa en sparad fråga även när status är outdated. Detta betyder att frågan bör **regenereras**, inte att Talena automatiskt gör ett nytt AI-anrop så snart kontexten ändras.

Kod: personality_questions.save_personality_questions() samt processes/personality_question_selection_policy.py.

## 8. Vad skickas inte och hur skyddas uppgifter?

- Kandidatreferensen i genereringsprompten är **CANDIDATE_A**, inte kandidatens namn.
- OpenAI-anropen går via apps/core/ai/openai_client.py, som utför Talenas privacy-screening/maskning för utgående fält.
- Den nya granskningsmodulen sparar inte granskningscitat eller AI:ns interna bedömningslista i kandidatens resultat.
- Loggarna för kvalitetssteget innehåller antalet underkända frågor och feltyper, inte hela frågetexter eller kontexten.
- Den nya granskningen bygger på översatta Result Summary-texter, inte på ett separat nytt utskick av råa STEN-poäng.

**Fritext är en integritetsrisk:** processkontexten kan innehålla det användaren själv sparat. Det är fortsatt viktigt att undvika personuppgifter och ovidkommande information i processkontext och intervjunoter.

## 9. När körs den extra granskningen inte?

Skyddet gäller i denna version **vanliga personlighetsdrag** med en sparad, meningsfull processkontext (minst 20 tecken och fem ord).

- Saknas kontext eller finns bara en extremt kort etikett bevaras det tidigare flödet utan den extra kontrollen.
- Kompetensbaserat läge, där fokusnyckeln börjar med competency::, använder en separat evidensväg och omfattas ännu inte av den nya granskningen.

Det är viktigt att vara transparent med denna avgränsning. Vi kan inte kräva citat från en processkontext som faktiskt saknas.

### Exempel: kort processkontext för projektkoordinator

När processkontexten bara säger att rollen ska planera och koordinera leveranser, skapa struktur i komplexa projekt, kommunicera med intressenter och hantera ändrade prioriteringar, får Talena använda samma *faktiskt nämnda arbetsuppgift* i flera olika frågor med skilda personlighetsvinklar. Det vore fel att hitta på en bransch, ett specifikt verktyg eller kundtyp för att skapa artificiell variation. Frågorna ska bli så konkreta underlaget medger och aldrig stoppas bara för att åtta helt olika arbetsuppgifter saknas.

## 10. Tester, verifiering och förväntat resultat

Nytt testpaket: apps/core/test_personality_question_context_quality_policy.py.

Automatiska testfall kontrollerar bland annat att:

1. Bra Verisure-liknande rekryteringsfrågor kan passera utan ändring.
2. Generiska CPF/UX-frågor kan underkännas och ersättas **utan att redan bra frågor ändras**.
3. Ett påhittat kontextcitat inte räcker för godkännande.
4. Avsaknad av giltig personlighetsetikett inte godkänns.
5. Underkännande även efter två reparationsrundor **inte blockerar visning av frågorna**.
6. Saknad processkontext inte startar granskningsanrop.
7. Oavsiktliga ändringar av andra frågor blockeras.
8. Cachefingeravtrycket ändras när syfte eller text ändras.
9. Granskningsanrop eller reparationsanrop som misslyckas bevarar frågorna.
10. Kort svensk processkontext, exempelvis intern projektkoordinator, går att använda utan blockerande fel.

Kör lokalt:

~~~bash
python manage.py test apps.core.test_personality_question_context_quality_policy
~~~

**Manuell testplan på dev/stage:** Generera frågor för CPF/UX och Verisure/rekryteringsspecialist. Kontrollera att var och en av de åtta frågorna hänvisar till en faktisk arbetsuppgift och utforskar ett relevant personlighetsdrag. Testa även att ändra processkontext och kontrollera outdated-status, att omgenerering fungerar, att UI-texterna förblir naturliga och att kostnad/latens är acceptabla.

## 11. Ansvarsfördelning och begränsningar

| Område | Ansvar |
| --- | --- |
| Hämta rätt assessment-underlag och rätt processkontext | Django |
| Sammanfoga tekniska instruktioner och versionshantera genererat resultat | Django |
| Granska och försök förbättra rollkopplingar; behåll tekniskt giltiga frågor vid osäker granskning | Ny kodpolicy + OpenAI |
| Språk, intervjumetod och formuleringar | Adminprompt och globalprompt, ansvar hos promptägaren |
| Slutlig bedömning av frågans relevans i en rekrytering | Intervjuaren/Talena-teamet |

Det nya steget är en **kvalitetskontroll för genererat intervjumaterial**, inte en psykometrisk validering och inte en automatisk bedömning av kandidatens lämplighet.

## 12. Förbättrad UX- och rollförankring (5 november, nästa branch)

Vi upptäckte i produktion att de tidigare genererade UX-frågorna fortfarande kunde vara generella. Talena tog hänsyn till Result Summary men själva frågorna nämnde ofta bara ”projekt”, ”grupp” eller ”problem”, trots detaljerad processkontext om UX-design och användartester.

Den kompletterande implementationen förbättrar detta i **koden**, inte i adminprompten eller globalprompten:

1. `personality_question_role_anchors.py` identifierar upp till åtta **befintliga, ordagrant hämtade arbetsuppgifter** ur den sparade processkontexten. Den söker efter konkreta arbetsverb och delar upp uppräknade aktiviteter. Den hittar inte på nya krav. Exempel från CPF: användarcentrerad design, användarflöden, användartester samt analys och presentation av testresultat.
2. För den **första genereringen** läggs en separat lista `ROLE TASK ANCHORS` till i Talenas egen tekniska evidensdel. Modellen uppmanas att i varje frågetext använda en konkret rolluppgift och undvika oprecisa projektfrågor. Admin- och globalprompten förblir oförändrade.
3. Den efterföljande kvalitetsgranskningen får också se dessa befintliga arbetsuppgifter och granskar variationen **mellan hela frågeuppsättningen**, inte bara rollkopplingen i varje fråga.
4. Talena gör dessutom en försiktig, lokal jämförelse av frågetexterna. Om två frågor nästan är samma fråga (även när den andra har ett litet extra tillägg) markeras den senare för omarbetning.
5. Om AI-granskningen inte går att använda kan den lokala upprepningskontrollen fortfarande initiera en riktad förbättring. Om även denna misslyckas, behålls de bästa tekniskt giltiga frågorna. **Ingen blockerande röd ruta** ska komma enbart från det extra kvalitetsskyddet.

**Begränsning:** Att arbetsuppgifter har extraherats ur kontexten är ingen garanti för att modellen använder dem korrekt. Därför måste vi fortfarande bedöma faktiska frågor i dev/stage för CPF och rekryteringsspecialisten. Korta rollbeskrivningar kan ge färre än åtta ankaruppgifter; då är det tillåtet att använda samma verkliga uppgift i flera frågor, men beteendeperspektiven ska skilja sig. Nya tester kontrollerar både rollankarna och upprepningar.

### Felsökning utan känsliga data

Den extra kontrollens loggar anger antal identifierade arbetsuppgifter, antal frågor, antal upptäckta upprepningar och hur många frågor som behöver förbättras. Loggarna ska inte innehålla kandidatnamn, testresultat, personuppgifter eller hela processkontexten. Om utdata fortfarande är generiska kan vi nu skilja på två problem: att inga användbara arbetsuppgifter upptäcktes, eller att AI:n fick uppgifterna men inte använde dem.

## 13. Kodreferenser

- apps/core/ai/shared_context.py
- apps/core/ai/personality_questions.py
- apps/core/ai/personality_ai_evidence.py
- apps/core/ai/personality_question_definition_grounding_policy.py
- apps/core/ai/prompt_templates.py
- apps/core/ai/question_count_policy.py
- apps/core/ai/personality_question_label_policy.py
- apps/core/ai/openai_client.py
- **NY:** apps/core/ai/personality_question_context_quality_policy.py
- apps/processes/personality_question_selection_policy.py
- **NY:** apps/core/test_personality_question_context_quality_policy.py

**Dokumentets status:** beskriver implementerad kod på arbetsbranch. Verifiering med live-anrop i dev/stage behöver göras före merge.

- **NY på aktuell branch:** apps/core/ai/personality_question_role_anchors.py (ordagranna rolluppgifter till generering och granskning)
