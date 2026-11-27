# Generated for the new-account permission default.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_user_preferred_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userorgunitaccess",
            name="permission",
            field=models.CharField(
                choices=[
                    ("viewer", "Viewer"),
                    ("editor", "Editor"),
                    ("own", "Own only"),
                ],
                default="editor",
                max_length=10,
            ),
        ),
    ]
