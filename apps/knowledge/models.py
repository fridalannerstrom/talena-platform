from django.db import models
from django.conf import settings


class KnowledgeEntry(models.Model):
    BASE = "base"
    TQ = "tq"

    KNOWLEDGE_TYPE_CHOICES = [
        (BASE, "Base"),
        (TQ, "TQ-expert"),
    ]

    knowledge_type = models.CharField(
        max_length=20,
        choices=KNOWLEDGE_TYPE_CHOICES,
        default=BASE,
    )

    title = models.CharField(max_length=255)
    content = models.TextField()

    # För filtrering/ordning i framtiden (valfritt men bra)
    tags = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(max_length=255, blank=True, default="admin")

    # Pinecone tracking
    pinecone_namespace = models.CharField(max_length=255, blank=True, default="")
    pinecone_ids = models.JSONField(blank=True, null=True)  # lista av chunk-ids

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    indexed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title