from django.db import models


class ProjectMeta(models.Model):
    # Koppling till SOVA
    provider = models.CharField(max_length=50, default="sova")
    account_code = models.CharField(max_length=255)
    project_code = models.CharField(max_length=255)

    # Din egna info
    intern_name = models.TextField(blank=True, default="")
    tests = models.TextField(blank=True, default="")      # ["Personlighet", "Kognitivt"]
    languages = models.TextField(blank=True, default="")   # ["sv", "en"]
    notes = models.TextField(blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "account_code", "project_code")

    def __str__(self):
        return f"{self.provider}:{self.account_code}:{self.project_code}"
    
