"""
Management command to create sample data for testing the interconnected network
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from fighters.models import Fighter, FightHistory
from fighters.services.matching import FighterMatcher


class Command(BaseCommand):
    help = 'Create sample data to test the interconnected fighter network'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample data first',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing sample data...')
            self.clear_sample_data()
        
        self.stdout.write('Creating sample data for interconnected network testing...')
        
        with transaction.atomic():
            # Create sample fighters
            fighters = self.create_sample_fighters()
            
            # Create sample organizations and events (if models exist)
            organizations, events = self.create_sample_events()
            
            # Create interconnected fight histories
            self.create_sample_fight_histories(fighters, events)
            
            # Test the network
            self.test_network_functionality(fighters)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data for network testing!')
        )
    
    def clear_sample_data(self):
        """Clear existing sample data"""
        # Delete sample fight histories
        FightHistory.objects.filter(
            data_source='sample_data'
        ).delete()
        
        # Delete sample fighters
        Fighter.objects.filter(
            data_source='sample_data'
        ).delete()
        
        # Delete sample events and organizations if they exist
        try:
            from events.models import Event, Fight
            from organizations.models import Organization, WeightClass
            
            Fight.objects.filter(event__name__in=['UFC 182', 'UFC 214']).delete()
            Event.objects.filter(name__in=['UFC 182', 'UFC 214']).delete()
            Organization.objects.filter(name='Ultimate Fighting Championship').delete()
            WeightClass.objects.filter(name='Light Heavyweight').delete()
        except ImportError:
            pass
    
    def create_sample_fighters(self):
        """Create sample fighters for testing"""
        self.stdout.write('Creating sample fighters...')
        
        fighters_data = [
            {
                'first_name': 'Jon',
                'last_name': 'Jones',
                'nickname': 'Bones',
                'date_of_birth': date(1987, 7, 19),
                'nationality': 'American',
                'height_cm': 193,
                'weight_kg': 93.0,
                'reach_cm': 215,
                'stance': 'orthodox',
                'fighting_out_of': 'Albuquerque, New Mexico',
                'team': 'Jackson Wink MMA',
                'wins': 26,
                'losses': 1,
                'draws': 0,
                'no_contests': 1,
                'wins_by_ko': 6,
                'wins_by_tko': 4,
                'wins_by_submission': 6,
                'wins_by_decision': 10,
            },
            {
                'first_name': 'Daniel',
                'last_name': 'Cormier',
                'nickname': 'DC',
                'date_of_birth': date(1979, 3, 20),
                'nationality': 'American',
                'height_cm': 180,
                'weight_kg': 93.0,
                'reach_cm': 183,
                'stance': 'orthodox',
                'fighting_out_of': 'San Jose, California',
                'team': 'American Kickboxing Academy',
                'wins': 22,
                'losses': 3,
                'draws': 0,
                'no_contests': 1,
                'wins_by_ko': 2,
                'wins_by_tko': 8,
                'wins_by_submission': 2,
                'wins_by_decision': 10,
            },
            {
                'first_name': 'Alexander',
                'last_name': 'Gustafsson',
                'nickname': 'The Mauler',
                'date_of_birth': date(1987, 1, 15),
                'nationality': 'Swedish',
                'height_cm': 196,
                'weight_kg': 93.0,
                'reach_cm': 196,
                'stance': 'orthodox',
                'fighting_out_of': 'Stockholm, Sweden',
                'team': 'Allstars Training Center',
                'wins': 18,
                'losses': 8,
                'draws': 0,
                'no_contests': 0,
                'wins_by_ko': 4,
                'wins_by_tko': 6,
                'wins_by_submission': 0,
                'wins_by_decision': 8,
            },
            {
                'first_name': 'Anthony',
                'last_name': 'Johnson',
                'nickname': 'Rumble',
                'date_of_birth': date(1984, 3, 6),
                'nationality': 'American',
                'height_cm': 188,
                'weight_kg': 93.0,
                'reach_cm': 198,
                'stance': 'orthodox',
                'fighting_out_of': 'Dublin, Georgia',
                'team': 'Blackzilians',
                'wins': 23,
                'losses': 6,
                'draws': 0,
                'no_contests': 0,
                'wins_by_ko': 12,
                'wins_by_tko': 9,
                'wins_by_submission': 0,
                'wins_by_decision': 2,
            }
        ]
        
        fighters = {}
        for fighter_data in fighters_data:
            fighter_data['data_source'] = 'sample_data'
            fighter_data['data_quality_score'] = 0.95
            
            fighter = Fighter.objects.create(**fighter_data)
            fighters[f"{fighter.first_name}_{fighter.last_name}"] = fighter
            
            self.stdout.write(f'  Created fighter: {fighter.get_full_name()}')
        
        return fighters
    
    def create_sample_events(self):
        """Create sample events and organizations if models exist"""
        organizations = {}
        events = {}
        
        try:
            from events.models import Event
            from organizations.models import Organization, WeightClass
            
            self.stdout.write('Creating sample organizations and events...')
            
            # Create UFC organization
            ufc = Organization.objects.create(
                name='Ultimate Fighting Championship',
                abbreviation='UFC',
                headquarters='Las Vegas, Nevada, United States',
                is_active=True
            )
            organizations['UFC'] = ufc
            self.stdout.write('  Created organization: UFC')
            
            # Create Light Heavyweight weight class
            lhw = WeightClass.objects.create(
                name='Light Heavyweight',
                weight_limit_lbs=205,
                weight_limit_kg=93.0,
                organization=ufc,
                gender='male',
                is_active=True
            )
            
            # Create sample events
            events_data = [
                {
                    'name': 'UFC 182',
                    'date': date(2015, 1, 3),
                    'location': 'Las Vegas, Nevada, United States',
                    'venue': 'MGM Grand Garden Arena',
                    'organization': ufc,
                },
                {
                    'name': 'UFC 214',
                    'date': date(2017, 7, 29),
                    'location': 'Anaheim, California, United States',
                    'venue': 'Honda Center',
                    'organization': ufc,
                }
            ]
            
            for event_data in events_data:
                event = Event.objects.create(**event_data)
                events[event.name] = event
                self.stdout.write(f'  Created event: {event.name}')
                
        except ImportError:
            self.stdout.write('Event and Organization models not available - skipping')
        
        return organizations, events
    
    def create_sample_fight_histories(self, fighters, events):
        """Create interconnected fight histories"""
        self.stdout.write('Creating sample fight histories...')
        
        jon_jones = fighters['Jon_Jones']
        daniel_cormier = fighters['Daniel_Cormier']
        alex_gustafsson = fighters['Alexander_Gustafsson']
        anthony_johnson = fighters['Anthony_Johnson']
        
        # Create fight histories with interconnected opponents
        fight_histories = [
            # Jon Jones vs Daniel Cormier - UFC 182
            {
                'fighter': jon_jones,
                'opponent_fighter': daniel_cormier,
                'opponent_first_name': 'Daniel',
                'opponent_last_name': 'Cormier',
                'opponent_full_name': 'Daniel Cormier',
                'result': 'win',
                'method': 'decision_unanimous',
                'event_name': 'UFC 182',
                'event_date': date(2015, 1, 3),
                'ending_round': 5,
                'ending_time': '5:00',
                'scheduled_rounds': 5,
                'location': 'Las Vegas, Nevada, United States',
                'venue': 'MGM Grand Garden Arena',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 20,
                'fighter_record_at_time': '19-1 (0)',
                'notes': 'Jones retained the UFC Light Heavyweight title',
            },
            # Daniel Cormier's perspective of the same fight
            {
                'fighter': daniel_cormier,
                'opponent_fighter': jon_jones,
                'opponent_first_name': 'Jon',
                'opponent_last_name': 'Jones',
                'opponent_full_name': 'Jon Jones',
                'result': 'loss',
                'method': 'decision_unanimous',
                'event_name': 'UFC 182',
                'event_date': date(2015, 1, 3),
                'ending_round': 5,
                'ending_time': '5:00',
                'scheduled_rounds': 5,
                'location': 'Las Vegas, Nevada, United States',
                'venue': 'MGM Grand Garden Arena',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 15,
                'fighter_record_at_time': '15-0 (0)',
                'notes': 'Failed to win the UFC Light Heavyweight title',
            },
            # Jon Jones vs Daniel Cormier II - UFC 214
            {
                'fighter': jon_jones,
                'opponent_fighter': daniel_cormier,
                'opponent_first_name': 'Daniel',
                'opponent_last_name': 'Cormier',
                'opponent_full_name': 'Daniel Cormier',
                'result': 'win',
                'method': 'tko_kicks',
                'method_details': 'head kick and punches',
                'event_name': 'UFC 214',
                'event_date': date(2017, 7, 29),
                'ending_round': 3,
                'ending_time': '4:20',
                'scheduled_rounds': 5,
                'location': 'Anaheim, California, United States',
                'venue': 'Honda Center',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 21,
                'fighter_record_at_time': '22-1 (0)',
                'notes': 'Jones reclaimed the UFC Light Heavyweight title',
                'performance_bonuses': ['Performance of the Night'],
            },
            # Daniel Cormier's perspective of UFC 214
            {
                'fighter': daniel_cormier,
                'opponent_fighter': jon_jones,
                'opponent_first_name': 'Jon',
                'opponent_last_name': 'Jones',
                'opponent_full_name': 'Jon Jones',
                'result': 'loss',
                'method': 'tko_kicks',
                'method_details': 'head kick and punches',
                'event_name': 'UFC 214',
                'event_date': date(2017, 7, 29),
                'ending_round': 3,
                'ending_time': '4:20',
                'scheduled_rounds': 5,
                'location': 'Anaheim, California, United States',
                'venue': 'Honda Center',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 16,
                'fighter_record_at_time': '19-1 (0)',
                'notes': 'Lost the UFC Light Heavyweight title',
            },
            # Jon Jones vs Alexander Gustafsson
            {
                'fighter': jon_jones,
                'opponent_fighter': alex_gustafsson,
                'opponent_first_name': 'Alexander',
                'opponent_last_name': 'Gustafsson',
                'opponent_full_name': 'Alexander Gustafsson',
                'result': 'win',
                'method': 'decision_unanimous',
                'event_name': 'UFC 165',
                'event_date': date(2013, 9, 21),
                'ending_round': 5,
                'ending_time': '5:00',
                'scheduled_rounds': 5,
                'location': 'Toronto, Ontario, Canada',
                'venue': 'Air Canada Centre',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 18,
                'fighter_record_at_time': '18-1 (0)',
                'notes': 'Fight of the Year candidate',
                'performance_bonuses': ['Fight of the Night'],
            },
            # Daniel Cormier vs Anthony Johnson
            {
                'fighter': daniel_cormier,
                'opponent_fighter': anthony_johnson,
                'opponent_first_name': 'Anthony',
                'opponent_last_name': 'Johnson',
                'opponent_full_name': 'Anthony Johnson',
                'result': 'win',
                'method': 'submission_rear_naked_choke',
                'event_name': 'UFC 210',
                'event_date': date(2017, 4, 8),
                'ending_round': 2,
                'ending_time': '4:47',
                'scheduled_rounds': 5,
                'location': 'Buffalo, New York, United States',
                'venue': 'KeyBank Center',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 17,
                'fighter_record_at_time': '18-1 (0)',
                'notes': 'Successfully defended the UFC Light Heavyweight title',
                'performance_bonuses': ['Performance of the Night'],
            },
            # Anthony Johnson's perspective of the same fight
            {
                'fighter': anthony_johnson,
                'opponent_fighter': daniel_cormier,
                'opponent_first_name': 'Daniel',
                'opponent_last_name': 'Cormier',
                'opponent_full_name': 'Daniel Cormier',
                'result': 'loss',
                'method': 'submission_rear_naked_choke',
                'event_name': 'UFC 210',
                'event_date': date(2017, 4, 8),
                'ending_round': 2,
                'ending_time': '4:47',
                'scheduled_rounds': 5,
                'location': 'Buffalo, New York, United States',
                'venue': 'KeyBank Center',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 15,
                'fighter_record_at_time': '22-6 (0)',
                'notes': 'Lost title fight to Daniel Cormier',
            },
            # Alexander Gustafsson's perspective vs Jon Jones
            {
                'fighter': alex_gustafsson,
                'opponent_fighter': jon_jones,
                'opponent_first_name': 'Jon',
                'opponent_last_name': 'Jones',
                'opponent_full_name': 'Jon Jones',
                'result': 'loss',
                'method': 'decision_unanimous',
                'event_name': 'UFC 165',
                'event_date': date(2013, 9, 21),
                'ending_round': 5,
                'ending_time': '5:00',
                'scheduled_rounds': 5,
                'location': 'Toronto, Ontario, Canada',
                'venue': 'Air Canada Centre',
                'organization_name': 'UFC',
                'weight_class_name': 'Light Heavyweight',
                'is_title_fight': True,
                'title_belt': 'UFC Light Heavyweight Championship',
                'fight_order': 12,
                'fighter_record_at_time': '15-1 (0)',
                'notes': 'Came close to winning the title',
                'performance_bonuses': ['Fight of the Night'],
            }
        ]
        
        for fight_data in fight_histories:
            fight_data['data_source'] = 'sample_data'
            fight_history = FightHistory.objects.create(**fight_data)
            
            self.stdout.write(f'  Created fight: {fight_history.fighter.get_full_name()} vs {fight_history.opponent_full_name}')
    
    def test_network_functionality(self, fighters):
        """Test the interconnected network functionality"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('TESTING INTERCONNECTED NETWORK FUNCTIONALITY')
        self.stdout.write('='*50)
        
        jon_jones = fighters['Jon_Jones']
        daniel_cormier = fighters['Daniel_Cormier']
        
        # Test 1: Get Jon Jones' fight history
        self.stdout.write(f'\n1. {jon_jones.get_full_name()} Fight History:')
        for fight in jon_jones.fight_history.all()[:3]:
            opponent = fight.opponent
            self.stdout.write(f'   vs {fight.opponent_full_name} ({fight.result.upper()})')
            if opponent:
                self.stdout.write(f'      → Linked to Fighter: {opponent.get_full_name()} (ID: {opponent.id})')
                self.stdout.write(f'      → Opponent Record: {opponent.get_record_string()}')
            else:
                self.stdout.write('      → No Fighter link (string data only)')
        
        # Test 2: Test opponent property
        self.stdout.write(f'\n2. Network Navigation Test:')
        first_fight = jon_jones.fight_history.first()
        if first_fight:
            self.stdout.write(f'   Fight: {first_fight}')
            self.stdout.write(f'   Opponent object: {first_fight.opponent}')
            if first_fight.opponent:
                self.stdout.write(f'   Opponent nationality: {first_fight.opponent.nationality}')
                self.stdout.write(f'   Opponent team: {first_fight.opponent.team}')
        
        # Test 3: Bidirectional relationships
        self.stdout.write(f'\n3. Bidirectional Relationship Test:')
        jones_vs_dc = jon_jones.fight_history.filter(opponent_fighter=daniel_cormier).first()
        dc_vs_jones = daniel_cormier.fight_history.filter(opponent_fighter=jon_jones).first()
        
        if jones_vs_dc and dc_vs_jones:
            self.stdout.write(f'   Jones perspective: {jones_vs_dc.result} vs {jones_vs_dc.opponent_full_name}')
            self.stdout.write(f'   DC perspective: {dc_vs_jones.result} vs {dc_vs_jones.opponent_full_name}')
            self.stdout.write('   ✓ Bidirectional relationship confirmed!')
        
        # Test 4: Network statistics
        from fighters.services.validation import NetworkConsistencyValidator
        stats = NetworkConsistencyValidator.get_network_statistics()
        
        self.stdout.write(f'\n4. Network Statistics:')
        self.stdout.write(f'   Total fight histories: {stats["total_fight_histories"]}')
        self.stdout.write(f'   Linked opponents: {stats["linked_opponents"]}')
        self.stdout.write(f'   Opponent link percentage: {stats["opponent_link_percentage"]:.1f}%')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Network testing completed!')
        self.stdout.write('='*50)