from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "processes",
            "0061_merge_0060_interviewquestionnote_0060_processautomationsettings",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="testprocess",
            name="candidate_results_enabled",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Allow candidates to access a simplified result after all "
                    "required assessments are completed."
                ),
                verbose_name="Candidate results enabled",
            ),
        ),
    ]
