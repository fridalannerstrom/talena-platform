from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0071_manager_report_interview_comments"),
    ]

    operations = [
        migrations.AddField(
            model_name="testprocess",
            name="integrity_guard_visible_override",
            field=models.BooleanField(
                blank=True,
                default=None,
                help_text="Optional project-level override for Talena's Integrity Guard display.",
                null=True,
            ),
        ),
    ]
