from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0005_candidate_du_copy_version"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidateresultsnapshot",
            name="prompt_versions",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Legacy prompt metadata; empty for static candidate reports.",
            ),
        ),
    ]
