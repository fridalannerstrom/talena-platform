# Ticket #182: isolated report branding per company.
import django.db.models.deletion
import apps.accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0017_company_migration_onboarding_enabled_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyBranding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("logo", models.ImageField(blank=True, upload_to=apps.accounts.models.company_brand_asset_path)),
                ("cover_image", models.ImageField(blank=True, upload_to=apps.accounts.models.company_brand_asset_path)),
                ("primary_color", models.CharField(default="#FF6F61", help_text="Primary HEX colour for PDF/report accents.", max_length=7)),
                ("cover_focus_y", models.PositiveSmallIntegerField(default=50, help_text="Vertical cover-image focal point (0–100%).")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="report_branding", to="accounts.company")),
            ],
        ),
    ]
