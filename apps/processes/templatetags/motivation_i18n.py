# Bilingual display helpers for Talena Motivation Results.

from __future__ import annotations

from django import template
from django.utils.translation import get_language


register = template.Library()


DOMAIN_CONTENT = {
    "belonging": {
        "title": "Samhörighet",
        "subtitle": "Social kontakt, stöd och en känsla av tillhörighet i arbetet",
    },
    "influence": {
        "title": "Inflytande",
        "subtitle": "Självständighet, erkännande och möjligheter att påverka resultat",
    },
    "growth": {
        "title": "Utveckling",
        "subtitle": "Prestation, kvalitet, lärande och meningsfulla standarder",
    },
    "interest": {
        "title": "Intresse",
        "subtitle": "Utforskande, kreativitet, arbetsglädje, variation och risktagande",
    },
}


FACTOR_CONTENT = {
    "attachment": {
        "name": "Samhörighet",
        "description": "Social kontakt, stöd och att arbeta som en del av ett team.",
        "top_text": (
            "Värdesätter social interaktion med andra på jobbet, detta är en primär drivkraft för dem. "
            "Trivs med känslan av att tillhöra ett team och drivs av att utveckla starka band och goda arbetsrelationer."
        ),
        "bottom_text": (
            "Social interaktion och känslan av tillhörighet verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte stark teamtillhörighet eller täta sociala band för att känna engagemang i arbetet. "
            "Det betyder inte att goda arbetsrelationer är oviktiga."
        ),
    },
    "customer_service": {
        "name": "Kundservice",
        "description": "Att förstå kunders behov och ge hjälpsam service.",
        "top_text": (
            "Trivs i en kundorienterad roll där de får hjälpa och stödja andra. Lägger värde på att bygga relationer med kunder "
            "och förstå kundernas behov. Lägger stor vikt vid att möta och överträffa kunders behov och förväntningar."
        ),
        "bottom_text": (
            "Att hjälpa, stödja och bygga relationer med kunder verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte en tydligt kundorienterad roll för att känna engagemang. "
            "Det betyder inte att personen har svårt att ge god service när arbetet kräver det."
        ),
    },
    "work_life_balance": {
        "name": "Balans mellan arbete och fritid",
        "description": "Att upprätthålla en hållbar balans mellan arbete och livet utanför arbetet.",
        "top_text": (
            "Balans mellan arbete och privatliv är viktigt, så att de kan uppfylla sina åtaganden både i arbetet och utanför. "
            "Söker tydliga gränser så att de kan stänga av när arbetsdagen är slut och ägna tid åt andra aktiviteter som är viktiga."
        ),
        "bottom_text": (
            "Tydliga gränser mellan arbete och privatliv verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte en lika tydlig separation mellan arbete och fritid för att känna engagemang. "
            "Det säger inte något om personens förmåga att skapa en hållbar balans."
        ),
    },
    "people_development": {
        "name": "Utveckla andra",
        "description": "Att hjälpa andra människor att lära, växa och utvecklas.",
        "top_text": (
            "Hjälpa och stödja andra och aktivt bidra till deras utveckling. Trivs med att vägleda andra genom svåra tider "
            "och hjälper andra att övervinna motgångar eller utmaningar. Erbjuder proaktivt stöd så att andra kan växa."
        ),
        "bottom_text": (
            "Att utveckla och vägleda andra verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte ansvar för andras utveckling för att känna engagemang. "
            "Det betyder inte att personen är ovillig att hjälpa eller stödja kollegor när det behövs."
        ),
    },
    "stability": {
        "name": "Stabilitet",
        "description": "Förutsägbarhet, kontinuitet och trygghet i arbetsmiljön.",
        "top_text": (
            "Känner trygghet på jobbet och föredrar troligen att arbeta i en bransch eller organisation som de ser som stabil. "
            "Lägger vikt vid att känna att deras position på jobbet är säker och är sannolikt mer angelägen om att ha stabilitet i sin roll."
        ),
        "bottom_text": (
            "Trygghet, förutsägbarhet och stabilitet verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte en hög grad av kontinuitet eller säkerhet i rollen för att känna engagemang. "
            "Det betyder inte att personen föredrar osäkerhet."
        ),
    },
    "authority": {
        "name": "Auktoritet",
        "description": "Status, senioritet och möjligheten att påverka eller leda andra.",
        "top_text": (
            "Värdesätter möjligheten att ta på sig ledande befattningar och möjlighet till befordran. "
            "Uppskattar roller där det ges utrymme att ange riktningen, organisera andra och säkerställa att arbetet utförs som det ska."
        ),
        "bottom_text": (
            "Formell auktoritet, status och ledande ansvar verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte en chefsroll eller tydlig position av inflytande för att känna engagemang. "
            "Det säger inte något om personens förmåga att leda när situationen kräver det."
        ),
    },
    "acquisition": {
        "name": "Ekonomisk belöning",
        "description": "Ekonomisk belöning, resurser och materiella fördelar.",
        "top_text": (
            "Motiveras av ekonomisk belöning och av att arbeta i en välbetald roll så att de har råd med de saker de vill ha utan att behöva oroa sig för kostnader. "
            "Fokus på lön och förmåner är starkt, och attraktiv ersättning är motiverande."
        ),
        "bottom_text": (
            "Lön, förmåner och materiell belöning verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte en särskilt stark ekonomisk uppsida för att känna engagemang i arbetet. "
            "Det betyder inte att rättvis eller konkurrenskraftig ersättning är oviktig."
        ),
    },
    "independence": {
        "name": "Självständighet",
        "description": "Frihet att fatta beslut och påverka hur arbetet genomförs.",
        "top_text": (
            "Friheten att fatta egna beslut om hur de ska planera tid och organisera sitt arbete är viktig. "
            "Presterar som bäst när de får förtroende för att sätta sin egen arbetsriktning och slutföra sitt arbete på det sätt de tycker är lämpligt."
        ),
        "bottom_text": (
            "Hög grad av självständighet och frihet att styra arbetssättet verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte full autonomi för att känna engagemang. "
            "Det betyder inte att personen föredrar detaljstyrning eller saknar förmåga att arbeta självständigt."
        ),
    },
    "recognition": {
        "name": "Erkännande",
        "description": "Synlighet, beröm och uppskattning för den egna insatsen.",
        "top_text": (
            "Motiveras av erkännande, beröm och uppskattning. Prioriterar aktiviteter eller projekt som är synliga i organisationen "
            "så att andra kan se arbetet de gör och värdet de tillför. Positiv feedback och beröm är motiverande för dem."
        ),
        "bottom_text": (
            "Erkännande, beröm och synlighet verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte frekvent uppskattning eller synlighet för att känna engagemang. "
            "Det betyder inte att återkoppling eller erkännande saknar betydelse."
        ),
    },
    "making_a_difference": {
        "name": "Göra skillnad",
        "description": "Att bidra till ett större syfte eller skapa positiv påverkan.",
        "top_text": (
            "Känner motivation av att göra en positiv skillnad för andra. Anser att det är viktigt att vara en del av en organisation vars mål och syfte upplevs som värdiga "
            "och att kunna se hur det egna arbetet har en gynnsam inverkan på samhället i stort."
        ),
        "bottom_text": (
            "Att göra en tydlig positiv skillnad eller bidra till ett större samhällssyfte verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte se en direkt samhällseffekt av arbetet för att känna engagemang. "
            "Det betyder inte att värderingar eller meningsfullhet är oviktiga."
        ),
    },
    "achievement": {
        "name": "Prestation",
        "description": "Tydliga mål, utmaningar och en synlig känsla av framsteg.",
        "top_text": (
            "Får energi av definierade och utmanande mål att arbeta mot. Möjligheter som utmanar professionellt har stor betydelse, "
            "och de trivs med konkurrens och en miljö där de har möjlighet att jämföra sin prestation med andras."
        ),
        "bottom_text": (
            "Utmanande mål, konkurrens och tydliga prestationsjämförelser verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte ständig tävlan eller högt satta mål för att känna engagemang. "
            "Ett lägre resultat betyder inte låg ambitionsnivå eller låg prestationsförmåga."
        ),
    },
    "quality": {
        "name": "Kvalitet",
        "description": "Att leverera noggrant och tillförlitligt arbete med hög kvalitet.",
        "top_text": (
            "Motiveras av att leverera högkvalitativa resultat på en konsekvent basis. Är stolt över att producera arbete som är i linje med både vad de har lovat och vad som förväntas av dem. "
            "Säkerställer att arbetet slutförs så perfekt som möjligt."
        ),
        "bottom_text": (
            "Att sträva efter perfektion och göra kvalitet till en central drivkraft verkar vara mindre motiverande. "
            "Personen behöver sannolikt inte själva kvalitetssträvandet för att känna engagemang. "
            "Ett lägre resultat betyder inte att personen levererar arbete av låg kvalitet eller saknar noggrannhet."
        ),
    },
    "learning": {
        "name": "Lärande",
        "description": "Att utveckla kunskap, förmåga och nya färdigheter.",
        "top_text": (
            "Drivs av möjligheten att lära sig och utveckla sin expertis. Känner sig bekväm i en miljö där det finns gott om möjligheter till fortlöpande utbildning och utveckling "
            "och att bemästra nya färdigheter."
        ),
        "bottom_text": (
            "Kontinuerligt lärande och utveckling av ny expertis verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte ständiga utbildningsmöjligheter för att känna engagemang. "
            "Det betyder inte att personen är ovillig eller oförmögen att lära sig nya saker."
        ),
    },
    "ethics": {
        "name": "Etik",
        "description": "Att agera i linje med tydliga principer och etiska standarder.",
        "top_text": (
            "Upprätthåller hög etisk standard för sig själv och sin organisation. Följer branschriktlinjer och krav på bästa praxis. "
            "Är stolt över sin professionella integritet och trivs i en organisation vars etiska värderingar ligger i linje med de egna."
        ),
        "bottom_text": (
            "Etiska riktlinjer och värderingsmässig överensstämmelse verkar vara en mindre central källa till motivation i sig. "
            "Personen behöver sannolikt inte att etik är en framträdande del av rollen för att känna engagemang. "
            "Ett lägre resultat säger inte att personen har svag etik eller låg professionell integritet."
        ),
    },
    "commercial_focus": {
        "name": "Kommersiellt värde",
        "description": "Att skapa mätbart kommersiellt värde och affärsresultat.",
        "top_text": (
            "Trivs i en roll som är kommersiellt fokuserad och bidrar till organisationens ekonomiska framgång. "
            "Värdesätter att se kopplingen mellan sin roll och organisationens resultat och får energi av att se hur arbetet leder till kommersiell vinst."
        ),
        "bottom_text": (
            "Kommersiella resultat och direkt koppling till ekonomisk framgång verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte se tydliga finansiella effekter av sitt arbete för att känna engagemang. "
            "Det betyder inte att personen saknar kommersiell förståelse eller förmåga."
        ),
    },
    "curiosity": {
        "name": "Nyfikenhet",
        "description": "Att utforska ny information, frågor och obekanta problem.",
        "top_text": (
            "Motiveras av att utforska och upptäcka nya saker. Eftersträvar kunskap och erfarenhet, utnyttjar möjligheter till nya upplevelser och ny information "
            "och utforskar de saker som fångar deras intresse."
        ),
        "bottom_text": (
            "Att utforska nya områden och söka ny information verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte ständig nyhet eller utforskning för att känna engagemang. "
            "Det betyder inte att personen saknar nyfikenhet eller förmåga att sätta sig in i nya frågor."
        ),
    },
    "creativity": {
        "name": "Kreativitet",
        "description": "Att skapa nya idéer och hitta originella tillvägagångssätt.",
        "top_text": (
            "Motiveras av att utöva sin kreativitet, tänka utanför ramarna, generera nya idéer och identifiera nya lösningar. "
            "Deras idéer och förslag kommer sannolikt att vara användbara, inte bara originella för att vara annorlunda eller unika."
        ),
        "bottom_text": (
            "Att generera nya idéer och hitta originella lösningar verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte ett starkt kreativt inslag i arbetet för att känna engagemang. "
            "Ett lägre resultat betyder inte att personen saknar kreativ förmåga."
        ),
    },
    "enjoyment": {
        "name": "Arbetsglädje",
        "description": "Positiv energi och glädje i det dagliga arbetet.",
        "top_text": (
            "Värdesätter en miljö där man trivs med sitt arbete men även kan ha roligt med sina kollegor. "
            "Trivs i en lättsam miljö där man kan uttrycka sin lekfulla sida, dela humor med kollegor och bli accepterad för den man är."
        ),
        "bottom_text": (
            "En lättsam och socialt lekfull arbetsmiljö verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte humor eller ett tydligt inslag av nöje i arbetsvardagen för att känna engagemang. "
            "Det betyder inte att personen ogillar en trivsam arbetsmiljö eller social samvaro."
        ),
    },
    "variety": {
        "name": "Variation",
        "description": "Förändring, olika uppgifter och varierade arbetssätt.",
        "top_text": (
            "Motiveras av en roll med mycket variation och möjlighet att arbeta med olika saker. Trivs i en mångsidig roll med en blandning av uppgifter och projekt "
            "där de får rikta sin uppmärksamhet mot olika arbetskrav och dra nytta av sina olika färdigheter."
        ),
        "bottom_text": (
            "Variation och ständig växling mellan olika uppgifter verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte stor omväxling för att känna engagemang. "
            "Det betyder inte automatiskt att personen föredrar monotoni eller har svårt att hantera förändring."
        ),
    },
    "risk": {
        "name": "Risktagande",
        "description": "Att ta kalkylerade risker och agera trots osäkerhet.",
        "top_text": (
            "Motiveras av risk i arbetet och att få möta situationer där utgången är oklar. Är bekväm med att ta riskfyllda beslut "
            "och trivs i roller som ger utrymme att uppleva spänningen i att ta en risk och sedan se om det lönar sig."
        ),
        "bottom_text": (
            "Risk och osäkerhet verkar vara en mindre central källa till motivation. "
            "Personen behöver sannolikt inte riskfyllda situationer eller spänning för att känna engagemang i arbetet. "
            "Ett lägre resultat betyder inte att personen undviker nödvändiga eller väl avvägda risker när situationen kräver det."
        ),
    },
}


def _is_swedish() -> bool:
    return str(get_language() or "sv").lower().startswith("sv")


def _item_key(value) -> str:
    if isinstance(value, dict):
        return str(value.get("key") or "").strip()
    return ""


@register.filter
def motivation_profile_title(value):
    if _is_swedish():
        return "Motivationsprofil"
    return value


@register.filter
def motivation_domain_title(value):
    if not _is_swedish() or not isinstance(value, dict):
        return value.get("title", "") if isinstance(value, dict) else value
    content = DOMAIN_CONTENT.get(str(value.get("key") or ""))
    return content["title"] if content else value.get("title", "")


@register.filter
def motivation_domain_subtitle(value):
    if not _is_swedish() or not isinstance(value, dict):
        return value.get("subtitle", "") if isinstance(value, dict) else value
    content = DOMAIN_CONTENT.get(str(value.get("key") or ""))
    return content["subtitle"] if content else value.get("subtitle", "")


@register.filter
def motivation_name(value):
    if not isinstance(value, dict):
        return value
    if not _is_swedish():
        return value.get("name", "")
    content = FACTOR_CONTENT.get(_item_key(value))
    return content["name"] if content else value.get("name", "")


@register.filter
def motivation_description(value):
    if not isinstance(value, dict):
        return value
    if not _is_swedish():
        return value.get("description", "")
    content = FACTOR_CONTENT.get(_item_key(value))
    return content["description"] if content else value.get("description", "")


@register.filter
def motivation_top_interpretation(value):
    if not isinstance(value, dict):
        return value
    if not _is_swedish():
        return value.get("interpretation", "")
    content = FACTOR_CONTENT.get(_item_key(value))
    if content and content.get("top_text"):
        return content["top_text"]
    description = content["description"] if content else value.get("description", "")
    if not description:
        return "Resultatet tyder på att detta kan vara en mer framträdande källa till energi och engagemang."
    return f"{description} Resultatet tyder på att detta kan vara en mer framträdande källa till energi och engagemang."


@register.filter
def motivation_least_prominent(value):
    if not isinstance(value, dict):
        return []
    scored_items = []
    for domain in value.get("domains") or []:
        if not isinstance(domain, dict):
            continue
        for item in domain.get("items") or []:
            if not isinstance(item, dict) or item.get("score") is None:
                continue
            try:
                sort_score = float(item.get("score"))
            except (TypeError, ValueError):
                continue
            scored_items.append((sort_score, item))
    scored_items.sort(key=lambda entry: entry[0])
    return [item for _, item in scored_items[:3]]


@register.filter
def motivation_factors_descending(value):
    if not isinstance(value, dict):
        return []
    scored_items = []
    unscored_items = []
    for domain in value.get("domains") or []:
        if not isinstance(domain, dict):
            continue
        for item in domain.get("items") or []:
            if not isinstance(item, dict):
                continue
            score = item.get("score")
            if score is None:
                unscored_items.append(item)
                continue
            try:
                sort_score = float(score)
            except (TypeError, ValueError):
                unscored_items.append(item)
                continue
            scored_items.append((sort_score, item))
    scored_items.sort(key=lambda entry: entry[0], reverse=True)
    return [item for _, item in scored_items] + unscored_items


@register.filter
def motivation_bottom_interpretation(value):
    if not isinstance(value, dict):
        return value
    if not _is_swedish():
        description = value.get("description", "")
        explanation = (
            "A lower result is not negative; it indicates that this factor is likely to be a less central source of motivation for the person."
        )
        return f"{description} {explanation}".strip()
    content = FACTOR_CONTENT.get(_item_key(value))
    if content and content.get("bottom_text"):
        return content["bottom_text"]
    description = content["description"] if content else value.get("description", "")
    explanation = (
        "Ett lägre resultat är inte negativt, utan visar att faktorn sannolikt är en mindre central källa till motivation för personen."
    )
    return f"{description} {explanation}".strip()
