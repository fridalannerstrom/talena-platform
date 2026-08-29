from __future__ import annotations

from django import template
from django.utils.translation import get_language


register = template.Library()


SWEDISH_LIST_DEFINITIONS = {
    "attachment": "Motiveras av socialt samspel samt av att få stöd och arbeta i team.",
    "customer_service": "Motiveras av kundinriktade miljöer samt av att förstå kunders behov och ge god service.",
    "work_life_balance": "Motiveras av att kunna bevara en hälsosam balans mellan arbete och fritid.",
    "people_development": "Motiveras av att hjälpa andra att växa och utvecklas.",
    "stability": "Motiveras av anställningstrygghet samt stabilitet och enhetlighet i organisationen.",
    "authority": "Motiveras av bekräftelse gällande yrkesmässig status samt att utöva makt och inflytande över andra.",
    "acquisition": "Motiveras av ökat välstånd och ekonomisk belöning.",
    "independence": "Motiveras av att själv kunna styra över sin egen tid och sitt arbetssätt.",
    "recognition": "Motiveras av synlighet, beröm och av att få sina prestationer erkända inför andra.",
    "making_a_difference": "Motiveras av att bidra till organisationen, samhället eller någon sorts större syfte.",
    "achievement": "Motiveras av att uppnå mål, bemästra svårigheter och konkurrera med andra.",
    "quality": "Motiveras av att leverera arbetsresultat med hög precision och kvalitet i tid.",
    "ethics": "Motiveras av att upprätthålla höga etiska normer både för egen del och för organisationens del.",
    "commercial_focus": "Motiveras av att skapa intäkter och vinst för organisationen.",
    "creativity": "Motiveras av nyskapande och att hitta nya möjligheter till kreativitet.",
    "enjoyment": "Motiveras av att trivas på arbetet och ha roligt med kollegorna.",
    "risk": "Motiveras av att få mandat att ta risker i arbetet.",
    "variety": "Motiveras av variation i arbetet, nya och varierade arbetssätt samt förändring.",
    "learning": "Motiveras av möjligheter till vidareutveckling, fortbildning och att lära sig nya färdigheter.",
    "curiosity": "Motiveras av att hitta ny information och lösa nya problem.",
}


def _is_swedish() -> bool:
    return str(get_language() or "sv").lower().startswith("sv")


@register.filter
def motivation_list_description(value):
    if not isinstance(value, dict):
        return value

    if not _is_swedish():
        return value.get("description", "")

    key = str(value.get("key") or "").strip()
    return SWEDISH_LIST_DEFINITIONS.get(key, value.get("description", ""))
