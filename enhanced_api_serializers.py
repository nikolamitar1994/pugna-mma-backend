from rest_framework import serializers
from rest_framework.reverse import reverse
from django.db.models import Q, Count, Avg
from .models import (
    Organization, WeightClass, Fighter, Event, Fight, 
    FightStats, Scorecard, Ranking, Championship, ScrapingJob
)
from django.utils import timezone


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer with event count"""
    event_count = serializers.SerializerMethodField()
    active_fighters_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'abbreviation', 'founded_date', 'headquarters',
            'website', 'logo', 'is_active', 'description', 'event_count',
            'active_fighters_count', 'created_at', 'updated_at'
        ]
    
    def get_event_count(self, obj):
        return obj.event_set.filter(is_completed=True).count()
    
    def get_active_fighters_count(self, obj):
        return Fighter.objects.filter(
            Q(fights_as_fighter_1__event__organization=obj) |
            Q(fights_as_fighter_2__event__organization=obj),
            status='active'
        ).distinct().count()


class WeightClassSerializer(serializers.ModelSerializer):
    """Weight class serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    current_champion = serializers.SerializerMethodField()
    
    class Meta:
        model = WeightClass
        fields = [
            'id', 'name', 'weight_limit_lbs', 'weight_limit_kg', 
            'organization', 'organization_name', 'gender', 'is_active',
            'current_champion'
        ]
    
    def get_current_champion(self, obj):
        champion = Championship.objects.filter(
            weight_class=obj,
            is_current=True
        ).first()
        if champion:
            return {
                'id': champion.fighter.id,
                'name': champion.fighter.display_name,
                'title_won_date': champion.title_won_date
            }
        return None


class FighterListSerializer(serializers.ModelSerializer):
    """Lightweight fighter serializer for list views"""
    record_string = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    
    class Meta:
        model = Fighter
        fields = [
            'id', 'first_name', 'last_name', 'nickname', 'display_name',
            'record_string', 'age', 'weight_class_name', 'nationality',
            'status', 'profile_image', 'slug'
        ]


class FighterDetailSerializer(serializers.ModelSerializer):
    """Detailed fighter serializer"""
    record_string = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    organization_name = serializers.CharField(source='weight_class.organization.name', read_only=True)
    
    # Career statistics
    recent_fights = serializers.SerializerMethodField()
    championship_history = serializers.SerializerMethodField()
    current_ranking = serializers.SerializerMethodField()
    career_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Fighter
        fields = [
            'id', 'first_name', 'last_name', 'nickname', 'display_name',
            'height_cm', 'weight_lbs', 'reach_cm', 'stance', 'date_of_birth',
            'nationality', 'birthplace', 'gender', 'professional_debut',
            'weight_class', 'weight_class_name', 'organization_name', 'team',
            'status', 'profile_image', 'record_string', 'age',
            'total_wins', 'total_losses', 'total_draws', 'total_no_contests',
            'wins_by_ko_tko', 'wins_by_submission', 'wins_by_decision',
            'bio', 'recent_fights', 'championship_history', 'current_ranking',
            'career_stats', 'wikipedia_url', 'instagram_url', 'twitter_url',
            'slug'
        ]
    
    def get_recent_fights(self, obj):
        recent_fights = Fight.objects.filter(
            Q(fighter_1=obj) | Q(fighter_2=obj)
        ).select_related('event', 'fighter_1', 'fighter_2').order_by('-event__date')[:5]
        
        return FightListSerializer(recent_fights, many=True, context=self.context).data
    
    def get_championship_history(self, obj):
        championships = Championship.objects.filter(
            fighter=obj
        ).select_related('weight_class', 'organization').order_by('-title_won_date')
        
        return ChampionshipSerializer(championships, many=True).data
    
    def get_current_ranking(self, obj):
        ranking = Ranking.objects.filter(
            fighter=obj,
            ranking_date__lte=timezone.now().date()
        ).order_by('-ranking_date').first()
        
        if ranking:
            return {
                'position': ranking.position,
                'weight_class': ranking.weight_class.name,
                'organization': ranking.organization.name,
                'is_champion': ranking.is_champion,
                'ranking_date': ranking.ranking_date
            }
        return None
    
    def get_career_stats(self, obj):
        """Calculate comprehensive career statistics"""
        fights = Fight.objects.filter(
            Q(fighter_1=obj) | Q(fighter_2=obj),
            result__in=['win_fighter_1', 'win_fighter_2']
        ).select_related('stats')
        
        total_fights = fights.count()
        if total_fights == 0:
            return {}
        
        # Calculate average fight stats
        total_sig_strikes = 0
        total_takedowns = 0
        total_submissions = 0
        total_control_time = 0
        
        for fight in fights:
            if hasattr(fight, 'stats'):
                if fight.fighter_1 == obj:
                    total_sig_strikes += fight.stats.fighter_1_significant_strikes_landed
                    total_takedowns += fight.stats.fighter_1_takedowns_landed
                    total_submissions += fight.stats.fighter_1_submission_attempts
                    total_control_time += fight.stats.fighter_1_control_time_seconds
                else:
                    total_sig_strikes += fight.stats.fighter_2_significant_strikes_landed
                    total_takedowns += fight.stats.fighter_2_takedowns_landed
                    total_submissions += fight.stats.fighter_2_submission_attempts
                    total_control_time += fight.stats.fighter_2_control_time_seconds
        
        return {
            'avg_significant_strikes_per_fight': round(total_sig_strikes / total_fights, 1),
            'avg_takedowns_per_fight': round(total_takedowns / total_fights, 1),
            'avg_submission_attempts_per_fight': round(total_submissions / total_fights, 1),
            'avg_control_time_per_fight': round(total_control_time / total_fights, 1),
            'total_fights_with_stats': total_fights
        }


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight event serializer for list views"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    fight_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'organization', 'organization_name', 'event_number',
            'date', 'location', 'venue', 'city', 'country', 'poster',
            'is_completed', 'fight_count', 'slug'
        ]
    
    def get_fight_count(self, obj):
        return obj.fights.count()


class FightListSerializer(serializers.ModelSerializer):
    """Fight serializer for list views"""
    fighter_1_name = serializers.CharField(source='fighter_1.display_name', read_only=True)
    fighter_2_name = serializers.CharField(source='fighter_2.display_name', read_only=True)
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_date = serializers.DateField(source='event.date', read_only=True)
    winner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Fight
        fields = [
            'id', 'event', 'event_name', 'event_date', 'fighter_1', 'fighter_1_name',
            'fighter_2', 'fighter_2_name', 'weight_class_name', 'fight_type',
            'card_position', 'fight_order', 'result', 'method', 'ending_round',
            'ending_time', 'winner_name', 'performance_bonus', 'fight_of_the_night'
        ]
    
    def get_winner_name(self, obj):
        winner = obj.winner
        return winner.display_name if winner else None


class ScorecardSerializer(serializers.ModelSerializer):
    """Scorecard serializer"""
    total_fighter_1 = serializers.ReadOnlyField()
    total_fighter_2 = serializers.ReadOnlyField()
    
    class Meta:
        model = Scorecard
        fields = [
            'judge_name', 'round_1_fighter_1', 'round_1_fighter_2',
            'round_2_fighter_1', 'round_2_fighter_2', 'round_3_fighter_1',
            'round_3_fighter_2', 'round_4_fighter_1', 'round_4_fighter_2',
            'round_5_fighter_1', 'round_5_fighter_2', 'total_fighter_1',
            'total_fighter_2'
        ]


class FightStatsSerializer(serializers.ModelSerializer):
    """Fight statistics serializer"""
    class Meta:
        model = FightStats
        fields = [
            'fighter_1_significant_strikes_landed', 'fighter_1_significant_strikes_attempted',
            'fighter_1_total_strikes_landed', 'fighter_1_total_strikes_attempted',
            'fighter_1_takedowns_landed', 'fighter_1_takedowns_attempted',
            'fighter_1_submission_attempts', 'fighter_1_control_time_seconds',
            'fighter_2_significant_strikes_landed', 'fighter_2_significant_strikes_attempted',
            'fighter_2_total_strikes_landed', 'fighter_2_total_strikes_attempted',
            'fighter_2_takedowns_landed', 'fighter_2_takedowns_attempted',
            'fighter_2_submission_attempts', 'fighter_2_control_time_seconds',
            'round_by_round_data'
        ]


class FightDetailSerializer(serializers.ModelSerializer):
    """Detailed fight serializer"""
    fighter_1_name = serializers.CharField(source='fighter_1.display_name', read_only=True)
    fighter_2_name = serializers.CharField(source='fighter_2.display_name', read_only=True)
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    event_date = serializers.DateField(source='event.date', read_only=True)
    organization_name = serializers.CharField(source='event.organization.name', read_only=True)
    winner_name = serializers.SerializerMethodField()
    
    # Related data
    stats = FightStatsSerializer(read_only=True)
    scorecards = ScorecardSerializer(many=True, read_only=True)
    
    class Meta:
        model = Fight
        fields = [
            'id', 'event', 'event_name', 'event_date', 'organization_name',
            'fighter_1', 'fighter_1_name', 'fighter_2', 'fighter_2_name',
            'weight_class', 'weight_class_name', 'fight_type', 'card_position',
            'fight_order', 'scheduled_rounds', 'result', 'method',
            'submission_method', 'ending_round', 'ending_time', 'winner_name',
            'performance_bonus', 'fight_of_the_night', 'stats', 'scorecards',
            'ufcstats_url', 'mmadecisions_url'
        ]
    
    def get_winner_name(self, obj):
        winner = obj.winner
        return winner.display_name if winner else None


class EventDetailSerializer(serializers.ModelSerializer):
    """Detailed event serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    fights = serializers.SerializerMethodField()
    main_event = serializers.SerializerMethodField()
    co_main_event = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'organization', 'organization_name', 'event_number',
            'date', 'location', 'venue', 'city', 'state_province', 'country',
            'poster', 'description', 'main_event', 'co_main_event', 'fights',
            'wikipedia_url', 'official_url', 'is_completed', 'slug'
        ]
    
    def get_fights(self, obj):
        fights = obj.fights.all().select_related(
            'fighter_1', 'fighter_2', 'weight_class'
        ).order_by('fight_order')
        return FightListSerializer(fights, many=True, context=self.context).data
    
    def get_main_event(self, obj):
        main_event = obj.fights.filter(fight_type='main').first()
        return FightListSerializer(main_event, context=self.context).data if main_event else None
    
    def get_co_main_event(self, obj):
        co_main_event = obj.fights.filter(fight_type='co_main').first()
        return FightListSerializer(co_main_event, context=self.context).data if co_main_event else None


class RankingSerializer(serializers.ModelSerializer):
    """Ranking serializer"""
    fighter_name = serializers.CharField(source='fighter.display_name', read_only=True)
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    fighter_record = serializers.CharField(source='fighter.record_string', read_only=True)
    
    class Meta:
        model = Ranking
        fields = [
            'id', 'fighter', 'fighter_name', 'fighter_record', 'weight_class',
            'weight_class_name', 'organization', 'organization_name', 'position',
            'is_champion', 'is_interim_champion', 'ranking_date', 'previous_position'
        ]


class ChampionshipSerializer(serializers.ModelSerializer):
    """Championship history serializer"""
    fighter_name = serializers.CharField(source='fighter.display_name', read_only=True)
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    reign_duration_days = serializers.ReadOnlyField()
    won_against_name = serializers.CharField(source='won_against.display_name', read_only=True)
    
    class Meta:
        model = Championship
        fields = [
            'id', 'fighter', 'fighter_name', 'weight_class', 'weight_class_name',
            'organization', 'organization_name', 'title_won_date', 'title_lost_date',
            'is_current', 'is_interim', 'won_against', 'won_against_name',
            'how_won', 'how_lost', 'successful_defenses', 'reign_duration_days'
        ]


class ScrapingJobSerializer(serializers.ModelSerializer):
    """Scraping job serializer for monitoring data collection"""
    progress_percentage = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = ScrapingJob
        fields = [
            'id', 'job_type', 'source', 'status', 'target_url', 'target_model',
            'target_id', 'items_processed', 'items_total', 'error_count',
            'progress_percentage', 'duration', 'started_at', 'completed_at',
            'created_at', 'error_log'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.items_total > 0:
            return round((obj.items_processed / obj.items_total) * 100, 1)
        return 0
    
    def get_duration(self, obj):
        if obj.started_at:
            end_time = obj.completed_at or timezone.now()
            duration = end_time - obj.started_at
            return duration.total_seconds()
        return None


# Custom serializers for specific API endpoints

class DivisionRankingsSerializer(serializers.Serializer):
    """Serializer for complete division rankings"""
    weight_class = WeightClassSerializer(read_only=True)
    champion = serializers.SerializerMethodField()
    interim_champion = serializers.SerializerMethodField()
    contenders = serializers.SerializerMethodField()
    
    def get_champion(self, obj):
        champion_ranking = obj.get('rankings', []).filter(position=1, is_champion=True).first()
        return RankingSerializer(champion_ranking).data if champion_ranking else None
    
    def get_interim_champion(self, obj):
        interim_ranking = obj.get('rankings', []).filter(is_interim_champion=True).first()
        return RankingSerializer(interim_ranking).data if interim_ranking else None
    
    def get_contenders(self, obj):
        contenders = obj.get('rankings', []).filter(
            position__range=(2, 15),
            is_champion=False,
            is_interim_champion=False
        ).order_by('position')
        return RankingSerializer(contenders, many=True).data


class FighterStatsComparisonSerializer(serializers.Serializer):
    """Serializer for comparing two fighters"""
    fighter_1 = FighterDetailSerializer(read_only=True)
    fighter_2 = FighterDetailSerializer(read_only=True)
    head_to_head = serializers.SerializerMethodField()
    common_opponents = serializers.SerializerMethodField()
    
    def get_head_to_head(self, obj):
        """Get direct fights between the two fighters"""
        fighter_1 = obj['fighter_1']
        fighter_2 = obj['fighter_2']
        
        head_to_head_fights = Fight.objects.filter(
            Q(fighter_1=fighter_1, fighter_2=fighter_2) |
            Q(fighter_1=fighter_2, fighter_2=fighter_1)
        ).select_related('event').order_by('-event__date')
        
        return FightListSerializer(head_to_head_fights, many=True).data
    
    def get_common_opponents(self, obj):
        """Get fighters that both have fought"""
        fighter_1 = obj['fighter_1']
        fighter_2 = obj['fighter_2']
        
        # Get all opponents of fighter_1
        fighter_1_opponents = Fighter.objects.filter(
            Q(fights_as_fighter_1__fighter_2=fighter_1) |
            Q(fights_as_fighter_2__fighter_1=fighter_1)
        ).distinct()
        
        # Get all opponents of fighter_2
        fighter_2_opponents = Fighter.objects.filter(
            Q(fights_as_fighter_1__fighter_2=fighter_2) |
            Q(fights_as_fighter_2__fighter_1=fighter_2)
        ).distinct()
        
        # Find common opponents
        common_opponents = fighter_1_opponents.intersection(fighter_2_opponents)
        
        return FighterListSerializer(common_opponents, many=True).data