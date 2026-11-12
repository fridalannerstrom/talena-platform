from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processes", "0062_testprocess_candidate_results_enabled"),
    ]

    operations = [
        migrations.CreateModel(
            name="PinnedProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("process", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pins", to="processes.testprocess")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pinned_projects", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="pinnedproject",
            constraint=models.UniqueConstraint(fields=("user", "process"), name="unique_pinned_project_per_user"),
        ),
    ]
