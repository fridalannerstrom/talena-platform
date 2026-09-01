from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0059_refine_post_interview_hierarchy_prompts"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProcessAutomationSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "automatic_invitation_enabled",
                    models.BooleanField(default=False),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "process",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_settings",
                        to="processes.testprocess",
                    ),
                ),
            ],
            options={
                "verbose_name": "Process automation settings",
                "verbose_name_plural": "Process automation settings",
            },
        ),
    ]
