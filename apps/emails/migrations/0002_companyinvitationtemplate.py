# Ticket #87: company-wide invitation templates
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyInvitationTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(choices=[("sv", "Swedish"), ("en", "English")], default="sv", max_length=10)),
                ("subject", models.CharField(max_length=255)),
                ("body", models.TextField(help_text="Include {assessment_url} so the candidate receives the test link.")),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitation_email_templates", to="accounts.company")),
            ],
        ),
        migrations.AddConstraint(
            model_name="companyinvitationtemplate",
            constraint=models.UniqueConstraint(
                fields=("company", "language"),
                name="uniq_company_invitation_template_lang",
            ),
        ),
    ]
