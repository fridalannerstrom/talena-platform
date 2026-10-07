from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("teams", "0003_team_created_by_team_org_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="goals",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="team",
            name="context",
            field=models.TextField(blank=True),
        ),
        migrations.CreateModel(
            name="TeamAIInsight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("insight_type", models.CharField(choices=[("communication_styles", "Communication styles"), ("collaboration", "Collaboration")], max_length=40)),
                ("language", models.CharField(choices=[("sv", "Swedish"), ("en", "English")], max_length=10)),
                ("content", models.TextField()),
                ("source_signature", models.CharField(max_length=64)),
                ("source_metadata", models.JSONField(blank=True, default=dict)),
                ("prompt_key", models.CharField(max_length=100)),
                ("prompt_revision", models.CharField(blank=True, max_length=100)),
                ("prompt_digest", models.CharField(max_length=64)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                ("generated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_team_insights", to=settings.AUTH_USER_MODEL)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_insights", to="teams.team")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("team", "insight_type", "language"), name="unique_team_ai_insight_type_language")],
            },
        ),
    ]
