from typing import Iterable
from apps.accounts.models import OrgUnit, UserOrgUnitAccess, CompanyMember


def get_user_accessible_orgunits(user) -> Iterable[OrgUnit]:
    return (
        OrgUnit.objects
        .filter(user_accesses__user=user)
        .select_related("parent", "company")
        .distinct()
        .order_by("name")
    )


def user_can_access_orgunit(user, org_unit: OrgUnit) -> bool:
    if not org_unit:
        return False

    if not CompanyMember.objects.filter(user=user, company=org_unit.company).exists():
        return False

    return UserOrgUnitAccess.objects.filter(user=user, org_unit=org_unit).exists()


# ---------------------------------------------------------------------------
# Legacy alias: så gamla imports inte kraschar
# ---------------------------------------------------------------------------

def get_user_accessible_accounts(user):
    return get_user_accessible_orgunits(user)


def filter_by_user_accounts(user, queryset):
    return queryset.filter(org_unit__in=get_user_accessible_orgunits(user))


def user_can_access_account(user, obj) -> bool:
    if isinstance(obj, OrgUnit):
        return user_can_access_orgunit(user, obj)

    org_unit = getattr(obj, "org_unit", None)
    if org_unit:
        return user_can_access_orgunit(user, org_unit)

    return False
