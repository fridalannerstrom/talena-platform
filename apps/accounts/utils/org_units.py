from django.db import transaction

from apps.accounts.models import CompanyMember, OrgUnit, UserOrgUnitAccess


DEFAULT_ORG_UNIT_NAME = "Main account"
DEFAULT_ORG_UNIT_CODE = "MAIN"


def get_or_create_main_org_unit(company):
    """
    Ensures that a company always has a default/root org unit.

    This is used when the company does not need a custom account structure.
    """
    unit, created = OrgUnit.objects.get_or_create(
        company=company,
        unit_code=DEFAULT_ORG_UNIT_CODE,
        defaults={
            "name": DEFAULT_ORG_UNIT_NAME,
            "parent": None,
        },
    )

    return unit


@transaction.atomic
def ensure_user_has_default_orgunit(user, company, permission="own"):
    """
    Ensures that a user:
    - is a member of the company
    - has a primary org unit
    - has access to the default/main org unit

    Returns:
        membership, main_unit, access
    """
    main_unit = get_or_create_main_org_unit(company)

    membership, _ = CompanyMember.objects.get_or_create(
        company=company,
        user=user,
        defaults={
            "primary_org_unit": main_unit,
        },
    )

    if not membership.primary_org_unit_id:
        membership.primary_org_unit = main_unit
        membership.save(update_fields=["primary_org_unit"])

    access, created_access = UserOrgUnitAccess.objects.get_or_create(
        user=user,
        org_unit=membership.primary_org_unit,
        defaults={
            "permission": permission,
        },
    )

    return membership, membership.primary_org_unit, access