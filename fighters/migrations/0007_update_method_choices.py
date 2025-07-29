# Migration to update method field choices to simplified format
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fighters', '0006_migrate_method_data'),
    ]

    operations = [
        # Update method data to use simplified choices
        migrations.RunSQL(
            sql=[
                # Update all TKO variants to just 'tko'
                "UPDATE fight_history SET method = 'tko' WHERE method LIKE 'tko_%';",
                
                # Update all submission variants to just 'submission'
                "UPDATE fight_history SET method = 'submission' WHERE method LIKE 'submission_%';",
                
                # Update all decision variants to just 'decision'
                "UPDATE fight_history SET method = 'decision' WHERE method LIKE 'decision_%';",
                "UPDATE fight_history SET method = 'decision' WHERE method = 'technical_decision';",
            ],
            reverse_sql=[
                # This reverse would be complex and is handled by the previous migration's reverse
                "-- Reverse handled by previous migration"
            ]
        ),
        
        # Update the field choices
        migrations.AlterField(
            model_name='fighthistory',
            name='method',
            field=models.CharField(
                blank=True, 
                choices=[
                    ('decision', 'Decision'), 
                    ('ko', 'KO'), 
                    ('tko', 'TKO'), 
                    ('submission', 'Submission'), 
                    ('disqualification', 'Disqualification'), 
                    ('forfeit', 'Forfeit'), 
                    ('no_contest', 'No Contest'), 
                    ('other', 'Other')
                ], 
                max_length=50
            ),
        ),
    ]