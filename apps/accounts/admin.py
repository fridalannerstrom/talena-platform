from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Profile, Account, UserAccountAccess

User = get_user_model()


def _user_access_accessor_name() -> str:
    """
    Returnerar rätt reverse-accessor från User -> UserAccountAccess
    oavsett om du har related_name eller inte.
    Ex:
      - related_name="account_access"  => "account_access"
      - ingen related_name             => "useraccountaccess_set"
    """
    f = UserAccountAccess._meta.get_field("user")
    rn = f.remote_field.related_name
    if rn:
        return rn
    # default när related_name saknas:
    return f"{UserAccountAccess._meta.model_name}_set"


ACCESSOR = _user_access_accessor_name()


# =============================================================================
# PROFILE INLINE
# =============================================================================

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"


# =============================================================================
# USER ADMIN
# =============================================================================

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "account_info",
    )
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Prefetch med RÄTT reverse accessor + account
        return qs.prefetch_related(f"{ACCESSOR}__account")

    def account_info(self, obj):
        """
        Visar första account-kopplingen (om flera).
        Fungerar både för FK (manager) och O2O (direktobjekt).
        """
        rel = getattr(obj, ACCESSOR, None)

        # OneToOne: rel är ett objekt (eller None)
        if rel and not hasattr(rel, "all"):
            access = rel
        else:
            # FK/M2M-liknande manager
            access = rel.select_related("account").first() if rel else None

        if access and getattr(access, "account", None):
            return format_html('<span style="color:#059669;">{}</span>', access.account.name)

        return format_html('<span style="color:#dc2626;">Inget konto</span>')

    account_info.short_description = "Account"


# =============================================================================
# ACCOUNT ADMIN
# =============================================================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("hierarchical_name", "account_code", "parent", "level", "created_at")
    list_filter = ("parent", "created_at")
    search_fields = ("name", "account_code")
    readonly_fields = ("created_at", "updated_at", "level", "full_path")

    def hierarchical_name(self, obj):
        indent = "—" * (obj.level or 0)
        return format_html("{} {}", indent, obj.name)

    hierarchical_name.short_description = "Name"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("parent")


# =============================================================================
# USER ACCOUNT ACCESS ADMIN
# =============================================================================

@admin.register(UserAccountAccess)
class UserAccountAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "account", "created_at")
    list_filter = ("account", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "account__name")
    autocomplete_fields = ("user", "account")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "account")
