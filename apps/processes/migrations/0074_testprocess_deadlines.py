from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0073_testinvitation_email_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="testprocess",
            name="project_deadline",
            field=models.DateTimeField(
                blank=True,
                help_text="Optional fixed date and time for the invitation email deadline.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="testprocess",
            name="candidate_deadline_days",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Optional number of days from sending the invitation.",
                null=True,
            ),
        ),
    ]
