import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0002_candidateresultfeedback"),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateTestExperienceFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")])),
                ("comment", models.TextField(blank=True, max_length=2000)),
                ("locale", models.CharField(default="sv", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("snapshot", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="test_experience_feedback", to="candidate_results.candidateresultsnapshot")),
            ],
        ),
    ]
