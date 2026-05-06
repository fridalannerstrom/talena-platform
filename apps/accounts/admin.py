from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Profile, Company, CompanyMember, OrgUnit, UserOrgUnitAccess, UserInvite
from django.utils.html import format_html

User = get_user_model()


def _user_access_accessor_name() -> str:
    """
    Returnerar rätt reverse-accessor från User -> UserOrgUnitAccess
    oavsett om du har related_name eller inte.
    Ex:
      - related_name="orgunit_accesses" => "orgunit_accesses"
      - ingen related_name              => "userorgunitaccess_set"
    """
    f = UserOrgUnitAccess._meta.get_field("user")
    rn = f.remote_field.related_name
    if rn:
        return rn
    # default när related_name saknas:
    return f"{UserOrgUnitAccess._meta.model_name}_set"


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
        "orgunit_info",
    )
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Prefetch med RÄTT reverse accessor + org_unit
        return qs.prefetch_related(f"{ACCESSOR}__org_unit")

    def orgunit_info(self, obj):
        rel = getattr(obj, ACCESSOR, None)

        # OneToOne: rel är ett objekt (eller None)
        if rel and not hasattr(rel, "all"):
            access = rel
        else:
            # FK/M2M-liknande manager
            access = rel.select_related("org_unit").first() if rel else None

        if access and getattr(access, "org_unit", None):
            return format_html('<span style="color:#059669;">{}</span>', access.org_unit.name)

        # ✅ Viktigt: format_html måste få minst ett arg/kwarg
        return format_html('<span style="color:#dc2626;">{}</span>', "Ingen enhet")

    orgunit_info.short_description = "Org unit"


# =============================================================================
# ORG UNIT ADMIN
# =============================================================================

@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ("hierarchical_name", "company", "unit_code", "parent", "level", "created_at")
    list_filter = ("company", "parent", "created_at")
    search_fields = ("name", "unit_code", "company__name")
    autocomplete_fields = ("company", "parent")
    readonly_fields = ("created_at", "updated_at", "level", "full_path")

    def hierarchical_name(self, obj):
        indent = "—" * (obj.level or 0)
        return format_html("{} {}", indent, obj.name)

    hierarchical_name.short_description = "Name"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("parent")


# =============================================================================
# USER ORG UNIT ACCESS ADMIN
# =============================================================================

@admin.register(UserOrgUnitAccess)
class UserOrgUnitAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "org_unit", "created_at")
    list_filter = ("org_unit", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "org_unit__name")
    autocomplete_fields = ("user", "org_unit")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "org_unit")

# =============================================================================
# COMPANY ADMIN
# =============================================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "org_number", "member_count", "orgunit_count", "created_at", "updated_at")
    search_fields = ("name", "org_number")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    def member_count(self, obj):
        return obj.memberships.count()

    member_count.short_description = "Members"

    def orgunit_count(self, obj):
        return obj.org_units.count()

    orgunit_count.short_description = "Org units"


# =============================================================================
# COMPANY MEMBER ADMIN
# =============================================================================

@admin.register(CompanyMember)
class CompanyMemberAdmin(admin.ModelAdmin):
    list_display = ("company", "user", "role", "primary_org_unit", "created_at")
    list_filter = ("company", "role")
    search_fields = (
        "company__name",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    autocomplete_fields = ("company", "user", "primary_org_unit")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("company", "user", "primary_org_unit")


# =============================================================================
# USER INVITE ADMIN
# =============================================================================

@admin.register(UserInvite)
class UserInviteAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "created_by", "created_at", "accepted_at", "revoked_at")
    list_filter = ("company", "accepted_at", "revoked_at")
    search_fields = (
        "user__email",
        "company__name",
        "created_by__email",
    )
    autocomplete_fields = ("user", "company", "created_by")
    readonly_fields = ("id", "created_at", "accepted_at", "revoked_at")