from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0009_candidate_result_access_one_year"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidateresultsnapshot",
            name="content_version",
            field=models.CharField(
                default="candidate-static-v5",
                help_text="Version of the approved candidate-facing content library.",
                max_length=32,
            ),
        ),
    ]
