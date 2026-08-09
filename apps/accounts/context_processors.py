from apps.accounts.models import CompanyMember
from apps.core.utils.auth import is_admin
from apps.processes.models import (
    HistoricalProcessCandidate,
    TestProcess,
)


def migration_onboarding(request):
    """
    Expose migration-onboarding data globally
    in the customer workspace.

    The onboarding is shown only when:

    - the user is authenticated
    - the user is not a Talena platform admin
    - the user's company has migration onboarding enabled
    - this specific company membership has not seen it yet
    - the company actually has historical archived processes
    """

    context = {
        "show_migration_onboarding": False,
    }

    user = getattr(
        request,
        "user",
        None,
    )

    if (
        not user
        or not user.is_authenticated
        or is_admin(user)
    ):
        return context

    membership = (
        CompanyMember.objects
        .select_related("company")
        .filter(user=user)
        .first()
    )

    if not membership:
        return context

    company = membership.company

    if not company.migration_onboarding_enabled:
        return context

    if membership.migration_onboarding_seen_at:
        return context

    historical_processes = (
        TestProcess.objects
        .filter(
            company=company,
            is_historical=True,
            is_archived=True,
        )
    )

    historical_process_count = (
        historical_processes.count()
    )

    # Do not show the onboarding before
    # historical data has actually been imported.
    if not historical_process_count:
        return context

    historical_candidate_count = (
        HistoricalProcessCandidate.objects
        .filter(
            process__in=historical_processes
        )
        .values("candidate_id")
        .distinct()
        .count()
    )

    return {
        "show_migration_onboarding": True,
        "migration_company": company,
        "migration_membership": membership,
        "migration_historical_process_count": (
            historical_process_count
        ),
        "migration_historical_candidate_count": (
            historical_candidate_count
        ),
    }