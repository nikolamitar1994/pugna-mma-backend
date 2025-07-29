"""
Management command to create comprehensive fight statistics demo data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
import random

from events.models import (
    Event, Fight, FightParticipant, FightStatistics, 
    RoundStatistics, Scorecard, RoundScore
)
from fighters.models import Fighter
from organizations.models import Organization, WeightClass


class Command(BaseCommand):
    help = 'Create comprehensive fight statistics demo data (UFCstats.com & mmadecisions.com style)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing demo data first',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing demo data...')
            self.clear_demo_data()
        
        self.stdout.write('Creating comprehensive fight statistics demo...')
        
        with transaction.atomic():
            # Get existing fighters or create them
            fighters = self.get_or_create_demo_fighters()
            
            # Get or create organization and weight class
            org, weight_class = self.get_or_create_demo_org()
            
            # Create demo event
            event = self.create_demo_event(org)
            
            # Create demo fight with full statistics
            fight = self.create_demo_fight(event, weight_class, fighters)
            
            # Create comprehensive fight statistics
            fight_stats = self.create_demo_fight_statistics(fight, fighters)
            
            # Create round-by-round statistics (5 rounds for title fight)
            self.create_demo_round_statistics(fight_stats)
            
            # Create judge scorecards with round-by-round details (5 rounds)
            self.create_demo_scorecards(fight, fighters)
            
            self.test_statistics_display(fight)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created comprehensive fight statistics demo!')
        )
    
    def clear_demo_data(self):
        """Clear existing demo data"""
        # Delete in order to avoid foreign key constraints
        
        RoundScore.objects.filter(
            scorecard__judge_name__in=['John McCarthy', 'Sal DAmato', 'Derek Cleary']
        ).delete()
        
        Scorecard.objects.filter(
            judge_name__in=['John McCarthy', 'Sal DAmato', 'Derek Cleary']
        ).delete()
        
        RoundStatistics.objects.filter(
            fight_statistics__fight__event__name='UFC 300: Demo Event'
        ).delete()
        
        FightStatistics.objects.filter(
            fight__event__name='UFC 300: Demo Event'
        ).delete()
        
        FightParticipant.objects.filter(
            fight__event__name='UFC 300: Demo Event'
        ).delete()
        
        Fight.objects.filter(
            event__name='UFC 300: Demo Event'
        ).delete()
        
        Event.objects.filter(
            name='UFC 300: Demo Event'
        ).delete()
    
    def get_or_create_demo_fighters(self):
        """Get or create demo fighters"""
        fighters = {}
        
        # Get existing fighters from sample data or create new ones
        jones = Fighter.objects.filter(first_name='Jon', last_name='Jones').first()
        if not jones:
            jones = Fighter.objects.create(
                first_name='Jon',
                last_name='Jones',
                nickname='Bones',  
                date_of_birth=date(1987, 7, 19),
                nationality='American',
                height_cm=193,
                weight_kg=93.0,
                reach_cm=215,
                stance='orthodox',
                wins=26,
                losses=1,
                draws=0,
                data_source='demo_stats'
            )
        
        stipe = Fighter.objects.filter(first_name='Stipe', last_name='Miocic').first()
        if not stipe:
            stipe = Fighter.objects.create(
                first_name='Stipe',
                last_name='Miocic',
                nickname='',
                date_of_birth=date(1982, 8, 19),
                nationality='American',
                height_cm=193,
                weight_kg=111.0,  # Heavyweight
                reach_cm=203,
                stance='orthodox',
                wins=20,
                losses=4,
                draws=0,
                data_source='demo_stats'
            )
        
        fighters['jones'] = jones
        fighters['stipe'] = stipe
        
        self.stdout.write(f'  Using fighters: {jones.get_full_name()} vs {stipe.get_full_name()}')
        return fighters
    
    def get_or_create_demo_org(self):
        """Get or create UFC organization and heavyweight division"""
        ufc = Organization.objects.filter(name='Ultimate Fighting Championship').first()
        if not ufc:
            ufc = Organization.objects.create(
                name='Ultimate Fighting Championship',
                abbreviation='UFC',
                headquarters='Las Vegas, Nevada, United States',
                is_active=True
            )
        
        heavyweight = WeightClass.objects.filter(
            name='Heavyweight',
            organization=ufc
        ).first()
        if not heavyweight:
            heavyweight = WeightClass.objects.create(
                name='Heavyweight',
                weight_limit_lbs=265,
                weight_limit_kg=120.2,
                organization=ufc,
                gender='male',
                is_active=True
            )
        
        return ufc, heavyweight
    
    def create_demo_event(self, organization):
        """Create demo event"""
        event = Event.objects.create(
            organization=organization,
            name='UFC 300: Demo Event',
            event_number=300,
            date=date(2024, 4, 13),
            location='Las Vegas, Nevada, United States',
            venue='T-Mobile Arena',
            city='Las Vegas',
            state='Nevada',
            country='United States',
            status='completed',
            attendance=20000,
            gate_revenue=5000000.00
        )
        
        self.stdout.write(f'  Created event: {event.name}')
        return event
    
    def create_demo_fight(self, event, weight_class, fighters):
        """Create demo fight"""
        fight = Fight.objects.create(
            event=event,
            weight_class=weight_class,
            fight_order=1,
            is_main_event=True,
            is_title_fight=True,
            scheduled_rounds=5,
            status='completed',
            winner=fighters['jones'],  # Jones wins
            method='decision',
            method_details='unanimous',
            ending_round=5,
            ending_time='5:00',
            referee='Herb Dean'
        )
        
        # Create fight participants
        FightParticipant.objects.create(
            fight=fight,
            fighter=fighters['jones'],
            corner='red',
            result='win',
            weigh_in_weight=84.5  # Light heavyweight for this demo
        )
        
        FightParticipant.objects.create(
            fight=fight,
            fighter=fighters['stipe'],
            corner='blue',
            result='loss',
            weigh_in_weight=108.2  # Heavyweight cutting down
        )
        
        self.stdout.write(f'  Created fight: {fight}')
        return fight
    
    def create_demo_fight_statistics(self, fight, fighters):
        """Create demo fight statistics"""
        fight_stats = FightStatistics.objects.create(
            fight=fight,
            fighter1=fighters['jones'],
            fighter2=fighters['stipe'],
            
            # Overall striking statistics
            fighter1_strikes_landed=127,
            fighter1_strikes_attempted=218,
            fighter2_strikes_landed=89,
            fighter2_strikes_attempted=156,
            
            # Overall grappling statistics  
            fighter1_takedowns=3,
            fighter1_takedown_attempts=7,
            fighter2_takedowns=1,
            fighter2_takedown_attempts=3,
            
            # Overall control time (in seconds)
            fighter1_control_time=420,  # 7 minutes
            fighter2_control_time=180   # 3 minutes
        )
        
        self.stdout.write(f'  Created fight statistics for {fight}')
        return fight_stats
    
    def create_demo_round_statistics(self, fight_stats):
        """Create detailed round-by-round statistics"""
        
        # Round 1 - Close round, Jones edges it
        RoundStatistics.objects.create(
            fight_statistics=fight_stats,
            round_number=1,
            
            # Jones (Fighter 1) Round 1
            fighter1_head_strikes_landed=15,
            fighter1_head_strikes_attempted=28,
            fighter1_body_strikes_landed=8,
            fighter1_body_strikes_attempted=12,
            fighter1_leg_strikes_landed=3,
            fighter1_leg_strikes_attempted=5,
            fighter1_total_strikes_landed=26,
            fighter1_total_strikes_attempted=45,
            
            fighter1_distance_strikes_landed=20,
            fighter1_distance_strikes_attempted=35,
            fighter1_clinch_strikes_landed=4,
            fighter1_clinch_strikes_attempted=7,
            fighter1_ground_strikes_landed=2,
            fighter1_ground_strikes_attempted=3,
            
            fighter1_takedowns_landed=1,
            fighter1_takedown_attempts=2,
            fighter1_submission_attempts=1,
            fighter1_reversals=0,
            fighter1_control_time=95,  # 1:35
            fighter1_knockdowns=0,
            
            # Stipe (Fighter 2) Round 1
            fighter2_head_strikes_landed=12,
            fighter2_head_strikes_attempted=22,
            fighter2_body_strikes_landed=5,
            fighter2_body_strikes_attempted=8,
            fighter2_leg_strikes_landed=1,
            fighter2_leg_strikes_attempted=3,
            fighter2_total_strikes_landed=18,
            fighter2_total_strikes_attempted=33,
            
            fighter2_distance_strikes_landed=16,
            fighter2_distance_strikes_attempted=28,
            fighter2_clinch_strikes_landed=2,
            fighter2_clinch_strikes_attempted=5,
            fighter2_ground_strikes_landed=0,
            fighter2_ground_strikes_attempted=0,
            
            fighter2_takedowns_landed=0,
            fighter2_takedown_attempts=1,
            fighter2_submission_attempts=0,
            fighter2_reversals=1,
            fighter2_control_time=25,
            fighter2_knockdowns=0,
            
            round_duration=300,
            round_notes='Close opening round, Jones landed the harder shots and secured a takedown'
        )
        
        # Round 2 - Jones dominates
        RoundStatistics.objects.create(
            fight_statistics=fight_stats,
            round_number=2,
            
            # Jones (Fighter 1) Round 2
            fighter1_head_strikes_landed=22,
            fighter1_head_strikes_attempted=35,
            fighter1_body_strikes_landed=12,
            fighter1_body_strikes_attempted=18,
            fighter1_leg_strikes_landed=8,
            fighter1_leg_strikes_attempted=12,
            fighter1_total_strikes_landed=42,
            fighter1_total_strikes_attempted=65,
            
            fighter1_distance_strikes_landed=30,
            fighter1_distance_strikes_attempted=45,
            fighter1_clinch_strikes_landed=8,
            fighter1_clinch_strikes_attempted=12,
            fighter1_ground_strikes_landed=4,
            fighter1_ground_strikes_attempted=8,
            
            fighter1_takedowns_landed=2,
            fighter1_takedown_attempts=3,
            fighter1_submission_attempts=2,
            fighter1_reversals=1,
            fighter1_control_time=180,  # 3:00
            fighter1_knockdowns=0,
            
            # Stipe (Fighter 2) Round 2
            fighter2_head_strikes_landed=8,
            fighter2_head_strikes_attempted=18,
            fighter2_body_strikes_landed=3,
            fighter2_body_strikes_attempted=7,
            fighter2_leg_strikes_landed=2,
            fighter2_leg_strikes_attempted=4,
            fighter2_total_strikes_landed=13,
            fighter2_total_strikes_attempted=29,
            
            fighter2_distance_strikes_landed=11,
            fighter2_distance_strikes_attempted=24,
            fighter2_clinch_strikes_landed=2,
            fighter2_clinch_strikes_attempted=5,
            fighter2_ground_strikes_landed=0,
            fighter2_ground_strikes_attempted=0,
            
            fighter2_takedowns_landed=0,
            fighter2_takedown_attempts=0,
            fighter2_submission_attempts=0,
            fighter2_reversals=0,
            fighter2_control_time=15,
            fighter2_knockdowns=0,
            
            round_duration=300,
            round_notes='Jones dominated with takedowns and ground control'
        )
        
        # Round 3 - Stipe rallies but Jones edges it
        RoundStatistics.objects.create(
            fight_statistics=fight_stats,
            round_number=3,
            
            # Jones (Fighter 1) Round 3
            fighter1_head_strikes_landed=18,
            fighter1_head_strikes_attempted=32,
            fighter1_body_strikes_landed=6,
            fighter1_body_strikes_attempted=10,
            fighter1_leg_strikes_landed=4,
            fighter1_leg_strikes_attempted=8,
            fighter1_total_strikes_landed=28,
            fighter1_total_strikes_attempted=50,
            
            fighter1_distance_strikes_landed=25,
            fighter1_distance_strikes_attempted=42,
            fighter1_clinch_strikes_landed=3,
            fighter1_clinch_strikes_attempted=8,
            fighter1_ground_strikes_landed=0,
            fighter1_ground_strikes_attempted=0,
            
            fighter1_takedowns_landed=0,
            fighter1_takedown_attempts=2,
            fighter1_submission_attempts=0,
            fighter1_reversals=0,
            fighter1_control_time=45,
            fighter1_knockdowns=0,
            
            # Stipe (Fighter 2) Round 3
            fighter2_head_strikes_landed=28,
            fighter2_head_strikes_attempted=45,
            fighter2_body_strikes_landed=14,
            fighter2_body_strikes_attempted=22,
            fighter2_leg_strikes_landed=6,
            fighter2_leg_strikes_attempted=8,
            fighter2_total_strikes_landed=48,
            fighter2_total_strikes_attempted=75,
            
            fighter2_distance_strikes_landed=42,
            fighter2_distance_strikes_attempted=65,
            fighter2_clinch_strikes_landed=6,
            fighter2_clinch_strikes_attempted=10,
            fighter2_ground_strikes_landed=0,
            fighter2_ground_strikes_attempted=0,
            
            fighter2_takedowns_landed=1,
            fighter2_takedown_attempts=2,
            fighter2_submission_attempts=0, 
            fighter2_reversals=0,
            fighter2_control_time=140,  # 2:20
            fighter2_knockdowns=0,
            
            round_duration=300,
            round_notes='Stipe had his best round, landed more strikes but Jones edge in significant strikes'
        )
        
        # Round 4 - Back and forth action
        RoundStatistics.objects.create(
            fight_statistics=fight_stats,
            round_number=4,
            
            # Jones (Fighter 1) Round 4
            fighter1_head_strikes_landed=20,
            fighter1_head_strikes_attempted=34,
            fighter1_body_strikes_landed=7,
            fighter1_body_strikes_attempted=11,
            fighter1_leg_strikes_landed=5,
            fighter1_leg_strikes_attempted=9,
            fighter1_total_strikes_landed=32,
            fighter1_total_strikes_attempted=54,
            
            fighter1_distance_strikes_landed=28,
            fighter1_distance_strikes_attempted=46,
            fighter1_clinch_strikes_landed=4,
            fighter1_clinch_strikes_attempted=8,
            fighter1_ground_strikes_landed=0,
            fighter1_ground_strikes_attempted=0,
            
            fighter1_takedowns_landed=0,
            fighter1_takedown_attempts=1,
            fighter1_submission_attempts=0,
            fighter1_reversals=0,
            fighter1_control_time=75,  # 1:15
            fighter1_knockdowns=0,
            
            # Stipe (Fighter 2) Round 4
            fighter2_head_strikes_landed=25,
            fighter2_head_strikes_attempted=38,
            fighter2_body_strikes_landed=11,
            fighter2_body_strikes_attempted=18,
            fighter2_leg_strikes_landed=4,
            fighter2_leg_strikes_attempted=6,
            fighter2_total_strikes_landed=40,
            fighter2_total_strikes_attempted=62,
            
            fighter2_distance_strikes_landed=35,
            fighter2_distance_strikes_attempted=55,
            fighter2_clinch_strikes_landed=5,
            fighter2_clinch_strikes_attempted=7,
            fighter2_ground_strikes_landed=0,
            fighter2_ground_strikes_attempted=0,
            
            fighter2_takedowns_landed=0,
            fighter2_takedown_attempts=1,
            fighter2_submission_attempts=0,
            fighter2_reversals=0,
            fighter2_control_time=85,  # 1:25
            fighter2_knockdowns=0,
            
            round_duration=300,
            round_notes='Competitive round with both fighters landing clean shots'
        )
        
        # Round 5 - Championship round, Jones pulls away
        RoundStatistics.objects.create(
            fight_statistics=fight_stats,
            round_number=5,
            
            # Jones (Fighter 1) Round 5
            fighter1_head_strikes_landed=17,
            fighter1_head_strikes_attempted=30,
            fighter1_body_strikes_landed=4,
            fighter1_body_strikes_attempted=7,
            fighter1_leg_strikes_landed=2,
            fighter1_leg_strikes_attempted=4,
            fighter1_total_strikes_landed=23,
            fighter1_total_strikes_attempted=41,
            
            fighter1_distance_strikes_landed=18,
            fighter1_distance_strikes_attempted=32,
            fighter1_clinch_strikes_landed=3,
            fighter1_clinch_strikes_attempted=6,
            fighter1_ground_strikes_landed=2,
            fighter1_ground_strikes_attempted=3,
            
            fighter1_takedowns_landed=1,
            fighter1_takedown_attempts=2,
            fighter1_submission_attempts=1,
            fighter1_reversals=0,
            fighter1_control_time=110,  # 1:50
            fighter1_knockdowns=0,
            
            # Stipe (Fighter 2) Round 5
            fighter2_head_strikes_landed=14,
            fighter2_head_strikes_attempted=25,
            fighter2_body_strikes_landed=6,
            fighter2_body_strikes_attempted=10,
            fighter2_leg_strikes_landed=2,
            fighter2_leg_strikes_attempted=3,
            fighter2_total_strikes_landed=22,
            fighter2_total_strikes_attempted=38,
            
            fighter2_distance_strikes_landed=19,
            fighter2_distance_strikes_attempted=32,
            fighter2_clinch_strikes_landed=3,
            fighter2_clinch_strikes_attempted=6,
            fighter2_ground_strikes_landed=0,
            fighter2_ground_strikes_attempted=0,
            
            fighter2_takedowns_landed=0,
            fighter2_takedown_attempts=0,
            fighter2_submission_attempts=0,
            fighter2_reversals=1,
            fighter2_control_time=45,
            fighter2_knockdowns=0,
            
            round_duration=300,
            round_notes='Jones controlled the championship round with a late takedown'
        )
        
        self.stdout.write('  Created 5 rounds of detailed statistics')
    
    def create_demo_scorecards(self, fight, fighters):
        """Create judge scorecards with round-by-round details"""
        
        judges = [
            ('John McCarthy', [10, 10, 10, 10, 10], [9, 8, 9, 9, 9]),    # 50-44 Jones
            ('Sal DAmato', [10, 10, 9, 9, 10], [9, 8, 10, 10, 9]),       # 48-47 Jones
            ('Derek Cleary', [10, 10, 10, 10, 10], [9, 8, 9, 9, 9])      # 50-44 Jones
        ]
        
        for judge_name, jones_rounds, stipe_rounds in judges:
            jones_total = sum(jones_rounds)
            stipe_total = sum(stipe_rounds)
            
            scorecard = Scorecard.objects.create(
                fight=fight,
                judge_name=judge_name,
                fighter1_score=jones_total,
                fighter2_score=stipe_total,
                round_scores=[
                    [jones_rounds[0], stipe_rounds[0]],
                    [jones_rounds[1], stipe_rounds[1]],
                    [jones_rounds[2], stipe_rounds[2]],
                    [jones_rounds[3], stipe_rounds[3]],
                    [jones_rounds[4], stipe_rounds[4]]
                ]
            )
            
            # Create detailed round scores
            for round_num in range(5):
                RoundScore.objects.create(
                    scorecard=scorecard,
                    round_number=round_num + 1,
                    fighter1_round_score=jones_rounds[round_num],
                    fighter2_round_score=stipe_rounds[round_num],
                    
                    # Optional detailed scoring criteria (1-10 scale)
                    fighter1_effective_striking=7.5 + round_num * 0.5,
                    fighter1_effective_grappling=8.0 if round_num < 2 else 6.0,
                    fighter1_control=8.5 if round_num < 2 else 7.0,
                    fighter1_aggression=7.0,
                    
                    fighter2_effective_striking=6.5 + round_num * 1.0,
                    fighter2_effective_grappling=5.0 if round_num < 2 else 7.5,
                    fighter2_control=6.0 if round_num < 2 else 8.0,
                    fighter2_aggression=7.5,
                    
                    round_notes=f'Round {round_num + 1} judging notes for {judge_name}',
                    key_moments=[
                        'takedown attempt at 2:30' if round_num == 0 else '',
                        'ground control dominance' if round_num == 1 else '',
                        'Stipe rally in final minute' if round_num == 2 else '',
                        'back and forth exchanges' if round_num == 3 else '',
                        'championship round takedown' if round_num == 4 else ''
                    ]
                )
        
        self.stdout.write('  Created 3 judge scorecards with 5 rounds of detailed scoring')
    
    def test_statistics_display(self, fight):
        """Test the statistics display functionality"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('FIGHT STATISTICS DEMO RESULTS')
        self.stdout.write('='*60)
        
        # Basic fight info
        self.stdout.write(f'\nFight: {fight}')
        self.stdout.write(f'Method: {fight.method} ({fight.method_details})')
        self.stdout.write(f'Winner: {fight.winner.get_full_name()}')
        
        # Overall statistics
        stats = fight.statistics
        self.stdout.write(f'\nOverall Statistics:')
        self.stdout.write(f'  Jones: {stats.fighter1_strikes_landed}/{stats.fighter1_strikes_attempted} strikes (58.3%)')
        self.stdout.write(f'  Stipe: {stats.fighter2_strikes_landed}/{stats.fighter2_strikes_attempted} strikes (57.1%)')
        self.stdout.write(f'  Jones: {stats.fighter1_takedowns}/{stats.fighter1_takedown_attempts} takedowns (42.9%)')
        self.stdout.write(f'  Stipe: {stats.fighter2_takedowns}/{stats.fighter2_takedown_attempts} takedowns (33.3%)')
        
        # Round breakdown
        self.stdout.write(f'\nRound-by-Round Breakdown:')
        for round_stat in stats.round_stats.all():
            self.stdout.write(f'  Round {round_stat.round_number}:')
            self.stdout.write(f'    Jones: {round_stat.get_fighter1_striking_accuracy()}% striking accuracy')
            self.stdout.write(f'    Stipe: {round_stat.get_fighter2_striking_accuracy()}% striking accuracy')
            self.stdout.write(f'    Control: Jones {round_stat.fighter1_control_time}s vs Stipe {round_stat.fighter2_control_time}s')
        
        # Scorecards
        self.stdout.write(f'\nOfficial Scorecards:')
        for scorecard in fight.scorecards.all():
            self.stdout.write(f'  {scorecard.judge_name}: {scorecard.fighter1_score}-{scorecard.fighter2_score}')
            self.stdout.write(f'    {scorecard.get_round_summary()}')
        
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('✅ Comprehensive fight statistics system ready!')
        self.stdout.write('Visit Django Admin to explore the detailed data:')
        self.stdout.write('- Fight Statistics with round-by-round breakdown')
        self.stdout.write('- Official judge scorecards with detailed round scoring')
        self.stdout.write('='*60)