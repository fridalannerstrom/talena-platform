from django.contrib import admin
from .models import KnowledgeEntry


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "knowledge_type", "source", "indexed_at", "updated_at")
    list_filter = ("knowledge_type", "source")
    search_fields = ("title", "content")