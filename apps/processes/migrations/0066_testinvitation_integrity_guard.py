from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0065_candidate_project_removal"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="integrity_guard",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
