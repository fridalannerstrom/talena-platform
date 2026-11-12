from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("processes", "0063_pinnedproject"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManagerReportTextEdit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("block_key", models.CharField(max_length=100)),
                ("language_code", models.CharField(max_length=2)),
                ("text", models.TextField(blank=True, default="", max_length=30000)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_report_text_edits", to="processes.candidate")),
                ("process", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_report_text_edits", to="processes.testprocess")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="manager_report_text_edits_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["block_key", "language_code"]},
        ),
        migrations.CreateModel(
            name="ManagerReportTextEditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("block_key", models.CharField(max_length=100)),
                ("language_code", models.CharField(max_length=2)),
                ("action", models.CharField(choices=[("saved", "Text saved"), ("restored_ai", "AI text restored")], max_length=24)),
                ("version", models.PositiveIntegerField()),
                ("source_generated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="manager_report_text_edit_events", to=settings.AUTH_USER_MODEL)),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_report_text_edit_events", to="processes.candidate")),
                ("process", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_report_text_edit_events", to="processes.testprocess")),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="managerreporttextedit",
            constraint=models.UniqueConstraint(fields=("process", "candidate", "block_key", "language_code"), name="uniq_manager_report_text_edit"),
        ),
        migrations.AddIndex(
            model_name="managerreporttextedit",
            index=models.Index(fields=["process", "candidate", "language_code"], name="mgr_rpt_edit_lookup_idx"),
        ),
        migrations.AddIndex(
            model_name="managerreporttexteditevent",
            index=models.Index(fields=["process", "candidate", "-created_at"], name="mgr_rpt_edit_event_idx"),
        ),
    ]
