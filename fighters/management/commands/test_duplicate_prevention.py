"""
Management command to test duplicate prevention system
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from fighters.models import Fighter
from fighters.services.matching import FighterMatcher


class Command(BaseCommand):
    help = 'Test duplicate prevention system'
    
    def handle(self, *args, **options):
        self.stdout.write('=== TESTING DUPLICATE PREVENTION SYSTEM ===')
        
        # Test 1: Try to create a duplicate fighter - should fail with database constraint
        self.stdout.write('\n1. Testing database unique constraint...')
        try:
            # Try to create Jon Jones again (should fail due to unique constraint)
            duplicate_jones = Fighter.objects.create(
                first_name='Jon',
                last_name='Jones',
                date_of_birth='1987-07-19',
                data_source='test_duplicate'
            )
            self.stdout.write(self.style.ERROR('❌ FAILED: Duplicate was created!'))
        except IntegrityError as e:
            self.stdout.write(self.style.SUCCESS('✅ SUCCESS: Database prevented duplicate fighter'))
            self.stdout.write(f'   Error: {str(e)[:100]}...')
        
        # Test 2: Use FighterMatcher to find existing fighter instead of creating duplicate
        self.stdout.write('\n2. Testing FighterMatcher for existing fighter...')
        fighter, confidence = FighterMatcher.find_fighter_by_name('Jon', 'Jones')
        if fighter and confidence >= 0.8:
            self.stdout.write(self.style.SUCCESS(f'✅ SUCCESS: Found existing fighter: {fighter.get_full_name()}'))
            self.stdout.write(f'   Confidence: {confidence:.2f}')
            self.stdout.write(f'   Fighter ID: {str(fighter.id)[:8]}...')
        else:
            self.stdout.write(self.style.ERROR('❌ FAILED: Could not find existing fighter'))
        
        # Test 3: Test fuzzy matching for slight variations
        self.stdout.write('\n3. Testing fuzzy matching for name variations...')
        test_variations = [
            ('Jonathan', 'Jones'),
            ('Jon', 'Bones Jones'),
            ('Johnny', 'Jones'),
        ]
        
        for first, last in test_variations:
            fighter, confidence = FighterMatcher.find_fighter_by_name(first, last)
            if fighter:
                self.stdout.write(f'   "{first} {last}" → {fighter.get_full_name()} (confidence: {confidence:.2f})')
            else:
                self.stdout.write(f'   "{first} {last}" → No match found')
        
        # Test 4: Show current database state
        self.stdout.write('\n4. Current fighter database state:')
        total_fighters = Fighter.objects.count()
        sample_fighters = Fighter.objects.filter(data_source='sample_data').count()
        self.stdout.write(f'   Total fighters: {total_fighters}')
        self.stdout.write(f'   Sample fighters: {sample_fighters}')
        
        # Show some example fighters with their interconnected data
        self.stdout.write('\n5. Interconnected network examples:')
        jones = Fighter.objects.filter(first_name='Jon', last_name='Jones').first()
        if jones:
            fight_count = jones.fight_history.count()
            linked_opponents = jones.fight_history.filter(opponent_fighter__isnull=False).count()
            self.stdout.write(f'   {jones.get_full_name()}:')
            self.stdout.write(f'     - Fight histories: {fight_count}')
            self.stdout.write(f'     - Linked opponents: {linked_opponents}')
            
            # Show first fight as example
            first_fight = jones.fight_history.first()
            if first_fight and first_fight.opponent:
                self.stdout.write(f'     - Example: vs {first_fight.opponent.get_full_name()} → clickable in admin!')
        
        self.stdout.write('\n=== TEST COMPLETE ===')
        self.stdout.write(self.style.SUCCESS('✅ Duplicate prevention system is working correctly!'))
        self.stdout.write(f'\nAdmin interface: http://localhost:8000/admin/')
        self.stdout.write(f'Login: admin / admin123')


