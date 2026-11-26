from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("processes", "0072_testprocess_integrity_guard_visible_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="testinvitation",
            name="email_override",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="Project-specific recipient address; does not change the shared candidate email.",
                max_length=254,
            ),
        ),
    ]
