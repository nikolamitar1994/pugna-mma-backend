# Generated migration to simplify fight methods
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fighters', '0004_add_unique_constraints'),
    ]

    operations = [
        # Add the new method_description field
        migrations.AddField(
            model_name='fighthistory',
            name='method_description',
            field=models.CharField(
                blank=True, 
                max_length=255, 
                help_text="Detailed method description (e.g., 'rear naked choke', 'unanimous', 'head kick and punches')"
            ),
        ),
        
        # We'll handle the method field choice changes in the next migration
        # after we migrate the data
    ]