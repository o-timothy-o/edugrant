from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0008_applicationstatuslog"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="application",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
    ]
