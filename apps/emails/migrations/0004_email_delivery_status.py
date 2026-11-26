from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0003_companyinvitationtemplate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emaillog",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("sent", "Accepted by email service"),
                    ("failed", "Send failed"),
                ],
                default="queued",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="internet_message_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="delivery_status",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("pending", "Pending"),
                    ("delivered", "Delivered"),
                    ("failed", "Could not be delivered"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="delivery_status_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="delivery_error_code",
            field=models.CharField(blank=True, default="", max_length=60),
        ),
        migrations.CreateModel(
            name="EmailDeliveryUpdate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("provider_event_id", models.CharField(max_length=255, unique=True)),
                ("provider_status", models.CharField(max_length=40)),
                (
                    "delivery_status",
                    models.CharField(
                        choices=[
                            ("unknown", "Unknown"),
                            ("pending", "Pending"),
                            ("delivered", "Delivered"),
                            ("failed", "Could not be delivered"),
                        ],
                        max_length=20,
                    ),
                ),
                ("provider_occurred_at", models.DateTimeField(blank=True, null=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                (
                    "email_log",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery_updates",
                        to="emails.emaillog",
                    ),
                ),
            ],
            options={
                "ordering": ["received_at", "pk"],
            },
        ),
    ]
