"""
Behörighetslogik för Account-hierarkin
"""
from apps.accounts.models import Account, UserAccountAccess, CompanyMember


def user_can_access_process(user, process) -> bool:
    # Admins får allt
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True

    # Skaparen får alltid se sin process (bra fallback vid gamla data)
    if getattr(process, "created_by_id", None) == getattr(user, "id", None):
        return True

    # Process utan company -> neka (eller ändra om du vill)
    if not getattr(process, "company_id", None):
        return False

    # Användaren måste vara medlem i samma company
    return CompanyMember.objects.filter(user=user, company_id=process.company_id).exists()


def get_user_accessible_accounts(user):
    """
    Hämtar alla accounts som en user har tillgång till.
    
    För admins (is_staff/is_superuser): alla accounts
    För customers: sitt account + alla child-accounts
    """
    if user.is_staff or user.is_superuser:
        # Alla admins ser alla accounts (ditt krav D)
        return Account.objects.all()
    
    try:
        access = UserAccountAccess.objects.select_related('account').get(user=user)
        return Account.objects.filter(
            id__in=[acc.id for acc in access.get_accessible_accounts()]
        )
    except UserAccountAccess.DoesNotExist:
        # User har inget account kopplat → ingen access
        return Account.objects.none()


def user_can_access_account(user, account):
    """
    Kontrollerar om en user har tillgång till ett specifikt account.
    """
    if user.is_staff or user.is_superuser:
        return True
    
    accessible_accounts = get_user_accessible_accounts(user)
    return account in accessible_accounts


def get_user_account(user):
    """
    Returnerar det account som en user tillhör (eller None).
    """
    try:
        access = UserAccountAccess.objects.select_related('account').get(user=user)
        return access.account
    except UserAccountAccess.DoesNotExist:
        return None


def filter_by_user_accounts(queryset, user, account_field='account'):
    """
    Filtrerar en queryset baserat på användarens account-access.
    
    Exempel:
        processes = TestProcess.objects.all()
        processes = filter_by_user_accounts(processes, request.user, 'account')
    
    Args:
        queryset: Django QuerySet som ska filtreras
        user: User-objektet
        account_field: Namnet på fältet som pekar på Account (default: 'account')
    """
    if user.is_staff or user.is_superuser:
        return queryset
    
    accessible_accounts = get_user_accessible_accounts(user)
    filter_kwargs = {f'{account_field}__in': accessible_accounts}
    return queryset.filter(**filter_kwargs)