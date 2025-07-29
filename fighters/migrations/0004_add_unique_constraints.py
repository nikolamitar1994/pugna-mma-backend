# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fighters', '0003_add_interconnected_network'),
    ]

    operations = [
        # Add unique constraint to prevent duplicate fighters
        migrations.AlterUniqueTogether(
            name='fighter',
            unique_together={('first_name', 'last_name', 'date_of_birth')},
        ),
        
        # Add index for better performance on name lookups
        migrations.AddIndex(
            model_name='fighter',
            index=models.Index(fields=['first_name', 'last_name'], name='idx_fighter_full_name'),
        ),
    ]