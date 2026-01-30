from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Visa fler kolumner i listan
    list_display = ("username", "email", "is_staff", "is_superuser", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")

# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Profile, Account, UserAccountAccess


# ============================================================================
# USER & PROFILE ADMIN
# ============================================================================

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_staff', 'account_info']
    list_filter = ['is_staff', 'is_active']
    
    def account_info(self, obj):
        try:
            access = obj.account_access
            return format_html(
                '<span style="color: #059669;">{}</span>',
                access.account.name
            )
        except UserAccountAccess.DoesNotExist:
            return format_html('<span style="color: #dc2626;">Inget konto</span>')
    account_info.short_description = 'Account'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ============================================================================
# ACCOUNT ADMIN
# ============================================================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['hierarchical_name', 'account_code', 'parent', 'level', 'created_at']
    list_filter = ['parent', 'created_at']
    search_fields = ['name', 'account_code']
    readonly_fields = ['created_at', 'updated_at', 'level', 'full_path']
    
    fieldsets = (
        ('Grundinfo', {
            'fields': ('name', 'account_code', 'parent')
        }),
        ('Hierarki', {
            'fields': ('level', 'full_path'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def hierarchical_name(self, obj):
        """Visa indenterat namn baserat på nivå"""
        indent = '—' * obj.level
        return format_html('{} {}', indent, obj.name)
    hierarchical_name.short_description = 'Name'
    
    def get_queryset(self, request):
        """Optimera queryset med prefetch"""
        qs = super().get_queryset(request)
        return qs.select_related('parent')


# ============================================================================
# USER ACCOUNT ACCESS ADMIN
# ============================================================================

@admin.register(UserAccountAccess)
class UserAccountAccessAdmin(admin.ModelAdmin):
    list_display = ['user', 'account', 'created_at']
    list_filter = ['account', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'account__name']
    autocomplete_fields = ['user', 'account']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'account',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimera queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'account')