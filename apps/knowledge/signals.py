from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import KnowledgeEntry
from apps.core.ai.ingest import upsert_document


@receiver(post_save, sender=KnowledgeEntry)
def index_knowledge_entry(sender, instance: KnowledgeEntry, created, **kwargs):
    # Guard: om vi precis satte indexed_at, indexera inte igen
    if instance.indexed_at and (timezone.now() - instance.indexed_at).total_seconds() < 3:
        return

    ids = upsert_document(
        title=instance.title,
        text=instance.content,
        source=instance.source,
        tags=instance.tags,
        namespace=instance.pinecone_namespace or "",
        doc_id=f"knowledge-{instance.id}",
        kind=instance.knowledge_type,
    )

    KnowledgeEntry.objects.filter(pk=instance.pk).update(
        pinecone_ids=ids,
        indexed_at=timezone.now()
    )