import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("candidate_results", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateResultFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "result_area",
                    models.CharField(
                        choices=[
                            ("personality", "Personality"),
                            ("skills", "Skills"),
                            ("motivation", "Motivation"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "response",
                    models.CharField(
                        choices=[
                            ("recognises", "I recognise myself"),
                            ("partly_recognises", "I partly recognise myself"),
                            ("does_not_recognise", "I do not recognise myself"),
                        ],
                        max_length=32,
                    ),
                ),
                ("comment", models.TextField(blank=True, max_length=2000)),
                ("locale", models.CharField(default="sv", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="candidate_results.candidateresultsnapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["result_area"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("snapshot", "result_area"),
                        name="cand_feedback_snap_area_uniq",
                    ),
                ],
            },
        ),
    ]
