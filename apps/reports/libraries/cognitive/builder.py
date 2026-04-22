from apps.reports.libraries.cognitive.definitions import COGNITIVE_TESTS, COGNITIVE_REPORTS
from apps.reports.libraries.cognitive.resolver import resolve_cognitive_report_content


def build_cognitive_report(
    *,
    test_key: str,
    audience: str,
    percentile: int | None,
) -> dict:
    resolved = resolve_cognitive_report_content(
        test_key=test_key,
        audience=audience,
        percentile=percentile,
    )

    return {
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


def build_cognitive_reports_for_test(
    *,
    test_key: str,
    percentile: int | None,
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
        ),
    }