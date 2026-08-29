# Bilingual display helpers for Talena Motivation Results.

from __future__ import annotations

from django import template
from django.utils.translation import get_language


register = template.Library()


DOMAIN_CONTENT = {
    "belonging": {
        "title": "Samhörighet",
        "subtitle": (
            "Social kontakt, stöd och en känsla av tillhörighet i arbetet"
        ),
    },
    "influence": {
        "title": "Inflytande",
        "subtitle": (
            "Självständighet, erkännande och möjligheter att påverka resultat"
        ),
    },
    "growth": {
        "title": "Utveckling",
        "subtitle": (
            "Prestation, kvalitet, lärande och meningsfulla standarder"
        ),
    },
    "interest": {
        "title": "Intresse",
        "subtitle": (
            "Utforskande, kreativitet, arbetsglädje, variation och risktagande"
        ),
    },
}


FACTOR_CONTENT = {
    "attachment": {
        "name": "Samhörighet",
        "description": (
            "Social kontakt, stöd och att arbeta som en del av ett team."
        ),
    },
    "customer_service": {
        "name": "Kundservice",
        "description": (
            "Att förstå kunders behov och ge hjälpsam service."
        ),
    },
    "work_life_balance": {
        "name": "Balans mellan arbete och fritid",
        "description": (
            "Att upprätthålla en hållbar balans mellan arbete och "
            "livet utanför arbetet."
        ),
    },
    "people_development": {
        "name": "Utveckla andra",
        "description": (
            "Att hjälpa andra människor att lära, växa och utvecklas."
        ),
    },
    "stability": {
        "name": "Stabilitet",
        "description": (
            "Förutsägbarhet, kontinuitet och trygghet i arbetsmiljön."
        ),
    },
    "authority": {
        "name": "Auktoritet",
        "description": (
            "Status, senioritet och möjligheten att påverka eller leda andra."
        ),
    },
    "independence": {
        "name": "Självständighet",
        "description": (
            "Frihet att fatta beslut och påverka hur arbetet genomförs."
        ),
    },
    "recognition": {
        "name": "Erkännande",
        "description": (
            "Synlighet, beröm och uppskattning för den egna insatsen."
        ),
    },
    "making_a_difference": {
        "name": "Göra skillnad",
        "description": (
            "Att bidra till ett större syfte eller skapa positiv påverkan."
        ),
    },
    "acquisition": {
        "name": "Ekonomisk belöning",
        "description": (
            "Ekonomisk belöning, resurser och materiella fördelar."
        ),
    },
    "achievement": {
        "name": "Prestation",
        "description": (
            "Tydliga mål, utmaningar och en synlig känsla av framsteg."
        ),
    },
    "quality": {
        "name": "Kvalitet",
        "description": (
            "Att leverera noggrant och tillförlitligt arbete med hög kvalitet."
        ),
    },
    "learning": {
        "name": "Lärande",
        "description": (
            "Att utveckla kunskap, förmåga och nya färdigheter."
        ),
    },
    "ethics": {
        "name": "Etik",
        "description": (
            "Att agera i linje med tydliga principer och etiska standarder."
        ),
    },
    "commercial_focus": {
        "name": "Kommersiellt värde",
        "description": (
            "Att skapa mätbart kommersiellt värde och affärsresultat."
        ),
    },
    "curiosity": {
        "name": "Nyfikenhet",
        "description": (
            "Att utforska ny information, frågor och obekanta problem."
        ),
    },
    "creativity": {
        "name": "Kreativitet",
        "description": (
            "Att skapa nya idéer och hitta originella tillvägagångssätt."
        ),
    },
    "enjoyment": {
        "name": "Arbetsglädje",
        "description": (
            "Positiv energi och glädje i det dagliga arbetet."
        ),
    },
    "variety": {
        "name": "Variation",
        "description": (
            "Förändring, olika uppgifter och varierade arbetssätt."
        ),
    },
    "risk": {
        "name": "Risktagande",
        "description": (
            "Att ta kalkylerade risker och agera trots osäkerhet."
        ),
    },
}


def _is_swedish() -> bool:
    return str(
        get_language()
        or "sv"
    ).lower().startswith("sv")


def _item_key(value) -> str:
    if isinstance(value, dict):
        return str(
            value.get("key")
            or ""
        ).strip()

    return ""


@register.filter
def motivation_profile_title(value):
    if _is_swedish():
        return "Motivationsprofil"

    return value


@register.filter
def motivation_domain_title(value):
    if not _is_swedish() or not isinstance(value, dict):
        return (
            value.get("title", "")
            if isinstance(value, dict)
            else value
        )

    content = DOMAIN_CONTENT.get(
        str(value.get("key") or "")
    )
    return (
        content["title"]
        if content
        else value.get("title", "")
    )


@register.filter
def motivation_domain_subtitle(value):
    if not _is_swedish() or not isinstance(value, dict):
        return (
            value.get("subtitle", "")
            if isinstance(value, dict)
            else value
        )

    content = DOMAIN_CONTENT.get(
        str(value.get("key") or "")
    )
    return (
        content["subtitle"]
        if content
        else value.get("subtitle", "")
    )


@register.filter
def motivation_name(value):
    if not isinstance(value, dict):
        return value

    if not _is_swedish():
        return value.get("name", "")

    content = FACTOR_CONTENT.get(
        _item_key(value)
    )
    return (
        content["name"]
        if content
        else value.get("name", "")
    )


@register.filter
def motivation_description(value):
    if not isinstance(value, dict):
        return value

    if not _is_swedish():
        return value.get("description", "")

    content = FACTOR_CONTENT.get(
        _item_key(value)
    )
    return (
        content["description"]
        if content
        else value.get("description", "")
    )


@register.filter
def motivation_top_interpretation(value):
    if not isinstance(value, dict):
        return value

    if not _is_swedish():
        return value.get("interpretation", "")

    content = FACTOR_CONTENT.get(
        _item_key(value)
    )
    description = (
        content["description"]
        if content
        else value.get("description", "")
    )

    if not description:
        return (
            "Resultatet tyder på att detta kan vara en mer "
            "framträdande källa till energi och engagemang."
        )

    return (
        f"{description} Resultatet tyder på att detta kan vara en "
        "mer framträdande källa till energi och engagemang."
    )


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
def motivation_bottom_interpretation(value):
    if not isinstance(value, dict):
        return value

    content = FACTOR_CONTENT.get(
        _item_key(value)
    )
    description = (
        content["description"]
        if _is_swedish() and content
        else value.get("description", "")
    )

    if _is_swedish():
        explanation = (
            "Ett lägre resultat är inte negativt, utan visar att faktorn "
            "sannolikt är en mindre central källa till motivation för personen."
        )
    else:
        explanation = (
            "A lower result is not negative; it indicates that this factor "
            "is likely to be a less central source of motivation for the person."
        )

    if not description:
        return explanation

    return f"{description} {explanation}"
