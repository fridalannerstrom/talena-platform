from django.db import migrations, models


def preserve_existing_pin_order(apps, schema_editor):
    PinnedProject = apps.get_model("processes", "PinnedProject")
    database = schema_editor.connection.alias
    current_user_id = None
    position = 0

    pins = (
        PinnedProject.objects.using(database)
        .order_by("user_id", "-created_at", "-pk")
        .values_list("pk", "user_id")
    )

    for pin_id, user_id in pins.iterator():
        if user_id != current_user_id:
            current_user_id = user_id
            position = 0
        PinnedProject.objects.using(database).filter(pk=pin_id).update(
            sort_order=position
        )
        position += 1


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0066_testinvitation_integrity_guard"),
    ]

    operations = [
        migrations.AddField(
            model_name="pinnedproject",
            name="sort_order",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(
            preserve_existing_pin_order,
            migrations.RunPython.noop,
        ),
    ]
