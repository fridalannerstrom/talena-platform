from django.db import migrations, models


def retire_candidate_result_prompts(apps, schema_editor):
    prompt_model = apps.get_model("processes", "AIPromptTemplate")
    prompt_model.objects.filter(key__startswith="candidate_result_").update(
        is_active=False,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0003_candidatetestexperiencefeedback"),
        ("processes", "0063_pinnedproject"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidateresultsnapshot",
            name="content_version",
            field=models.CharField(
                default="ai-v1",
                help_text="Version of the approved candidate-facing content library.",
                max_length=32,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="candidateresultsnapshot",
            name="legacy_content",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Archived candidate-facing content from a replaced legacy snapshot.",
            ),
        ),
        migrations.AddField(
            model_name="candidateresultsnapshot",
            name="legacy_prompt_versions",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Archived prompt metadata associated with legacy candidate content.",
            ),
        ),
        migrations.AlterField(
            model_name="candidateresultsnapshot",
            name="content_version",
            field=models.CharField(
                default="candidate-static-v1",
                help_text="Version of the approved candidate-facing content library.",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            retire_candidate_result_prompts,
            migrations.RunPython.noop,
        ),
    ]
