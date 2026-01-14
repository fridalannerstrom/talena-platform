from django.contrib import admin
from .models import ProjectMeta


@admin.register(ProjectMeta)
class ProjectMetaAdmin(admin.ModelAdmin):
    list_display = ("provider", "account_code", "project_code", "updated_at")
    search_fields = ("account_code", "project_code")