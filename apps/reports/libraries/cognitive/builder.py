from apps.reports.libraries.cognitive.definitions import COGNITIVE_TESTS, COGNITIVE_REPORTS
from apps.reports.libraries.cognitive.resolver import resolve_cognitive_report_content
from apps.reports.libraries.cognitive.candidate_result_content import (
    CANDIDATE_COGNITIVE_REPORT_COPY,
    CANDIDATE_SKILL_ABILITIES,
    CANDIDATE_SKILL_TITLES,
    resolve_candidate_skill_text,
)


def build_cognitive_report(
    *,
    test_key: str,
    audience: str,
    percentile: int | None,
    language_code: str = "en",
) -> dict:
    if audience == "candidate":
        locale = str(language_code or "en").lower()[:2]
        if locale not in {"sv", "en"}:
            locale = "en"
        candidate_copy = CANDIDATE_COGNITIVE_REPORT_COPY[locale]
        return {
            "key": f"{test_key}_{audience}",
            "test_key": test_key,
            "audience": audience,
            "title": candidate_copy["title"],
            "label": CANDIDATE_SKILL_TITLES[locale][test_key],
            "percentile": None,
            "percentile_band": "",
            "intro": candidate_copy["intro"],
            "test_description": candidate_copy["test_description"].format(
                ability=CANDIDATE_SKILL_ABILITIES[locale][test_key]
            ),
            "result_text": resolve_candidate_skill_text(
                test_key,
                percentile,
                language_code=locale,
            ),
        }

    resolved = resolve_cognitive_report_content(
        test_key=test_key,
        audience=audience,
        percentile=percentile,
    )

    report = {
        "key": f"{test_key}_{audience}",
        "test_key": test_key,
        "audience": audience,
        "title": COGNITIVE_REPORTS[audience]["title"],
        "label": resolved["label"],
        "percentile": resolved["percentile"],
        "percentile_band": resolved["percentile_band"],
        "intro": resolved["intro"],
        "test_description": resolved["test_description"],
        "result_text": resolved["result_text"],
    }
    return report


def build_cognitive_reports_for_test(
    *,
    test_key: str,
    percentile: int | None,
    language_code: str = "en",
) -> dict:
    test_def = COGNITIVE_TESTS[test_key]

    return {
        "key": test_key,
        "label": test_def["label"],
        "percentile": percentile,
        "practitioner_report": build_cognitive_report(
            test_key=test_key,
            audience="practitioner",
            percentile=percentile,
        ),
        "candidate_report": build_cognitive_report(
            test_key=test_key,
            audience="candidate",
            percentile=percentile,
            language_code=language_code,
        ),
    }
