import re

from django.db import migrations


_CREDENTIAL_RE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9_-])")
_CODE_RE = re.compile(r"(?<!\d)\d{6}(?!\d)")


def _redact(value):
    value = value or ""
    value = _CREDENTIAL_RE.sub("[redacted candidate result credential]", value)
    return _CODE_RE.sub("[redacted verification code]", value)


def redact_candidate_result_logs(apps, schema_editor):
    EmailLog = apps.get_model("emails", "EmailLog")
    database = schema_editor.connection.alias

    logs = (
        EmailLog.objects.using(database)
        .filter(template_type="candidate_result")
        .only("id", "body_snapshot", "error")
    )
    for email_log in logs.iterator():
        body_snapshot = _redact(email_log.body_snapshot)
        error = _redact(email_log.error)
        if body_snapshot != (email_log.body_snapshot or "") or error != (email_log.error or ""):
            EmailLog.objects.using(database).filter(pk=email_log.pk).update(
                body_snapshot=body_snapshot,
                error=error,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            redact_candidate_result_logs,
            migrations.RunPython.noop,
        ),
    ]
