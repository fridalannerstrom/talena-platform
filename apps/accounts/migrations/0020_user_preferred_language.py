"""Persist a user's Talena interface language without changing older browser preferences."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0019_company_integrity_guard_visible"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(
                max_length=2,
                choices=[
                    ("", "Automatiskt (webbläsare)"),
                    ("sv", "Svenska"),
                    ("en", "English"),
                ],
                blank=True,
                default="",
                verbose_name="Språk i Talena",
            ),
        ),
    ]
