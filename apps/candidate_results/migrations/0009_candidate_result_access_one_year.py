from datetime import timedelta

from django.db import migrations


def extend_existing_access_to_one_year(apps, schema_editor):
    CandidateResultAccess = apps.get_model(
        "candidate_results",
        "CandidateResultAccess",
    )
    database = schema_editor.connection.alias
    accesses = (
        CandidateResultAccess.objects.using(database)
        .filter(revoked_at__isnull=True)
        .only("id", "created_at", "expires_at")
    )

    for access in accesses.iterator():
        if access.expires_at is None:
            one_year_after_last_issue = access.created_at + timedelta(days=365)
        else:
            # Before this migration, both initial issuance and a resend set a
            # 30-day lifetime. Extending the existing expiry by 335 days keeps
            # the one-year window anchored to the latest credential rotation.
            one_year_after_last_issue = access.expires_at + timedelta(days=335)
        CandidateResultAccess.objects.using(database).filter(
            pk=access.pk,
        ).update(expires_at=one_year_after_last_issue)


class Migration(migrations.Migration):
    dependencies = [
        ("candidate_results", "0008_candidate_static_v4"),
    ]

    operations = [
        migrations.RunPython(
            extend_existing_access_to_one_year,
            migrations.RunPython.noop,
        ),
    ]
