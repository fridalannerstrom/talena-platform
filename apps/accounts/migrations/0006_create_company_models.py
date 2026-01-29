from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="Företagsnamn")),
                ("org_number", models.CharField(blank=True, max_length=30, null=True, verbose_name="Organisationsnummer")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name": "Company",
                "verbose_name_plural": "Companies",
            },
        ),
        migrations.CreateModel(
            name="CompanyMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("admin", "Admin"), ("member", "Member"), ("viewer", "Viewer")], default="member", max_length=20, verbose_name="Roll")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="memberships", to="accounts.company", verbose_name="Företag")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="company_memberships", to=settings.AUTH_USER_MODEL, verbose_name="Användare")),
            ],
            options={
                "verbose_name": "Company member",
                "verbose_name_plural": "Company members",
                "unique_together": {("company", "user")},
            },
        ),
    ]
