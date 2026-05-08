from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_emailverification'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicantprofile',
            name='full_name',
        ),
        migrations.AddField(
            model_name='applicantprofile',
            name='first_name',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='applicantprofile',
            name='middle_name',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='applicantprofile',
            name='last_name',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
