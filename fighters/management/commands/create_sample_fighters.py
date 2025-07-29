from django.core.management.base import BaseCommand
from django.db import transaction
from fighters.models import Fighter, FighterNameVariation
from organizations.models import Organization, WeightClass
from datetime import date
import random


class Command(BaseCommand):
    help = 'Create sample fighter data for development and testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=25,
            help='Number of fighters to create (default: 25)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing fighters before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        if options['clear']:
            self.stdout.write('Clearing existing fighters...')
            Fighter.objects.all().delete()
            
        # Create organizations if they don't exist
        self.create_organizations()
        
        # Create weight classes if they don't exist
        self.create_weight_classes()
        
        self.stdout.write(f'Creating {count} sample fighters...')
        
        with transaction.atomic():
            for i in range(count):
                fighter_data = self.get_fighter_data(i)
                fighter = Fighter.objects.create(**fighter_data)
                
                # Add name variations for some fighters
                if random.choice([True, False]):
                    self.create_name_variations(fighter)
                
                if i % 5 == 0:
                    self.stdout.write(f'Created {i + 1} fighters...')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} sample fighters!')
        )

    def create_organizations(self):
        """Create sample MMA organizations"""
        orgs = [
            {'name': 'Ultimate Fighting Championship', 'abbreviation': 'UFC', 'country': 'USA'},
            {'name': 'Konfrontacja Sztuk Walki', 'abbreviation': 'KSW', 'country': 'Poland'},
            {'name': 'Oktagon MMA', 'abbreviation': 'Oktagon', 'country': 'Czech Republic'},
            {'name': 'Professional Fighters League', 'abbreviation': 'PFL', 'country': 'USA'},
        ]
        
        for org_data in orgs:
            Organization.objects.get_or_create(
                abbreviation=org_data['abbreviation'],
                defaults=org_data
            )
            
        self.stdout.write('Organizations created/verified')

    def create_weight_classes(self):
        """Create standard MMA weight classes"""
        weight_classes = [
            {'name': 'Flyweight', 'weight_limit_lbs': 125, 'gender': 'M'},
            {'name': 'Bantamweight', 'weight_limit_lbs': 135, 'gender': 'M'},
            {'name': 'Featherweight', 'weight_limit_lbs': 145, 'gender': 'M'},
            {'name': 'Lightweight', 'weight_limit_lbs': 155, 'gender': 'M'},
            {'name': 'Welterweight', 'weight_limit_lbs': 170, 'gender': 'M'},
            {'name': 'Middleweight', 'weight_limit_lbs': 185, 'gender': 'M'},
            {'name': 'Light Heavyweight', 'weight_limit_lbs': 205, 'gender': 'M'},
            {'name': 'Heavyweight', 'weight_limit_lbs': 265, 'gender': 'M'},
            {'name': 'Women\'s Strawweight', 'weight_limit_lbs': 115, 'gender': 'F'},
            {'name': 'Women\'s Flyweight', 'weight_limit_lbs': 125, 'gender': 'F'},
            {'name': 'Women\'s Bantamweight', 'weight_limit_lbs': 135, 'gender': 'F'},
            {'name': 'Women\'s Featherweight', 'weight_limit_lbs': 145, 'gender': 'F'},
        ]
        
        ufc = Organization.objects.get(abbreviation='UFC')
        
        for wc_data in weight_classes:
            WeightClass.objects.get_or_create(
                name=wc_data['name'],
                organization=ufc,
                defaults={
                    'weight_limit_lbs': wc_data['weight_limit_lbs'],
                    'gender': wc_data['gender']
                }
            )
            
        self.stdout.write('Weight classes created/verified')

    def get_fighter_data(self, index):
        """Generate realistic fighter data"""
        
        # Sample fighter templates with realistic data
        fighters_templates = [
            # Western fighters
            {'first_name': 'Jon', 'last_name': 'Jones', 'nickname': 'Bones', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Conor', 'last_name': 'McGregor', 'nickname': 'The Notorious', 'nationality': 'Ireland', 'stance': 'southpaw'},
            {'first_name': 'Khabib', 'last_name': 'Nurmagomedov', 'nickname': 'The Eagle', 'nationality': 'Russia', 'stance': 'orthodox'},
            {'first_name': 'Daniel', 'last_name': 'Cormier', 'nickname': 'DC', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Dustin', 'last_name': 'Poirier', 'nickname': 'The Diamond', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Justin', 'last_name': 'Gaethje', 'nickname': 'The Highlight', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Tony', 'last_name': 'Ferguson', 'nickname': 'El Cucuy', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Jorge', 'last_name': 'Masvidal', 'nickname': 'Gamebred', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Colby', 'last_name': 'Covington', 'nickname': 'Chaos', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Kamaru', 'last_name': 'Usman', 'nickname': 'The Nigerian Nightmare', 'nationality': 'Nigeria', 'stance': 'orthodox'},
            
            # Brazilian fighters (some with single names)
            {'first_name': 'Anderson', 'last_name': 'Silva', 'nickname': 'The Spider', 'nationality': 'Brazil', 'stance': 'orthodox'},
            {'first_name': '', 'last_name': 'Shogun', 'display_name': 'Shogun', 'nationality': 'Brazil', 'stance': 'orthodox'},
            {'first_name': 'José', 'last_name': 'Aldo', 'nickname': 'Scarface', 'nationality': 'Brazil', 'stance': 'orthodox'},
            {'first_name': 'Charles', 'last_name': 'Oliveira', 'nickname': 'Do Bronx', 'nationality': 'Brazil', 'stance': 'orthodox'},
            {'first_name': '', 'last_name': 'Ronaldo', 'display_name': 'Ronaldo', 'nationality': 'Brazil', 'stance': 'southpaw'},
            
            # International fighters
            {'first_name': 'Zhang', 'last_name': 'Weili', 'nickname': 'Magnum', 'nationality': 'China', 'stance': 'orthodox'},
            {'first_name': 'Israel', 'last_name': 'Adesanya', 'nickname': 'The Last Stylebender', 'nationality': 'Nigeria', 'stance': 'orthodox'},
            {'first_name': 'Alexander', 'last_name': 'Volkanovski', 'nickname': 'The Great', 'nationality': 'Australia', 'stance': 'orthodox'},
            {'first_name': 'Jan', 'last_name': 'Błachowicz', 'nickname': 'Prince of Cieszyn', 'nationality': 'Poland', 'stance': 'orthodox'},
            {'first_name': 'Jiří', 'last_name': 'Procházka', 'nickname': 'Denisa', 'nationality': 'Czech Republic', 'stance': 'southpaw'},
            
            # Women fighters
            {'first_name': 'Amanda', 'last_name': 'Nunes', 'nickname': 'The Lioness', 'nationality': 'Brazil', 'stance': 'orthodox'},
            {'first_name': 'Valentina', 'last_name': 'Shevchenko', 'nickname': 'Bullet', 'nationality': 'Kyrgyzstan', 'stance': 'orthodox'},
            {'first_name': 'Rose', 'last_name': 'Namajunas', 'nickname': 'Thug', 'nationality': 'USA', 'stance': 'orthodox'},
            {'first_name': 'Joanna', 'last_name': 'Jędrzejczyk', 'nickname': 'Joanna Champion', 'nationality': 'Poland', 'stance': 'orthodox'},
            {'first_name': 'Miesha', 'last_name': 'Tate', 'nickname': 'Cupcake', 'nationality': 'USA', 'stance': 'orthodox'},
        ]
        
        # Cycle through templates or create variations
        if index < len(fighters_templates):
            template = fighters_templates[index].copy()
        else:
            # Create variations of existing templates
            base_template = fighters_templates[index % len(fighters_templates)]
            template = base_template.copy()
            template['first_name'] = f"{template['first_name']}{index}"
            template['last_name'] = f"{template['last_name']}_V{index}"
        
        # Generate realistic stats
        wins = random.randint(8, 25)
        losses = random.randint(0, 8)
        draws = random.randint(0, 2)
        
        # Generate finish distribution
        wins_by_ko = random.randint(0, min(wins // 2, 8))
        wins_by_tko = random.randint(0, min(wins // 2, 6))
        wins_by_submission = random.randint(0, min(wins // 3, 4))
        wins_by_decision = wins - wins_by_ko - wins_by_tko - wins_by_submission
        
        # Ensure non-negative decisions
        if wins_by_decision < 0:
            excess = abs(wins_by_decision)
            wins_by_ko = max(0, wins_by_ko - excess // 3)
            wins_by_tko = max(0, wins_by_tko - excess // 3)
            wins_by_submission = max(0, wins_by_submission - excess // 3)
            wins_by_decision = wins - wins_by_ko - wins_by_tko - wins_by_submission
        
        fighter_data = {
            'first_name': template.get('first_name', ''),
            'last_name': template.get('last_name', ''),
            'display_name': template.get('display_name', ''),
            'nickname': template.get('nickname', ''),
            'nationality': template.get('nationality', 'USA'),
            'stance': template.get('stance', 'orthodox'),
            'date_of_birth': date(
                random.randint(1980, 2000),
                random.randint(1, 12),
                random.randint(1, 28)
            ),
            'height_cm': random.randint(160, 200),
            'weight_kg': random.randint(60, 120),
            'reach_cm': random.randint(165, 210),
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'wins_by_ko': wins_by_ko,
            'wins_by_tko': wins_by_tko,
            'wins_by_submission': wins_by_submission,
            'wins_by_decision': wins_by_decision,
            'fighting_out_of': random.choice([
                'American Top Team', 'Jackson Wink MMA', 'American Kickboxing Academy',
                'Team Alpha Male', 'SBG Ireland', 'ATT', 'Kings MMA', 'Tristar Gym'
            ]),
            'is_active': random.choice([True, True, True, False]),  # 75% active
            'data_source': 'sample_data',
            'data_quality_score': round(random.uniform(0.7, 1.0), 2),
        }
        
        return fighter_data

    def create_name_variations(self, fighter):
        """Create name variations for some fighters"""
        variations = []
        
        if fighter.nickname:
            variations.append({
                'fighter': fighter,
                'first_name_variation': '',
                'last_name_variation': fighter.nickname,
                'full_name_variation': fighter.nickname,
                'variation_type': 'nickname_only',
                'source': 'sample_data'
            })
        
        # Add transliteration variations for international fighters
        if fighter.nationality in ['Russia', 'China', 'Poland', 'Czech Republic']:
            alt_spellings = {
                'Khabib': 'Habib',
                'Nurmagomedov': 'Nourmagomedov', 
                'Zhang': 'Zheng',
                'Błachowicz': 'Blachowicz',
                'Procházka': 'Prochazka',
                'Jędrzejczyk': 'Jedrzejczyk',
            }
            
            if fighter.last_name in alt_spellings:
                variations.append({
                    'fighter': fighter,
                    'first_name_variation': fighter.first_name,
                    'last_name_variation': alt_spellings[fighter.last_name],
                    'full_name_variation': f"{fighter.first_name} {alt_spellings[fighter.last_name]}".strip(),
                    'variation_type': 'transliteration',
                    'source': 'sample_data'
                })
        
        # Create the variations
        for variation_data in variations:
            FighterNameVariation.objects.create(**variation_data)