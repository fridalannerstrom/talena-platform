from django.db import migrations
from django.db.models import Q


def set_historical_process_purpose(apps, schema_editor):
    TestProcess = apps.get_model(
        "processes",
        "TestProcess",
    )

    (
        TestProcess.objects
        .filter(
            is_historical=True,
        )
        .filter(
            Q(purpose="")
            | Q(purpose__isnull=True)
        )
        .update(
            purpose="unsure"
        )
    )


def reverse_historical_process_purpose(
    apps,
    schema_editor,
):
    # Intentionally do nothing.
    # We cannot know which historical processes originally
    # had a deliberately selected purpose.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0053_testprocess_candidate_language'),
    ]

    operations = [
    ]

    operations = [
        migrations.RunPython(
            set_historical_process_purpose,
            reverse_historical_process_purpose,
        ),
    ]