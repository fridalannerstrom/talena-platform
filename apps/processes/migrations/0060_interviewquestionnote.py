from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processes", "0059_refine_post_interview_hierarchy_prompts"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewQuestionNote",
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
                    "source",
                    models.CharField(
                        choices=[
                            ("personality", "Personality"),
                            ("motivation", "Motivation"),
                            ("cognitive", "Cognitive"),
                        ],
                        max_length=24,
                    ),
                ),
                ("question_key", models.CharField(max_length=64)),
                ("question_text", models.TextField()),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "candidate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interview_question_notes",
                        to="processes.candidate",
                    ),
                ),
                (
                    "process",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interview_question_notes",
                        to="processes.testprocess",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interview_question_notes_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["source", "created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="interviewquestionnote",
            constraint=models.UniqueConstraint(
                fields=(
                    "process",
                    "candidate",
                    "source",
                    "question_key",
                ),
                name="uniq_interview_question_note",
            ),
        ),
        migrations.AddIndex(
            model_name="interviewquestionnote",
            index=models.Index(
                fields=["process", "candidate", "source"],
                name="interview_note_lookup_idx",
            ),
        ),
    ]
