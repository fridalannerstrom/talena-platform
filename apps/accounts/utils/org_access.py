from apps.accounts.models import OrgUnit, UserOrgUnitAccess

def _build_children_map(company):
    units = OrgUnit.objects.filter(company=company).only("id", "parent_id")
    children = {}
    for u in units:
        children.setdefault(u.parent_id, []).append(u.id)
    return children

def _descendants(children_map, root_id):
    out = set()
    stack = list(children_map.get(root_id, []))
    while stack:
        nid = stack.pop()
        if nid in out:
            continue
        out.add(nid)
        stack.extend(children_map.get(nid, []))
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

    all_ids = set(direct_ids)
    for rid in direct_ids:
        all_ids |= _descendants(children_map, rid)

    return all_ids
