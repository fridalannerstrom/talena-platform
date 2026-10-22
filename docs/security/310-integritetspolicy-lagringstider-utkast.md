# Underlag till Talenas framtida integritetspolicy: lagring och gallring

**Status:** TEXTUTKAST, INTE EN PUBLICERAD ELLER JURIDISKT GODKÄND INTEGRITETSPOLICY  
**Datum:** 2026-10-22  
**Följer produktförslag:** [Lagrings- och gallringspolicy v0.2](./310-lagrings-och-gallringspolicy-forslag.md).

> OBS! Detta är **framtida planerat arbetssätt**, inte en beskrivning av vad Talena redan gör i produktion. Automatiska gallringsregler, separata åtkomstnivåer och kandidatprocessens avslutsdatum är ännu inte implementerade/aktiverade. Publicera inte texten förrän funktionerna är införda, ansvarsfördelning och faktisk lagring är verifierad, och ansvarig/jurist har godkänt texten.

## Förslag på lättläst text till kandidat- eller kundinformation

### Hur länge sparas personuppgifter i Talena?

> Talena är en plattform för tester och bedömningsunderlag i bland annat rekryteringar. Hur länge dina personuppgifter får behandlas beror på ändamålet med behandlingen, tillämpliga lagkrav och den personuppgiftsansvariga organisationens beslut. Den organisation som använder Talena ansvarar normalt för att bestämma ändamål och lagringstider för uppgifter som behandlas i den organisationens rekrytering.
>
> För vanliga privata rekryteringar föreslår Talena en standardmodell där uppgifter kan vara tillgängliga i det ordinarie rekryteringsarbetet i **högst 90 dagar efter att rekryteringen avslutats**, men bara så länge det fortfarande är nödvändigt. Därefter ska uppgifter som inte längre behövs tas bort eller avidentifieras. Om vissa uppgifter behöver bevaras för ett särskilt, dokumenterat och tillåtet ändamål, exempelvis för att hantera rättsliga anspråk, kan just dessa uppgifter bevaras med begränsad åtkomst. **Tolvmånadersperioden är Talenas föreslagna övre standardgräns för sådant prövat bevarande**, räknat från rekryteringens avslut. Det innebär **inte** att alla testresultat, intervjunoteringar eller AI-genererade rapporter automatiskt får sparas i tolv månader.
>
> Personuppgifter ska raderas eller avidentifieras tidigare om de inte längre behövs. I vissa situationer kan särskilda lagkrav eller dokumenterade rättsliga anspråk göra att vissa uppgifter måste eller får bevaras längre. Offentliga arbetsgivare kan exempelvis omfattas av arkivregler som kräver annan hantering. För andra ändamål än rekrytering, såsom medarbetarutveckling, gäller egna dokumenterade lagringsregler.
>
> En begäran om tillgång till eller radering av personuppgifter hanteras enligt dataskyddslagstiftningen och den personuppgiftsansvariga organisationens instruktioner. Att en rekrytering har avslutats eller ett projekt har arkiverats innebär inte att alla personuppgifter automatiskt raderas samma dag. Det innebär inte heller att en eventuell radering i Talena automatiskt verkställts i externa tjänster som Sova; de hanteras genom separata rutiner.

*Redaktionell anmärkning:* Använd **inte** ordalydelsen ovan förrän Talena faktiskt kan upprätthålla 90-dagarsbegränsningen och gallringsprocessen. För kandidattext kan en kortare version tas fram efter att kundavtal och ansvarsfördelning är fastställda.

## Kortare alternativ för kundavtal och DPA-bilaga (inte publiceringsklart)

> Talena erbjuder en konfigurerbar modell för ändamålsbaserad lagring. Som föreslagen standard för vanliga privata rekryteringar begränsas den ordinarie åtkomsten senast 90 dagar efter dokumenterat avslut. Därefter får endast personuppgifter med ett särskilt dokumenterat och tillåtet bevarandeändamål lagras med begränsad åtkomst. Talenas föreslagna övre standardgräns för sådan prövad lagring är 12 månader från avslut, med tidigare gallring när ändamålet upphör och separata undantag för lagkrav eller styrkta rättsliga anspråk. Den personuppgiftsansvarigas dokumenterade instruktioner och tillämplig rätt har företräde framför produktens förvalda alternativ.

## Kvar innan vi får använda texten externt

- [ ] Bekräfta vilka roller Talent Qode respektive kunden har för varje behandling: personuppgiftsansvarig, biträde och eventuellt underbiträde.
- [ ] Verifiera rättslig grund, lagringstid och faktisk behandlingsmodell per datakategori och kundtyp; bedöm speciellt personlighetstester och AI-genererade tolkningar.
- [ ] Slutför DPIA och anpassa DPA/biträdesavtal, integritetspolicy samt information direkt till kandidater.
- [ ] Inför faktisk `closed_at`-hantering på kandidat-/rekryteringsnivå. **Arkiverat projekt och färdigt test är inte samma sak som avslutad rekrytering.**
- [ ] Implementera separerad/behörighetsbegränsad lagring efter 90 dagar, säker radering/avidentifiering senast enligt beslutad deadline och kontrollerade undantag.
- [ ] Dokumentera Sova, OpenAI, Pinecone, e-post, Azure-blobbar och backuper inklusive vilka uppgifter som raderas respektive kan kräva senare radering.
- [ ] Separata regler för kommuner/offentlig sektor, intern utveckling, kandidatpool och räkenskapsinformation.
- [ ] Testa att data inte återkommer via backupåterställning, gamla resultatdelningslänkar eller korskund-kopplingar.
- [ ] Få dokumenterad juridisk/verksamhetsmässig sign-off och ange senast uppdaterad policyversion.

## Varför vi inte skriver "vi lagrar dina uppgifter i ett år"

En generell formulering vore missvisande: vissa uppgifter måste gallras betydligt tidigare, medan andra kan behöva sparas längre enligt rättsliga skyldigheter eller bevisning. Talena kan tekniskt *föreslå* en tolvmånadersgräns, men varje lagring måste vara nödvändig, proportionerlig och förenlig med kundens instruktion.

## Källor

- IMY, *Rekryteringssystem och kompetensdatabaser*: https://www.imy.se/verksamhet/dataskydd/dataskydd-pa-olika-omraden/arbetsliv/rekryteringssystem-och-kompetensdatabaser/
- IMY, *Grundläggande principer enligt GDPR* (lagringsminimering): https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/grundlaggande-principer/
- IMY, *Personuppgiftsansvariga och personuppgiftsbiträden*: https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/personuppgiftsansvariga-och-personuppgiftsbitraden/
