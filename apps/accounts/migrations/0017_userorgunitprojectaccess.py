# Generated for per-unit project visibility scopes.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_user_role"),
        ("processes", "0028_remove_historicalcandidatereport_invitation_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserOrgUnitProjectAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("org_unit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_project_accesses", to="accounts.orgunit")),
                ("projects", models.ManyToManyField(blank=True, related_name="user_orgunit_project_accesses", to="processes.testprocess")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orgunit_project_accesses", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("user", "org_unit"), name="uniq_user_orgunit_project_scope"),
                ],
            },
        ),
    ]
