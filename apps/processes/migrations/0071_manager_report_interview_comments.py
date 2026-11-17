from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0070_alter_pinnedproject_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="ai_manager_report_interview_comments",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="historicalprocesscandidate",
            name="ai_manager_report_interview_comments",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
