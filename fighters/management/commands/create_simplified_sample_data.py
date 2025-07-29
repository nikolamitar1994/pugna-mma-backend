"""
Management command to create sample fight data using the new simplified method system.
This demonstrates the new 4-method system: Decision, KO, TKO, Submission + descriptions.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from fighters.models import Fighter, FightHistory
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Creates sample fight history data using the simplified method system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of sample fights to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample data first'
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing sample data...')
            FightHistory.objects.filter(data_source='manual').delete()
            Fighter.objects.filter(data_source='manual').delete()
        
        # Create sample fighters first
        fighters = self.create_sample_fighters()
        
        # Create sample fights using simplified method system
        self.create_sample_fights(fighters, options['count'])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {options["count"]} sample fights using simplified method system!'
            )
        )
    
    def create_sample_fighters(self):
        """Create sample fighters with diverse names"""
        fighters_data = [
            {
                'first_name': 'Jon',
                'last_name': 'Jones',
                'nickname': 'Bones',
                'nationality': 'USA',
                'weight_kg': 93.0,
                'height_cm': 193,
                'reach_cm': 215,
                'stance': 'orthodox'
            },
            {
                'first_name': 'Anderson',
                'last_name': 'Silva',
                'nickname': 'The Spider',
                'nationality': 'Brazil',
                'weight_kg': 84.0,
                'height_cm': 188,
                'reach_cm': 195,
                'stance': 'orthodox'
            },
            {
                'first_name': 'Conor',
                'last_name': 'McGregor',
                'nickname': 'The Notorious',
                'nationality': 'Ireland',
                'weight_kg': 70.0,
                'height_cm': 175,
                'reach_cm': 188,
                'stance': 'southpaw'
            },
            {
                'first_name': 'Khabib',
                'last_name': 'Nurmagomedov',
                'nickname': 'The Eagle',
                'nationality': 'Russia',
                'weight_kg': 70.0,
                'height_cm': 178,
                'reach_cm': 178,
                'stance': 'orthodox'
            },
            {
                'first_name': 'Amanda',
                'last_name': 'Nunes',
                'nickname': 'The Lioness',
                'nationality': 'Brazil',
                'weight_kg': 61.0,
                'height_cm': 173,
                'reach_cm': 180,
                'stance': 'orthodox'
            },
            {
                'first_name': 'Royce',
                'last_name': 'Gracie',
                'nickname': '',
                'nationality': 'Brazil',
                'weight_kg': 77.0,
                'height_cm': 183,
                'reach_cm': 183,
                'stance': 'orthodox'
            },
            {
                # Example of single-name Brazilian fighter
                'first_name': 'Shogun',
                'last_name': '',
                'nickname': '',
                'nationality': 'Brazil',
                'weight_kg': 93.0,
                'height_cm': 185,
                'reach_cm': 190,
                'stance': 'orthodox'
            },
            {
                'first_name': 'Daniel',
                'last_name': 'Cormier',
                'nickname': 'DC',
                'nationality': 'USA',
                'weight_kg': 106.0,
                'height_cm': 180,
                'reach_cm': 183,
                'stance': 'orthodox'
            }
        ]
        
        fighters = []
        for fighter_data in fighters_data:
            fighter, created = Fighter.objects.get_or_create(
                first_name=fighter_data['first_name'],
                last_name=fighter_data['last_name'],
                defaults={
                    'nickname': fighter_data['nickname'],
                    'nationality': fighter_data['nationality'],
                    'weight_kg': fighter_data['weight_kg'],
                    'height_cm': fighter_data['height_cm'],
                    'reach_cm': fighter_data['reach_cm'],
                    'stance': fighter_data['stance'],
                    'data_source': 'manual',
                    'is_active': True,
                }
            )
            fighters.append(fighter)
            
            if created:
                self.stdout.write(f'  Created fighter: {fighter.get_full_name()}')
        
        return fighters
    
    def create_sample_fights(self, fighters, count):
        """Create sample fights using the new simplified method system"""
        
        # Method examples using the new 4-method system
        method_examples = [
            # Decision examples
            ('decision', 'unanimous'),
            ('decision', 'majority'),  
            ('decision', 'split'),
            ('decision', 'technical decision'),
            
            # KO examples
            ('ko', 'head kick'),
            ('ko', 'overhand right'),
            ('ko', 'uppercut'),
            ('ko', ''),  # Basic KO with no description
            
            # TKO examples
            ('tko', 'punches'),
            ('tko', 'kicks'),
            ('tko', 'knees'),
            ('tko', 'elbows'),
            ('tko', 'injury'),
            ('tko', 'retirement'),
            ('tko', 'corner stoppage'),
            ('tko', 'doctor stoppage'),
            ('tko', 'head kick and punches'),
            ('tko', 'body shots'),
            
            # Submission examples
            ('submission', 'rear naked choke'),
            ('submission', 'guillotine choke'),
            ('submission', 'triangle choke'),
            ('submission', 'armbar'),
            ('submission', 'kimura'),
            ('submission', 'americana'),
            ('submission', 'ankle lock'),
            ('submission', 'heel hook'),
            ('submission', 'north-south choke'),
            ('submission', 'mounted triangle'),
        ]
        
        event_names = [
            'UFC 285: Jones vs Gane',
            'UFC 284: Makhachev vs Volkanovski',
            'UFC 283: Teixeira vs Hill',
            'UFC Fight Night: Santos vs Hill',
            'UFC 282: Blachowicz vs Ankalaev',
            'UFC 281: Adesanya vs Pereira',
            'UFC 280: Oliveira vs Makhachev',
            'UFC 279: Diaz vs Ferguson',
            'UFC 278: Usman vs Edwards 2',
            'UFC 277: Peña vs Nunes 2',
        ]
        
        results = ['win', 'loss']
        
        for i in range(count):
            # Pick random fighters (ensure they're different)
            fighter_a, fighter_b = random.sample(fighters, 2)
            
            # Determine winner
            result = random.choice(results)
            winner = fighter_a if result == 'win' else fighter_b
            
            # Pick method from our simplified examples
            method, description = random.choice(method_examples)
            
            # Random fight details
            event_name = random.choice(event_names)
            fight_date = date.today() - timedelta(days=random.randint(30, 1000))
            ending_round = random.randint(1, 5) if method != 'decision' else random.choice([3, 5])
            ending_time = f"{random.randint(0, 4)}:{random.randint(10, 59):02d}" if method != 'decision' else ''
            
            # Create fight history for the main fighter
            fight_history = FightHistory.objects.create(
                fighter=fighter_a,
                result=result,
                opponent_first_name=fighter_b.first_name,
                opponent_last_name=fighter_b.last_name,
                opponent_full_name=fighter_b.get_full_name(),
                opponent_fighter=fighter_b,  # Link to the actual fighter
                method=method,  # Simplified method
                method_description=description,  # Detailed description
                event_name=event_name,
                event_date=fight_date,
                ending_round=ending_round if method != 'decision' else None,
                ending_time=ending_time if method != 'decision' else None,
                scheduled_rounds=3 if 'Fight Night' in event_name else 5,
                location=f'Las Vegas, Nevada, USA',
                venue='T-Mobile Arena',
                city='Las Vegas',
                state='Nevada',
                country='USA',
                weight_class_name='Lightweight',
                organization_name='UFC',
                data_source='manual',
                fight_order=i + 1,
                notes=f'Sample fight demonstrating simplified method system: {method.upper()}' + (f' ({description})' if description else ''),
            )
            
            # Also create the opposite perspective for the opponent
            opposite_result = 'loss' if result == 'win' else 'win'
            FightHistory.objects.create(
                fighter=fighter_b,
                result=opposite_result,
                opponent_first_name=fighter_a.first_name,
                opponent_last_name=fighter_a.last_name,
                opponent_full_name=fighter_a.get_full_name(),
                opponent_fighter=fighter_a,
                method=method,
                method_description=description,
                event_name=event_name,
                event_date=fight_date,
                ending_round=ending_round if method != 'decision' else None,
                ending_time=ending_time if method != 'decision' else None,
                scheduled_rounds=3 if 'Fight Night' in event_name else 5,
                location=f'Las Vegas, Nevada, USA',
                venue='T-Mobile Arena',
                city='Las Vegas',
                state='Nevada',
                country='USA',
                weight_class_name='Lightweight',
                organization_name='UFC',
                data_source='manual',
                fight_order=random.randint(1, 20),  # Random order for opponent
                notes=f'Sample fight demonstrating simplified method system: {method.upper()}' + (f' ({description})' if description else ''),
            )
            
            method_display = method.upper() + (f' ({description})' if description else '')
            self.stdout.write(
                f'  Fight {i+1}: {fighter_a.get_full_name()} {result.upper()} vs '
                f'{fighter_b.get_full_name()} by {method_display}'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n📊 Summary of Simplified Method System:\n'
                '• Decision: All decision types (unanimous, majority, split, technical)\n'
                '• KO: All knockouts with strike descriptions\n' 
                '• TKO: All technical knockouts with specific reasons\n'
                '• Submission: All submissions with technique names\n'
                '• Detailed information moved to "Method Description" field\n'
            )
        )