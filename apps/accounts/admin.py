from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Visa fler kolumner i listan
    list_display = ("username", "email", "role", "is_staff", "is_superuser", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")

    # Lägg role i edit-formen i admin
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Talena", {"fields": ("role",)}),
    )