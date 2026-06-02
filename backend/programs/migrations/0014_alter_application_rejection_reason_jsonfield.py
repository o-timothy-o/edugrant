from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0013_application_rejection_reason'),
    ]

    operations = [
        # Step 1: normalise all existing values to valid JSON arrays
        # - empty / NULL         → []
        # - already a JSON array → leave as-is
        # - plain string value   → wrap into ["value"]
        migrations.RunSQL(
            sql="""
                UPDATE programs_application
                SET rejection_reason = CASE
                    WHEN rejection_reason IS NULL OR rejection_reason = ''
                        THEN '[]'
                    WHEN rejection_reason LIKE '[%'
                        THEN rejection_reason
                    ELSE '["' || rejection_reason || '"]'
                END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Step 2: cast the column to jsonb in the database
        migrations.RunSQL(
            sql="ALTER TABLE programs_application ALTER COLUMN rejection_reason TYPE jsonb USING rejection_reason::jsonb",
            reverse_sql="ALTER TABLE programs_application ALTER COLUMN rejection_reason TYPE varchar(32) USING rejection_reason::text",
        ),
        # Step 3: update Django's internal state to match (no DB change)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='application',
                    name='rejection_reason',
                    field=models.JSONField(blank=True, default=list),
                ),
            ],
            database_operations=[],
        ),
    ]
