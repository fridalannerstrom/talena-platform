from collections import deque
from django.db.models import Q
from apps.accounts.models import OrgUnit, UserOrgUnitAccess, CompanyMember
from apps.accounts.models import Company
from apps.accounts.models import CompanyMember, OrgUnit, UserOrgUnitAccess, UserOrgUnitProjectAccess
from apps.core.utils.auth import is_admin

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

    Direct permissions come from UserOrgUnitAccess.
    If the user has a primary org unit but no explicit access row,
    they get a safe fallback permission: own.
    """
    children_map = _build_children_map(company)

    direct = list(
        UserOrgUnitAccess.objects
        .filter(user=user, org_unit__company=company)
        .values_list("org_unit_id", "permission")
    )

    primary_id = (
        CompanyMember.objects
        .filter(user=user, company=company)
        .values_list("primary_org_unit_id", flat=True)
        .first()
    )

    if primary_id and not any(int(unit_id) == int(primary_id) for unit_id, _perm in direct):
        direct.append((primary_id, "own"))

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
    # Talena admins can view all customer processes.
    if is_admin(user):
        return True

    perms = get_effective_orgunit_permissions(user, company)
    perm = perms.get(process.org_unit_id)

    if not perm:
        return False

    if perm == "own" and process.created_by_id != user.id:
        return False

    scope = UserOrgUnitProjectAccess.objects.filter(
        user=user,
        org_unit_id=process.org_unit_id,
    ).first()
    if scope and not scope.projects.filter(pk=process.pk).exists():
        return False

    return True


def user_can_edit_process(user, company, process):
    # Talena admins can work inside all customer processes.
    if is_admin(user):
        return True

    perms = get_effective_orgunit_permissions(user, company)
    perm = perms.get(process.org_unit_id)

    if not perm:
        return False

    if perm == "viewer":
        return False

    if not user_can_view_process(user, company, process):
        return False

    return perm == "editor" or (
        perm == "own" and process.created_by_id == user.id
    )

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
    - user's primary org unit
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

    if primary_id:
        all_ids.add(primary_id)

    for rid in list(all_ids):
        all_ids |= _descendants(children_map, rid)

    return all_ids

def filter_processes_for_user(queryset, user, company):
    """Apply unit role and project allow-lists to a process queryset."""
    if is_admin(user):
        return queryset.filter(company=company)

    perms = get_effective_orgunit_permissions(user, company)
    own_ids = [unit_id for unit_id, perm in perms.items() if perm == "own"]
    shared_ids = [
        unit_id for unit_id, perm in perms.items()
        if perm in ("viewer", "editor")
    ]
    allowed = queryset.filter(
        Q(org_unit_id__in=shared_ids)
        | Q(org_unit_id__in=own_ids, created_by=user)
    )

    restricted = UserOrgUnitProjectAccess.objects.filter(
        user=user,
        org_unit_id__in=list(perms),
    ).prefetch_related("projects")
    restricted_ids = []
    allowed_project_ids = []
    for scope in restricted:
        restricted_ids.append(scope.org_unit_id)
        allowed_project_ids.extend(scope.projects.values_list("id", flat=True))

    if restricted_ids:
        allowed = allowed.filter(
            ~Q(org_unit_id__in=restricted_ids)
            | Q(id__in=allowed_project_ids)
        )
    return allowed
