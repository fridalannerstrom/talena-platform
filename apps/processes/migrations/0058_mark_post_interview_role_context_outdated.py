from django.db import migrations


def mark_post_interview_results_outdated(apps, schema_editor):
    db_alias = schema_editor.connection.alias

    for model_name in (
        "TestInvitation",
        "HistoricalProcessCandidate",
    ):
        Model = apps.get_model(
            "processes",
            model_name,
        )

        (
            Model.objects
            .using(db_alias)
            .filter(
                ai_post_interview_decision_support_status="completed",
            )
            .exclude(
                ai_post_interview_decision_support={},
            )
            .update(
                ai_post_interview_decision_support_status="outdated",
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0057_refresh_post_interview_role_prompts"),
    ]

    operations = [
        migrations.RunPython(
            mark_post_interview_results_outdated,
            migrations.RunPython.noop,
        ),
    ]
