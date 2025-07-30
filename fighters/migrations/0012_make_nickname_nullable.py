# Generated manually to fix nickname column constraint
# This migration makes the nickname field nullable in the database

from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('fighters', '0011_add_json_import_field'),
    ]

    operations = [
        # Make nickname field nullable in the database
        migrations.AlterField(
            model_name='fighter',
            name='nickname',
            field=models.CharField(
                blank=True, 
                null=True,  # Explicitly set null=True
                max_length=255, 
                help_text="Fighter nickname (e.g., 'Bones')"
            ),
        ),
    ]