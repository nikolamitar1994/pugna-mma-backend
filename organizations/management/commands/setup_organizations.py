from django.core.management.base import BaseCommand
from django.db import transaction
from organizations.models import Organization, WeightClass


class Command(BaseCommand):
    help = 'Set up initial MMA organizations (UFC, KSW, Oktagon, PFL) with weight classes'

    def handle(self, *args, **options):
        self.stdout.write('Setting up MMA organizations...')
        
        with transaction.atomic():
            # Create UFC
            ufc = self.create_ufc()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {ufc.name}'))
            
            # Create KSW
            ksw = self.create_ksw()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {ksw.name}'))
            
            # Create Oktagon
            oktagon = self.create_oktagon()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {oktagon.name}'))
            
            # Create PFL
            pfl = self.create_pfl()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {pfl.name}'))
        
        self.stdout.write(self.style.SUCCESS('\nSuccessfully set up all organizations!'))
    
    def create_ufc(self):
        """Create UFC organization with weight classes"""
        ufc, created = Organization.objects.update_or_create(
            abbreviation='UFC',
            defaults={
                'name': 'Ultimate Fighting Championship',
                'full_name': 'Ultimate Fighting Championship',
                'org_type': 'major',
                'founded_date': '1993-11-12',
                'headquarters': 'Las Vegas, Nevada, USA',
                'country': 'United States',
                'website': 'https://www.ufc.com',
                'wikipedia_url': 'https://en.wikipedia.org/wiki/Ultimate_Fighting_Championship',
                'scoring_system': 'unified',
                'round_duration_minutes': 5,
                'championship_rounds': 5,
                'non_title_rounds': 3,
                'weight_allowance_lbs': 1.0,
                'event_naming_pattern': 'UFC {number}',
                'uses_event_numbers': True,
                'wikipedia_category': 'Ultimate_Fighting_Championship_events',
                'priority_order': 1,
                'is_active': True
            }
        )
        
        # UFC Men's Weight Classes
        mens_classes = [
            ('Flyweight', 'FLW', 125, 1),
            ('Bantamweight', 'BW', 135, 2),
            ('Featherweight', 'FW', 145, 3),
            ('Lightweight', 'LW', 155, 4),
            ('Welterweight', 'WW', 170, 5),
            ('Middleweight', 'MW', 185, 6),
            ('Light Heavyweight', 'LHW', 205, 7),
            ('Heavyweight', 'HW', 265, 8),
        ]
        
        for name, abbrev, limit, order in mens_classes:
            WeightClass.objects.update_or_create(
                organization=ufc,
                name=name,
                gender='male',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        # UFC Women's Weight Classes
        womens_classes = [
            ('Strawweight', 'WSW', 115, 11),
            ('Flyweight', 'WFLW', 125, 12),
            ('Bantamweight', 'WBW', 135, 13),
            ('Featherweight', 'WFW', 145, 14),
        ]
        
        for name, abbrev, limit, order in womens_classes:
            WeightClass.objects.update_or_create(
                organization=ufc,
                name=name,
                gender='female',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        return ufc
    
    def create_ksw(self):
        """Create KSW organization with weight classes"""
        ksw, created = Organization.objects.update_or_create(
            abbreviation='KSW',
            defaults={
                'name': 'Konfrontacja Sztuk Walki',
                'full_name': 'Konfrontacja Sztuk Walki',
                'org_type': 'major',
                'founded_date': '2004-05-01',
                'headquarters': 'Warsaw, Poland',
                'country': 'Poland',
                'website': 'https://www.kswmma.com',
                'wikipedia_url': 'https://en.wikipedia.org/wiki/Konfrontacja_Sztuk_Walki',
                'scoring_system': 'unified',
                'round_duration_minutes': 5,
                'championship_rounds': 5,
                'non_title_rounds': 3,
                'weight_allowance_lbs': 1.0,
                'event_naming_pattern': 'KSW {number}',
                'uses_event_numbers': True,
                'wikipedia_category': 'Konfrontacja_Sztuk_Walki_events',
                'priority_order': 2,
                'is_active': True
            }
        )
        
        # KSW uses similar weight classes to UFC
        classes = [
            ('Flyweight', 'FLW', 125, 1),
            ('Bantamweight', 'BW', 135, 2),
            ('Featherweight', 'FW', 145, 3),
            ('Lightweight', 'LW', 155, 4),
            ('Welterweight', 'WW', 170, 5),
            ('Middleweight', 'MW', 185, 6),
            ('Light Heavyweight', 'LHW', 205, 7),
            ('Heavyweight', 'HW', 265, 8),
        ]
        
        for name, abbrev, limit, order in classes:
            WeightClass.objects.update_or_create(
                organization=ksw,
                name=name,
                gender='male',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        return ksw
    
    def create_oktagon(self):
        """Create Oktagon MMA organization with weight classes"""
        oktagon, created = Organization.objects.update_or_create(
            abbreviation='OKTAGON',
            defaults={
                'name': 'Oktagon MMA',
                'full_name': 'Oktagon MMA',
                'org_type': 'major',
                'founded_date': '2016-01-01',
                'headquarters': 'Prague, Czech Republic',
                'country': 'Czech Republic',
                'website': 'https://www.oktagonmma.com',
                'wikipedia_url': 'https://en.wikipedia.org/wiki/Oktagon_MMA',
                'scoring_system': 'unified',
                'round_duration_minutes': 5,
                'championship_rounds': 5,
                'non_title_rounds': 3,
                'weight_allowance_lbs': 1.0,
                'event_naming_pattern': 'OKTAGON {number}',
                'uses_event_numbers': True,
                'priority_order': 3,
                'is_active': True
            }
        )
        
        # Oktagon weight classes
        classes = [
            ('Flyweight', 'FLW', 125, 1),
            ('Bantamweight', 'BW', 135, 2),
            ('Featherweight', 'FW', 145, 3),
            ('Lightweight', 'LW', 155, 4),
            ('Welterweight', 'WW', 170, 5),
            ('Middleweight', 'MW', 185, 6),
            ('Light Heavyweight', 'LHW', 205, 7),
            ('Heavyweight', 'HW', 265, 8),
        ]
        
        for name, abbrev, limit, order in classes:
            WeightClass.objects.update_or_create(
                organization=oktagon,
                name=name,
                gender='male',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        return oktagon
    
    def create_pfl(self):
        """Create PFL organization with weight classes"""
        pfl, created = Organization.objects.update_or_create(
            abbreviation='PFL',
            defaults={
                'name': 'Professional Fighters League',
                'full_name': 'Professional Fighters League',
                'org_type': 'major',
                'founded_date': '2018-01-01',  # Rebranded from WSOF
                'headquarters': 'New York City, New York, USA',
                'country': 'United States',
                'website': 'https://www.pflmma.com',
                'wikipedia_url': 'https://en.wikipedia.org/wiki/Professional_Fighters_League',
                'scoring_system': 'unified',
                'round_duration_minutes': 5,
                'championship_rounds': 5,
                'non_title_rounds': 3,
                'weight_allowance_lbs': 1.0,
                'event_naming_pattern': 'PFL {year} {event}',
                'uses_event_numbers': False,
                'wikipedia_category': 'Professional_Fighters_League_events',
                'priority_order': 4,
                'is_active': True
            }
        )
        
        # PFL Men's Weight Classes (they use different names for some)
        mens_classes = [
            ('Featherweight', 'FW', 145, 1),
            ('Lightweight', 'LW', 155, 2),
            ('Welterweight', 'WW', 170, 3),
            ('Middleweight', 'MW', 185, 4),
            ('Light Heavyweight', 'LHW', 205, 5),
            ('Heavyweight', 'HW', 265, 6),
        ]
        
        for name, abbrev, limit, order in mens_classes:
            WeightClass.objects.update_or_create(
                organization=pfl,
                name=name,
                gender='male',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        # PFL Women's Weight Classes
        womens_classes = [
            ('Lightweight', 'WLW', 155, 11),
        ]
        
        for name, abbrev, limit, order in womens_classes:
            WeightClass.objects.update_or_create(
                organization=pfl,
                name=name,
                gender='female',
                defaults={
                    'abbreviation': abbrev,
                    'weight_limit_lbs': limit,
                    'display_order': order,
                    'is_active': True
                }
            )
        
        return pfl