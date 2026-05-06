from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0007_application_awaiting_physical"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicationStatusLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=50)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_logs",
                        to="programs.application",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="status_log_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "programs_applicationstatuslog",
                "ordering": ["changed_at"],
            },
        ),
    ]
