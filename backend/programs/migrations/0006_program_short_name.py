from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0005_program_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='short_name',
            field=models.CharField(
                blank=True,
                max_length=32,
                help_text='Short label used on buttons, pills, and dashboards (e.g. SINAG, SPARK).',
            ),
        ),
    ]
