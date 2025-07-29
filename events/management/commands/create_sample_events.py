"""
Management command to create sample events with complete fight cards for testing.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from events.models import Event, Fight, FightParticipant
from organizations.models import Organization, WeightClass
from fighters.models import Fighter
import random


class Command(BaseCommand):
    help = 'Create sample events with complete fight cards'

    def handle(self, *args, **options):
        # Get or create UFC organization
        try:
            ufc = Organization.objects.get(abbreviation='UFC')
        except Organization.DoesNotExist:
            ufc = Organization.objects.create(
                name='Ultimate Fighting Championship',
                abbreviation='UFC',
                headquarters='Las Vegas, United States',
                founded_date=date(1993, 11, 12),
                website='https://www.ufc.com',
                is_active=True
            )

        # Get weight classes
        heavyweight = WeightClass.objects.filter(name='Heavyweight', organization=ufc).first()
        light_heavyweight = WeightClass.objects.filter(name='Light Heavyweight', organization=ufc).first()
        middleweight = WeightClass.objects.filter(name='Middleweight', organization=ufc).first()
        welterweight = WeightClass.objects.filter(name='Welterweight', organization=ufc).first()
        lightweight = WeightClass.objects.filter(name='Lightweight', organization=ufc).first()

        if not heavyweight:
            self.stdout.write(self.style.WARNING('Weight classes not found. Creating basic weight classes...'))
            heavyweight = WeightClass.objects.create(name='Heavyweight', organization=ufc, weight_limit_lbs=265, weight_limit_kg=120.0)
            light_heavyweight = WeightClass.objects.create(name='Light Heavyweight', organization=ufc, weight_limit_lbs=205, weight_limit_kg=93.0)
            middleweight = WeightClass.objects.create(name='Middleweight', organization=ufc, weight_limit_lbs=185, weight_limit_kg=84.0)
            welterweight = WeightClass.objects.create(name='Welterweight', organization=ufc, weight_limit_lbs=170, weight_limit_kg=77.0)
            lightweight = WeightClass.objects.create(name='Lightweight', organization=ufc, weight_limit_lbs=155, weight_limit_kg=70.0)

        # Get some fighters (create if needed)
        fighters_data = [
            {'first_name': 'Jon', 'last_name': 'Jones', 'weight_class': light_heavyweight},
            {'first_name': 'Stipe', 'last_name': 'Miocic', 'weight_class': heavyweight},
            {'first_name': 'Israel', 'last_name': 'Adesanya', 'weight_class': middleweight},
            {'first_name': 'Sean', 'last_name': 'Strickland', 'weight_class': middleweight},
            {'first_name': 'Leon', 'last_name': 'Edwards', 'weight_class': welterweight},
            {'first_name': 'Colby', 'last_name': 'Covington', 'weight_class': welterweight},
            {'first_name': 'Islam', 'last_name': 'Makhachev', 'weight_class': lightweight},
            {'first_name': 'Charles', 'last_name': 'Oliveira', 'weight_class': lightweight},
            {'first_name': 'Tom', 'last_name': 'Aspinall', 'weight_class': heavyweight},
            {'first_name': 'Curtis', 'last_name': 'Blaydes', 'weight_class': heavyweight},
            {'first_name': 'Alex', 'last_name': 'Pereira', 'weight_class': light_heavyweight},
            {'first_name': 'Jamahal', 'last_name': 'Hill', 'weight_class': light_heavyweight},
            {'first_name': 'Kamaru', 'last_name': 'Usman', 'weight_class': welterweight},
            {'first_name': 'Jorge', 'last_name': 'Masvidal', 'weight_class': welterweight},
        ]

        fighters = {}
        for fighter_data in fighters_data:
            fighter, created = Fighter.objects.get_or_create(
                first_name=fighter_data['first_name'],
                last_name=fighter_data['last_name'],
                defaults={
                    'nationality': 'United States',
                    'height_cm': random.randint(175, 195),
                    'weight_kg': fighter_data['weight_class'].weight_limit_kg - 2,
                    'is_active': True,
                    'data_source': 'sample_data'
                }
            )
            fighters[f"{fighter_data['first_name']} {fighter_data['last_name']}"] = fighter
            if created:
                self.stdout.write(f"Created fighter: {fighter.get_full_name()}")

        # Create sample events
        events_data = [
            {
                'name': 'UFC 309: Jones vs Miocic',
                'date': date(2024, 11, 16),
                'status': 'completed',
                'location': 'Madison Square Garden, New York, NY',
                'venue': 'Madison Square Garden',
                'city': 'New York',
                'state': 'New York',
                'country': 'United States',
                'fights': [
                    # Main Card
                    {
                        'fighter1': 'Jon Jones', 'fighter2': 'Stipe Miocic', 'weight_class': heavyweight,
                        'fight_order': 1, 'is_main_event': True, 'is_title_fight': True,
                        'result': ('Jon Jones', 'win'), 'method': 'tko', 'round': 3, 'time': '4:29'
                    },
                    {
                        'fighter1': 'Charles Oliveira', 'fighter2': 'Islam Makhachev', 'weight_class': lightweight,
                        'fight_order': 2, 'is_title_fight': True,
                        'result': ('Islam Makhachev', 'win'), 'method': 'submission', 'round': 2, 'time': '3:15'
                    },
                    {
                        'fighter1': 'Leon Edwards', 'fighter2': 'Colby Covington', 'weight_class': welterweight,
                        'fight_order': 3,
                        'result': ('Leon Edwards', 'win'), 'method': 'decision', 'round': 3, 'time': '5:00'
                    },
                    {
                        'fighter1': 'Alex Pereira', 'fighter2': 'Jamahal Hill', 'weight_class': light_heavyweight,
                        'fight_order': 4,
                        'result': ('Alex Pereira', 'win'), 'method': 'ko', 'round': 1, 'time': '2:47'
                    },
                    {
                        'fighter1': 'Tom Aspinall', 'fighter2': 'Curtis Blaydes', 'weight_class': heavyweight,
                        'fight_order': 5,
                        'result': ('Tom Aspinall', 'win'), 'method': 'tko', 'round': 1, 'time': '1:08'
                    },
                    # Preliminary Card
                    {
                        'fighter1': 'Israel Adesanya', 'fighter2': 'Sean Strickland', 'weight_class': middleweight,
                        'fight_order': 6,
                        'result': ('Sean Strickland', 'win'), 'method': 'decision', 'round': 3, 'time': '5:00'
                    },
                    {
                        'fighter1': 'Kamaru Usman', 'fighter2': 'Jorge Masvidal', 'weight_class': welterweight,
                        'fight_order': 7,
                        'result': ('Kamaru Usman', 'win'), 'method': 'ko', 'round': 2, 'time': '1:02'
                    },
                ]
            },
            {
                'name': 'UFC 310: Adesanya vs Strickland 2',
                'date': date(2025, 3, 8),
                'status': 'scheduled',
                'location': 'T-Mobile Arena, Las Vegas, NV',
                'venue': 'T-Mobile Arena',
                'city': 'Las Vegas',
                'state': 'Nevada',
                'country': 'United States',
                'fights': [
                    # Main Card (upcoming - no results)
                    {
                        'fighter1': 'Israel Adesanya', 'fighter2': 'Sean Strickland', 'weight_class': middleweight,
                        'fight_order': 1, 'is_main_event': True, 'is_title_fight': True,
                    },
                    {
                        'fighter1': 'Leon Edwards', 'fighter2': 'Kamaru Usman', 'weight_class': welterweight,
                        'fight_order': 2, 'is_title_fight': True,
                    },
                    {
                        'fighter1': 'Tom Aspinall', 'fighter2': 'Curtis Blaydes', 'weight_class': heavyweight,
                        'fight_order': 3,
                    },
                    {
                        'fighter1': 'Alex Pereira', 'fighter2': 'Jamahal Hill', 'weight_class': light_heavyweight,
                        'fight_order': 4,
                    },
                    {
                        'fighter1': 'Charles Oliveira', 'fighter2': 'Islam Makhachev', 'weight_class': lightweight,
                        'fight_order': 5,
                    },
                    # Preliminary Card
                    {
                        'fighter1': 'Colby Covington', 'fighter2': 'Jorge Masvidal', 'weight_class': welterweight,
                        'fight_order': 6,
                    },
                ]
            }
        ]

        for event_data in events_data:
            event, created = Event.objects.get_or_create(
                name=event_data['name'],
                defaults={
                    'organization': ufc,
                    'date': event_data['date'],
                    'status': event_data['status'],
                    'location': event_data['location'],
                    'venue': event_data['venue'],
                    'city': event_data['city'],
                    'state': event_data['state'],
                    'country': event_data['country'],
                    'attendance': 20000 if event_data['status'] == 'completed' else None,
                    'gate_revenue': 5000000.00 if event_data['status'] == 'completed' else None,
                }
            )

            if created:
                self.stdout.write(f"Created event: {event.name}")

                # Create fights for this event
                for fight_data in event_data['fights']:
                    fighter1 = fighters[fight_data['fighter1']]
                    fighter2 = fighters[fight_data['fighter2']]

                    fight = Fight.objects.create(
                        event=event,
                        weight_class=fight_data['weight_class'],
                        fight_order=fight_data['fight_order'],
                        is_main_event=fight_data.get('is_main_event', False),
                        is_title_fight=fight_data.get('is_title_fight', False),
                        scheduled_rounds=5 if fight_data.get('is_title_fight') else 3,
                        status='completed' if event_data['status'] == 'completed' else 'scheduled',
                        method=fight_data.get('method', '') if event_data['status'] == 'completed' else '',
                        ending_round=fight_data.get('round') if event_data['status'] == 'completed' else None,
                        ending_time=fight_data.get('time', '') if event_data['status'] == 'completed' else '',
                        referee='Herb Dean' if fight_data['fight_order'] <= 5 else 'Jason Herzog'
                    )

                    # Create fight participants
                    if event_data['status'] == 'completed' and 'result' in fight_data:
                        winner_name, result = fight_data['result']
                        if winner_name == fight_data['fighter1']:
                            fighter1_result = 'win'
                            fighter2_result = 'loss'
                            fight.winner = fighter1
                        else:
                            fighter1_result = 'loss'
                            fighter2_result = 'win'
                            fight.winner = fighter2
                        fight.save()
                    else:
                        fighter1_result = ''
                        fighter2_result = ''

                    FightParticipant.objects.create(
                        fight=fight,
                        fighter=fighter1,
                        corner='red',
                        result=fighter1_result,
                        weigh_in_weight=fight_data['weight_class'].weight_limit_kg - Decimal('1.0')
                    )

                    FightParticipant.objects.create(
                        fight=fight,
                        fighter=fighter2,
                        corner='blue',
                        result=fighter2_result,
                        weigh_in_weight=fight_data['weight_class'].weight_limit_kg - Decimal('0.5')
                    )

                    self.stdout.write(f"  Created fight: {fighter1.get_full_name()} vs {fighter2.get_full_name()}")

            else:
                self.stdout.write(f"Event already exists: {event.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample events created successfully!\n'
                f'Visit /admin/events/event/ to see the fight card overviews:\n'
                f'• UFC 309 (completed) - See results with methods and timing\n'
                f'• UFC 310 (upcoming) - See clean matchup preview\n'
                f'The fight cards are organized by Main Card, Prelims, and Early Prelims!'
            )
        )