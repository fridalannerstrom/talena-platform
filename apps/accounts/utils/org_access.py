from collections import deque
from django.db.models import Q
from apps.accounts.models import OrgUnit, UserOrgUnitAccess, CompanyMember
from apps.accounts.models import Company
from apps.accounts.models import CompanyMember, OrgUnit, UserOrgUnitAccess

PERM_RANK = {"own": 1, "viewer": 2, "editor": 3}

def _best_perm(a, b):
    if not a:
        return b
    return a if PERM_RANK[a] >= PERM_RANK[b] else b


def get_company_for_user(user):
    company_id = (
        CompanyMember.objects
        .filter(user=user)
        .values_list("company_id", flat=True)
        .first()
    )
    return Company.objects.get(pk=company_id) if company_id else None


def get_effective_orgunit_permissions(user, company):
    """
    Return dict {org_unit_id: perm} including inherited perms to descendants.
    More specific (child) can override if you want, but for MVP: strongest wins.
    """
    children_map = _build_children_map(company)

    direct = list(
        UserOrgUnitAccess.objects
        .filter(user=user, org_unit__company=company)
        .values_list("org_unit_id", "permission")
    )

    perm_map = {}

    for unit_id, perm in direct:
        unit_id = int(unit_id)

        # unit itself
        perm_map[unit_id] = _best_perm(perm_map.get(unit_id), perm)

        # descendants inherit same perm
        for child_id in _descendants(children_map, unit_id):
            perm_map[child_id] = _best_perm(perm_map.get(child_id), perm)

    return perm_map

def user_can_view_process(user, company, process):
    perms = get_effective_orgunit_permissions(user, company)
    perm = perms.get(process.org_unit_id)
    if not perm:
        return False
    if perm == "own":
        return process.created_by_id == user.id
    return True


def user_can_edit_process(user, company, process):
    perms = get_effective_orgunit_permissions(user, company)
    perm = perms.get(process.org_unit_id)
    if not perm:
        return False
    if perm == "viewer":
        return False
    if perm == "own":
        return process.created_by_id == user.id
    return True  # editor

def _build_children_map(company):
    units = OrgUnit.objects.filter(company=company).only("id", "parent_id")
    children = {}
    for u in units:
        children.setdefault(u.parent_id, []).append(u.id)   # <- ids
    return children

def _descendants(children_map, root_id):
    out = set()
    q = deque(children_map.get(root_id, []))
    while q:
        nid = q.popleft()
        if nid in out:
            continue
        out.add(nid)
        q.extend(children_map.get(nid, []))
    return out

def get_accessible_orgunit_ids(user, company):
    """
    Units user can access in company:
    - direct assignments
    - plus all descendants of those units
    """
    children_map = _build_children_map(company)

    direct_ids = set(
        UserOrgUnitAccess.objects
        .filter(user=user, org_unit__company=company)
        .values_list("org_unit_id", flat=True)
    )

    primary_id = (
        CompanyMember.objects
        .filter(user=user, company=company)
        .values_list("primary_org_unit_id", flat=True)
        .first()
    )

    all_ids = set(direct_ids)
    for rid in direct_ids:
        all_ids |= _descendants(children_map, rid)

    return all_ids
