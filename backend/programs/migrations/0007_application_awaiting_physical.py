from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0006_program_short_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Submitted'),
                    ('for_review', 'For Review'),
                    ('approved', 'Approved'),
                    ('awaiting_physical', 'Approved \u2013 Awaiting Physical Submission'),
                    ('rejected', 'Rejected'),
                ],
                default='draft',
                max_length=32,
            ),
        ),
    ]
