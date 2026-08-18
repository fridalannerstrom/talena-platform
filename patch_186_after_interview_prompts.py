from pathlib import Path

ROOT = Path(".")
PROMPT_TEMPLATES = ROOT / "apps/core/ai/prompt_templates.py"
DECISION_SUPPORT = ROOT / "apps/core/ai/decision_support.py"
PLAYGROUND = ROOT / "apps/core/ai/prompt_playground.py"

REGISTRY_ENTRIES = '\n    "post_interview_supported_indications": {\n        "name": "After interview · Evidence supporting assessment indications",\n        "category": "Interview",\n        "description": "Controls only the supported assessment indications section.",\n        "defaults": {\n            "sv": """Styr endast sektionen Evidence supporting assessment indications i Efter intervju.\n\nIdentifiera intervjuevidens som är förenlig med tidigare assessment-indikationer.\nSom standard, ge 2 till 4 relevanta items.\nSkilj tydligt mellan assessment-indikation, intervju-evidens och integrerad tolkning.\nEtt intervju-exempel bevisar inte automatiskt ett stabilt beteende, kompetens eller framtida prestation.\nHitta inte på stöd bara för att fylla sektionen. Listan får vara tom.""".strip(),\n            "en": """Control only the Evidence supporting assessment indications section in After interview.\n\nIdentify interview evidence consistent with earlier assessment indications.\nBy default, provide 2 to 4 relevant items.\nDistinguish assessment indication, interview evidence and integrated interpretation.\nAn interview example does not automatically prove stable behaviour, competence or future performance.\nDo not invent support merely to populate the section. The list may be empty.""".strip(),\n        },\n    },\n\n    "post_interview_added_nuance": {\n        "name": "After interview · What the interview adds or nuances",\n        "category": "Interview",\n        "description": "Controls only the added nuance section in After interview.",\n        "defaults": {\n            "sv": """Styr endast sektionen What the interview adds or nuances i Efter intervju.\n\nIdentifiera intervjuevidens som faktiskt förändrar, begränsar, förtydligar eller nyanserar en tidigare assessment-tolkning.\nSom standard, ge 2 till 4 relevanta items.\nFörankra varje item i faktiskt assessment- och intervjuunderlag.\nSkapa inte nyans som saknar stöd. Listan får vara tom.""".strip(),\n            "en": """Control only the What the interview adds or nuances section in After interview.\n\nIdentify interview evidence that materially changes, limits, clarifies or adds nuance to an earlier assessment interpretation.\nBy default, provide 2 to 4 relevant items.\nGround each item in actual assessment and interview evidence.\nDo not invent unsupported nuance. The list may be empty.""".strip(),\n        },\n    },\n\n    "post_interview_contradictions": {\n        "name": "After interview · Contradictions or tensions",\n        "category": "Interview",\n        "description": "Controls only the contradictions or tensions section in After interview.",\n        "defaults": {\n            "sv": """Styr endast sektionen Contradictions or tensions to consider i Efter intervju.\n\nIdentifiera relevanta skillnader eller spänningar mellan assessment- och intervjuunderlag.\nSom standard, ge 0 till 3 items.\nBeskriv skillnader neutralt. En skillnad betyder inte automatiskt att någon källa är fel.\nHitta inte på motsägelser för att fylla sektionen. Listan får vara tom.""".strip(),\n            "en": """Control only the Contradictions or tensions to consider section in After interview.\n\nIdentify meaningful differences or tensions between assessment and interview evidence.\nBy default, provide 0 to 3 items.\nDescribe differences neutrally. A difference does not automatically mean either source is wrong.\nDo not invent contradictions to populate the section. The list may be empty.""".strip(),\n        },\n    },\n\n    "post_interview_remaining_uncertainties": {\n        "name": "After interview · Remaining uncertainties",\n        "category": "Interview",\n        "description": "Controls only the remaining uncertainties section in After interview.",\n        "defaults": {\n            "sv": """Styr endast sektionen Remaining uncertainties i Efter intervju.\n\nIdentifiera verkliga frågor eller informationsgap som fortfarande inte kan besvaras säkert efter assessment och intervju.\nSom standard, ge upp till 5 korta punkter.\nHitta inte på osäkerheter bara för att fylla sektionen. Listan får vara tom.""".strip(),\n            "en": """Control only the Remaining uncertainties section in After interview.\n\nIdentify genuine questions or evidence gaps that still cannot be answered confidently after assessment and interview.\nBy default, provide up to 5 concise items.\nDo not invent uncertainty merely to populate the section. The list may be empty.""".strip(),\n        },\n    },\n\n    "post_interview_suggested_follow_up": {\n        "name": "After interview · Suggested follow-up",\n        "category": "Interview",\n        "description": "Controls only the suggested follow-up section in After interview.",\n        "defaults": {\n            "sv": """Styr endast sektionen Suggested follow-up i Efter intervju.\n\nFöreslå proportionerliga nästa steg som kan ge bättre evidens kring verkliga kvarstående frågor.\nSom standard, ge 2 till 5 relevanta uppföljningar.\nFöreslå endast sådant som har tydlig koppling till underlaget och kvarstående osäkerhet.\nGör inte beslut om anställning, avslag, placering eller befordran.""".strip(),\n            "en": """Control only the Suggested follow-up section in After interview.\n\nSuggest proportionate next steps that may provide better evidence for genuine remaining questions.\nBy default, provide 2 to 5 relevant follow-up actions.\nRecommend only actions clearly connected to the evidence and remaining uncertainty.\nDo not make hiring, rejection, placement or promotion decisions.""".strip(),\n        },\n    },\n\n'
OLD_DESCRIPTION = '"description": (\n            "Controls the tone, emphasis and synthesis style used when "\n            "Talena combines assessment evidence with interview notes "\n            "after the interview."\n        ),'
NEW_DESCRIPTION = '"description": (\n            "Controls only the Overall synthesis section in After interview."\n        ),'
OLD_LOOKUP = '    admin_instructions = (\n        get_ai_prompt_instructions(\n            key=(\n                "post_interview_"\n                "decision_support"\n            ),\n            language=language_code,\n        )\n    )\n'
NEW_LOOKUP = '    overall_instructions = get_ai_prompt_instructions(\n        key="post_interview_decision_support",\n        language=language_code,\n    )\n    supported_instructions = get_ai_feature_prompt_instructions(\n        key="post_interview_supported_indications",\n        language=language_code,\n    )\n    nuance_instructions = get_ai_feature_prompt_instructions(\n        key="post_interview_added_nuance",\n        language=language_code,\n    )\n    contradictions_instructions = get_ai_feature_prompt_instructions(\n        key="post_interview_contradictions",\n        language=language_code,\n    )\n    uncertainties_instructions = get_ai_feature_prompt_instructions(\n        key="post_interview_remaining_uncertainties",\n        language=language_code,\n    )\n    follow_up_instructions = get_ai_feature_prompt_instructions(\n        key="post_interview_suggested_follow_up",\n        language=language_code,\n    )\n'
GUIDANCE = "ADMINISTRATOR AI GUIDANCE\n\nOVERALL SYNTHESIS GUIDANCE\nApplies only to overall_synthesis_delta and context_note.\n{overall_instructions}\n\nSUPPORTED INDICATIONS GUIDANCE\nApplies only to supported_indications.\n{supported_instructions}\n\nADDED NUANCE GUIDANCE\nApplies only to added_nuance.\n{nuance_instructions}\n\nCONTRADICTIONS GUIDANCE\nApplies only to contradictions.\n{contradictions_instructions}\n\nREMAINING UNCERTAINTIES GUIDANCE\nApplies only to remaining_uncertainties.\n{uncertainties_instructions}\n\nSUGGESTED FOLLOW-UP GUIDANCE\nApplies only to suggested_follow_up.\n{follow_up_instructions}\n\nSECTION ISOLATION\nTreat each guidance block as authoritative only for its corresponding event.\nInstructions for one section must not change another section's substantive content or item count.\nGlobal Talena guidance still applies across all sections.\nDo not change required event names, JSON fields, NDJSON structure or streaming order.\n\n\n"
OLD_SCENARIO = '    "post_interview_decision_support": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": (\n            ALL_ASSESSMENT_EVIDENCE\n            + "\\n\\n"\n            + INTERVIEW_EVIDENCE\n        ),\n        "task": """\nGenerate sample post-interview decision support.\n\nIntegrate assessment evidence with the supplied sample interview\nnotes.\n\nDistinguish clearly between:\n\nEvidence supporting assessment indications\nWhat the interview adds or nuances\nWhat remains uncertain\nWhat requires cautious interpretation\n\nDo not invent evidence beyond the supplied information.\n""".strip(),\n    },\n'
NEW_SCENARIOS = '    "post_interview_decision_support": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": """\nGenerate only sample content for After interview · Overall synthesis.\nDo not generate the other After interview sections.\n""".strip(),\n    },\n\n    "post_interview_supported_indications": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": "Generate only Evidence supporting assessment indications.",\n    },\n\n    "post_interview_added_nuance": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": "Generate only What the interview adds or nuances.",\n    },\n\n    "post_interview_contradictions": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": "Generate only Contradictions or tensions to consider.",\n    },\n\n    "post_interview_remaining_uncertainties": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": "Generate only Remaining uncertainties.",\n    },\n\n    "post_interview_suggested_follow_up": {\n        "purpose": "hiring",\n        "purpose_label": "Recruitment",\n        "context": RECRUITMENT_CONTEXT,\n        "evidence": ALL_ASSESSMENT_EVIDENCE + "\\n\\n" + INTERVIEW_EVIDENCE,\n        "task": "Generate only Suggested follow-up.",\n    },\n'

for path in (PROMPT_TEMPLATES, DECISION_SUPPORT, PLAYGROUND):
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run from repo root.")

# prompt_templates.py
text = PROMPT_TEMPLATES.read_text(encoding="utf-8")

if '"post_interview_supported_indications"' in text:
    raise SystemExit("After-interview prompt split already appears applied.")

post_start = text.find('"post_interview_decision_support": {')
registry_end_marker = "\n}\n\n\ndef normalize_prompt_language("
registry_end = text.find(registry_end_marker, post_start)

if post_start == -1 or registry_end == -1:
    raise SystemExit("Could not locate post-interview registry block.")

post_block = text[post_start:registry_end]

if '"name": "Post-interview decision support"' not in post_block:
    raise SystemExit("Could not find existing post-interview prompt name.")

post_block = post_block.replace(
    '"name": "Post-interview decision support"',
    '"name": "After interview · Overall synthesis"',
    1,
)

if OLD_DESCRIPTION not in post_block:
    raise SystemExit("Could not find existing post-interview description.")

post_block = post_block.replace(
    OLD_DESCRIPTION,
    NEW_DESCRIPTION,
    1,
)

text = text[:post_start] + post_block + text[registry_end:]
text = text.replace(
    registry_end_marker,
    "\n" + REGISTRY_ENTRIES + registry_end_marker,
    1,
)

compile(text, str(PROMPT_TEMPLATES), "exec")
new_prompt_templates = text

# decision_support.py
text = DECISION_SUPPORT.read_text(encoding="utf-8")

old_import = "from .prompt_templates import get_ai_prompt_instructions\n"
new_import = """from .prompt_templates import (
    get_ai_prompt_instructions,
    get_ai_feature_prompt_instructions,
)
"""

if old_import not in text:
    raise SystemExit("Could not find prompt_templates import.")

text = text.replace(old_import, new_import, 1)

marker = """def build_post_interview_decision_support_prompt(
    owner,
    *,
    language_code: str | None = None,
) -> str:
"""

start = text.find(marker)
end = text.find("\ndef create_empty_post_interview_decision_support(", start)

if start == -1 or end == -1:
    raise SystemExit("Could not isolate language-aware post-interview prompt builder.")

block = text[start:end]

if OLD_LOOKUP not in block:
    raise SystemExit("Could not find current post-interview admin lookup.")

block = block.replace(OLD_LOOKUP, NEW_LOOKUP, 1)

gs = block.find("ADMINISTRATOR AI GUIDANCE\n")
ts = block.find("TALENA TECHNICAL OUTPUT CONTRACT\n", gs)

if gs == -1 or ts == -1:
    raise SystemExit("Could not isolate administrator guidance section.")

block = block[:gs] + GUIDANCE + block[ts:]
text = text[:start] + block + text[end:]

compile(text, str(DECISION_SUPPORT), "exec")
new_decision_support = text

# prompt_playground.py
text = PLAYGROUND.read_text(encoding="utf-8")

if OLD_SCENARIO not in text:
    raise SystemExit("Could not find current post-interview playground scenario.")

text = text.replace(OLD_SCENARIO, NEW_SCENARIOS, 1)

compile(text, str(PLAYGROUND), "exec")
new_playground = text

# Write only after all validation succeeds.
PROMPT_TEMPLATES.write_text(new_prompt_templates, encoding="utf-8")
DECISION_SUPPORT.write_text(new_decision_support, encoding="utf-8")
PLAYGROUND.write_text(new_playground, encoding="utf-8")

print("Updated:")
print("✓ apps/core/ai/prompt_templates.py")
print("✓ apps/core/ai/decision_support.py")
print("✓ apps/core/ai/prompt_playground.py")
print()
print("#186 After interview split complete:")
print("✓ 6 visible After interview sections now have isolated admin guidance")
print("✓ One OpenAI call retained")
print("✓ Technical NDJSON contract unchanged")
print("✓ Playground scenarios split for isolation testing")
