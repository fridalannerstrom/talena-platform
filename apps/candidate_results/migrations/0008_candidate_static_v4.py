from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0007_candidate_personality_categories"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidateresultsnapshot",
            name="content_version",
            field=models.CharField(
                default="candidate-static-v4",
                help_text="Version of the approved candidate-facing content library.",
                max_length=32,
            ),
        ),
    ]
