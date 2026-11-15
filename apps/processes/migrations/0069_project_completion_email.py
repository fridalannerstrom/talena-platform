from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0068_manager_report_personality_independent"),
    ]

    operations = [
        migrations.AddField(
            model_name="testprocess",
            name="project_completion_notifications_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="testinvitation",
            name="project_completion_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
