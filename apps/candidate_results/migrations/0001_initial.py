import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        (
            "processes",
            "0062_testprocess_candidate_results_enabled",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="CandidateResultSnapshot",
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
                    "locale",
                    models.CharField(default="sv", max_length=10),
                ),
                (
                    "content",
                    models.JSONField(
                        default=dict,
                        help_text="Frozen candidate-facing content.",
                    ),
                ),
                (
                    "prompt_versions",
                    models.JSONField(
                        default=dict,
                        help_text=(
                            "Prompt/version metadata used to create the content."
                        ),
                    ),
                ),
                (
                    "source_fingerprint",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text=(
                            "Optional fingerprint of the assessment evidence used."
                        ),
                        max_length=64,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "candidate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_result_snapshots",
                        to="processes.candidate",
                    ),
                ),
                (
                    "invitation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_result_snapshot",
                        to="processes.testinvitation",
                    ),
                ),
                (
                    "process",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="candidate_result_snapshots",
                        to="processes.testprocess",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["process", "candidate"],
                        name="candidate_r_process_5c0b8b_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="CandidateResultAccess",
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
                    "token_digest",
                    models.CharField(
                        db_index=True,
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "verification_code_hash",
                    models.CharField(max_length=128),
                ),
                (
                    "locale",
                    models.CharField(default="sv", max_length=10),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "last_accessed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "revoked_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "verification_failed_attempts",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "last_verification_failed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "locked_until",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "snapshot",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access",
                        to="candidate_results.candidateresultsnapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["expires_at"],
                        name="candidate_r_expires_4d17a0_idx",
                    ),
                    models.Index(
                        fields=["revoked_at"],
                        name="candidate_r_revoked_5f25ea_idx",
                    ),
                ],
            },
        ),
    ]
