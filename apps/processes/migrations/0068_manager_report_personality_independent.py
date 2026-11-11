from django.db import migrations, models


def copy_legacy_manager_report_personality(apps, schema_editor):
    for model_name in ("TestInvitation", "HistoricalProcessCandidate"):
        Model = apps.get_model("processes", model_name)
        for owner in Model.objects.all().iterator():
            saved = owner.ai_personality_interpretation or {}
            report = saved.get("manager_report_personality")
            if not isinstance(report, dict) or not report:
                continue
            owner.ai_manager_report_personality = report
            owner.ai_manager_report_personality_status = (
                "completed"
                if saved.get("manager_report_personality_schema_version") == 1
                else "outdated"
            )
            owner.ai_manager_report_personality_generated_at = (
                owner.ai_personality_interpretation_generated_at
            )
            owner.ai_manager_report_personality_purpose = (
                owner.ai_personality_interpretation_purpose
            )
            owner.save(update_fields=[
                "ai_manager_report_personality",
                "ai_manager_report_personality_status",
                "ai_manager_report_personality_generated_at",
                "ai_manager_report_personality_purpose",
            ])


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0067_pinnedproject_sort_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="ai_manager_report_personality",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="testinvitation",
            name="ai_manager_report_personality_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("not_started", "Not started"),
                    ("generating", "Generating"),
                    ("completed", "Completed"),
                    ("outdated", "Outdated"),
                    ("failed", "Failed"),
                ],
                default="not_started",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="testinvitation",
            name="ai_manager_report_personality_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="testinvitation",
            name="ai_manager_report_personality_purpose",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="historicalprocesscandidate",
            name="ai_manager_report_personality",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="historicalprocesscandidate",
            name="ai_manager_report_personality_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("not_started", "Not started"),
                    ("generating", "Generating"),
                    ("completed", "Completed"),
                    ("outdated", "Outdated"),
                    ("failed", "Failed"),
                ],
                default="not_started",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="historicalprocesscandidate",
            name="ai_manager_report_personality_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalprocesscandidate",
            name="ai_manager_report_personality_purpose",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.RunPython(
            copy_legacy_manager_report_personality,
            migrations.RunPython.noop,
        ),
    ]
