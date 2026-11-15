from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0069_project_completion_email"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="pinnedproject",
            options={"ordering": ["sort_order", "-created_at", "-pk"]},
        ),
    ]
