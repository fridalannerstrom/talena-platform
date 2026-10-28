from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0064_manager_report_text_edit"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="integrity_guard",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
