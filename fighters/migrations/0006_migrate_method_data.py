# Data migration to transform existing method data to simplified format
from django.db import migrations


def migrate_method_data(apps, schema_editor):
    """
    Migrate existing method data to simplified format
    """
    FightHistory = apps.get_model('fighters', 'FightHistory')
    
    # Mapping from old method values to new (method, description) format
    method_mapping = {
        # Knockout variants -> KO with descriptions
        'ko': ('ko', ''),
        'tko': ('tko', ''),
        'tko_punches': ('tko', 'punches'),
        'tko_kicks': ('tko', 'kicks'),
        'tko_knees': ('tko', 'knees'),
        'tko_elbows': ('tko', 'elbows'),
        'tko_injury': ('tko', 'injury'),
        'tko_retirement': ('tko', 'retirement'),
        'tko_corner_stoppage': ('tko', 'corner stoppage'),
        'tko_doctor_stoppage': ('tko', 'doctor stoppage'),
        
        # Submission variants -> Submission with descriptions
        'submission': ('submission', ''),
        'submission_rear_naked_choke': ('submission', 'rear naked choke'),
        'submission_guillotine': ('submission', 'guillotine choke'),
        'submission_triangle': ('submission', 'triangle choke'),
        'submission_armbar': ('submission', 'armbar'),
        'submission_kimura': ('submission', 'kimura'),
        'submission_americana': ('submission', 'americana'),
        'submission_ankle_lock': ('submission', 'ankle lock'),
        'submission_heel_hook': ('submission', 'heel hook'),
        'submission_other': ('submission', 'other'),
        
        # Decision variants -> Decision with descriptions
        'decision_unanimous': ('decision', 'unanimous'),
        'decision_majority': ('decision', 'majority'),
        'decision_split': ('decision', 'split'),
        
        # Special cases - keep as separate methods for now, we'll handle these differently
        'disqualification': ('disqualification', ''),
        'forfeit': ('forfeit', ''),
        'technical_decision': ('decision', 'technical decision'),
        'no_contest': ('no_contest', ''),
        'other': ('other', ''),
    }
    
    # Update all fight history records
    updated_count = 0
    for fight in FightHistory.objects.all():
        if fight.method in method_mapping:
            new_method, description = method_mapping[fight.method]
            
            # Store the description in the new field
            fight.method_description = description
            
            # For now, keep the original method - we'll change the choices in the next migration
            # This ensures we don't lose data if there are any unmapped methods
            
            fight.save(update_fields=['method_description'])
            updated_count += 1
    
    print(f"Updated {updated_count} fight history records with method descriptions")


def reverse_migrate_method_data(apps, schema_editor):
    """
    Reverse migration - reconstruct original method values from simplified format
    """
    FightHistory = apps.get_model('fighters', 'FightHistory')
    
    # Reverse mapping to reconstruct original method values
    reverse_mapping = {
        ('ko', ''): 'ko',
        ('tko', ''): 'tko',
        ('tko', 'punches'): 'tko_punches',
        ('tko', 'kicks'): 'tko_kicks',
        ('tko', 'knees'): 'tko_knees',
        ('tko', 'elbows'): 'tko_elbows',
        ('tko', 'injury'): 'tko_injury',
        ('tko', 'retirement'): 'tko_retirement',
        ('tko', 'corner stoppage'): 'tko_corner_stoppage',
        ('tko', 'doctor stoppage'): 'tko_doctor_stoppage',
        
        ('submission', ''): 'submission',
        ('submission', 'rear naked choke'): 'submission_rear_naked_choke',
        ('submission', 'guillotine choke'): 'submission_guillotine',
        ('submission', 'triangle choke'): 'submission_triangle',
        ('submission', 'armbar'): 'submission_armbar',
        ('submission', 'kimura'): 'submission_kimura',
        ('submission', 'americana'): 'submission_americana',
        ('submission', 'ankle lock'): 'submission_ankle_lock',
        ('submission', 'heel hook'): 'submission_heel_hook',
        ('submission', 'other'): 'submission_other',
        
        ('decision', 'unanimous'): 'decision_unanimous',
        ('decision', 'majority'): 'decision_majority',
        ('decision', 'split'): 'decision_split',
        ('decision', 'technical decision'): 'technical_decision',
        
        ('disqualification', ''): 'disqualification',
        ('forfeit', ''): 'forfeit',
        ('no_contest', ''): 'no_contest',
        ('other', ''): 'other',
    }
    
    # Reconstruct original method values
    for fight in FightHistory.objects.all():
        key = (fight.method, fight.method_description or '')
        if key in reverse_mapping:
            fight.method = reverse_mapping[key]
            fight.save(update_fields=['method'])


class Migration(migrations.Migration):

    dependencies = [
        ('fighters', '0005_simplify_fight_methods'),
    ]

    operations = [
        migrations.RunPython(migrate_method_data, reverse_migrate_method_data),
    ]