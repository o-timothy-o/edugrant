from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0012_increase_document_file_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='rejection_reason',
            field=models.CharField(
                blank=True,
                choices=[
                    ('income', 'Income exceeds program limit'),
                    ('residency', 'Does not meet residency requirement'),
                    ('not_enrolled', 'Not currently enrolled'),
                    ('incomplete', 'Incomplete or invalid documents'),
                    ('other', 'Other'),
                ],
                default='',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='application',
            name='rejection_reason_other',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
