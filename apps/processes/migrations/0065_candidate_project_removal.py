from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0064_manager_report_text_edit"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="removed_from_process_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="testinvitation",
            name="sova_revocation_state",
            field=models.CharField(
                choices=[
                    ("not_required", "No Sova access to revoke"),
                    ("manual_pending", "Sova revocation requires manual verification"),
                    ("confirmed", "Sova access revocation manually verified"),
                ],
                default="not_required",
                max_length=24,
            ),
        ),
    ]
