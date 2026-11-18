"""Company-wide display preference for Sova Integrity Guard in Talena only."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0018_companybranding")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="integrity_guard_visible",
            field=models.BooleanField(
                default=True,
                verbose_name="Visa Integrity Guard i Talena",
                help_text="Döljer endast Integrity Guard i Talenas gränssnitt, inte i Sova.",
            ),
        ),
    ]
