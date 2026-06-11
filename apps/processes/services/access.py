from django.db.models import Q

from apps.accounts.models import CompanyMember
from apps.accounts.utils.org_access import get_effective_orgunit_permissions
from apps.processes.models import TestProcess


def get_company_for_request_user(user):
    """
    Returns the first company linked to the user.

    Later, if users can actively switch between companies/accounts,
    this function can be updated to respect the active company.
    """
    membership = (
        CompanyMember.objects
        .select_related("company")
        .filter(user=user)
        .first()
    )

    return membership.company if membership else None


def get_accessible_processes_for_user(user, include_archived=False):
    """
    Returns processes the user is allowed to access.

    Access logic:
    - viewer/editor org units: user can see all processes in those units
    - own org units: user can only see processes they created
    """
    company = get_company_for_request_user(user)

    if not company:
        return TestProcess.objects.none(), None

    perms = get_effective_orgunit_permissions(user, company)

    own_ids = [
        unit_id
        for unit_id, permission in perms.items()
        if permission == "own"
    ]

    visible_ids = [
        unit_id
        for unit_id, permission in perms.items()
        if permission in ("viewer", "editor")
    ]

    process_q = Q(company=company) & (
        Q(org_unit_id__in=visible_ids) |
        Q(org_unit_id__in=own_ids, created_by=user)
    )

    queryset = TestProcess.objects.filter(process_q)

    if not include_archived:
        queryset = queryset.filter(is_archived=False)

    return queryset, company