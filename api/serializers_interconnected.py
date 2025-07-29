"""
Enhanced API serializers for the interconnected fight history system.

These serializers provide seamless access to both legacy string-based data
and new interconnected Fight relationships, returning the most up-to-date
information available.
"""

from rest_framework import serializers
from fighters.models import Fighter, FightHistory, FighterNameVariation
from events.models import Fight, Event, FightParticipant
from organizations.models import Organization, WeightClass


class FighterSummarySerializer(serializers.ModelSerializer):
    """Lightweight fighter serializer for nested use."""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    record = serializers.SerializerMethodField()
    
    class Meta:
        model = Fighter
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'nickname', 'nationality', 'record', 'is_active'
        ]
    
    def get_record(self, obj):
        """Get fighter's current record."""
        return {
            'wins': obj.wins,
            'losses': obj.losses,
            'draws': obj.draws,
            'no_contests': obj.no_contests
        }


class EventSummarySerializer(serializers.ModelSerializer):
    """Lightweight event serializer for nested use."""
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'date', 'location', 'organization_name'
        ]


class AuthoritativeFightSummarySerializer(serializers.ModelSerializer):
    """Summary of authoritative Fight record."""
    
    event = EventSummarySerializer(read_only=True)
    participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Fight
        fields = [
            'id', 'event', 'fight_order', 'is_main_event', 'is_title_fight',
            'status', 'method', 'ending_round', 'ending_time', 'participants'
        ]
    
    def get_participants(self, obj):
        """Get fight participants."""
        participants = obj.participants.select_related('fighter').all()[:2]
        return [
            {
                'fighter_id': p.fighter.id,
                'fighter_name': p.fighter.get_full_name(),
                'corner': p.corner,
                'result': p.result
            }
            for p in participants
        ]


class InterconnectedFightHistorySerializer(serializers.ModelSerializer):
    """
    Enhanced fight history serializer that seamlessly integrates legacy and 
    interconnected data, always returning the most current information available.
    """
    
    # Core fighter information
    fighter = FighterSummarySerializer(read_only=True)
    
    # Dynamic fields that prioritize live data from authoritative Fight
    opponent_name = serializers.SerializerMethodField()
    opponent_fighter = FighterSummarySerializer(read_only=True)
    event_name = serializers.SerializerMethodField()
    event_date = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    method = serializers.SerializerMethodField()
    method_display = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    # Interconnection metadata
    is_interconnected = serializers.SerializerMethodField()
    data_freshness = serializers.SerializerMethodField()
    authoritative_fight = serializers.SerializerMethodField()
    data_conflicts = serializers.SerializerMethodField()
    
    # Enhanced display fields
    fight_summary = serializers.SerializerMethodField()
    career_context = serializers.SerializerMethodField()
    
    # Original fields for transparency
    stored_opponent_name = serializers.CharField(source='opponent_full_name', read_only=True)
    stored_event_name = serializers.CharField(source='event_name', read_only=True)
    stored_result = serializers.CharField(source='result', read_only=True)
    
    class Meta:
        model = FightHistory
        fields = [
            # Core identification
            'id', 'fighter', 'fight_order',
            
            # Live data (prioritizes authoritative source)
            'opponent_name', 'opponent_fighter', 'result', 'method', 'method_display',
            'event_name', 'event_date', 'location',
            
            # Fight details
            'ending_round', 'ending_time', 'scheduled_rounds',
            'is_title_fight', 'is_interim_title', 'title_belt',
            'weight_class_name', 'organization_name',
            
            # Career context
            'fighter_record_at_time', 'career_context', 'fight_summary',
            
            # Data quality and source
            'data_quality_score', 'data_source', 'is_interconnected', 
            'data_freshness', 'data_conflicts', 'authoritative_fight',
            
            # Transparency fields (show original stored values)
            'stored_opponent_name', 'stored_event_name', 'stored_result',
            
            # Additional context
            'notes', 'performance_bonuses', 'created_at', 'updated_at'
        ]
    
    def get_opponent_name(self, obj):
        """Get opponent name, prioritizing live data from authoritative Fight."""
        return obj.get_live_opponent_name()
    
    def get_event_name(self, obj):
        """Get event name, prioritizing live data from authoritative Fight."""
        return obj.get_live_event_name()
    
    def get_event_date(self, obj):
        """Get event date, prioritizing live data from authoritative Fight."""
        return obj.get_live_event_date()
    
    def get_result(self, obj):
        """Get fight result, prioritizing live data from authoritative Fight."""
        return obj.get_live_result()
    
    def get_method(self, obj):
        """Get fight method, prioritizing live data from authoritative Fight."""
        return obj.get_live_method()
    
    def get_method_display(self, obj):
        """Get human-readable method with details."""
        return obj.get_method_display()
    
    def get_location(self, obj):
        """Get fight location, prioritizing live data from authoritative Fight."""
        return obj.get_live_location()
    
    def get_is_interconnected(self, obj):
        """Check if this record is linked to an authoritative Fight."""
        return obj.is_interconnected()
    
    def get_data_freshness(self, obj):
        """Get data freshness indicator (live vs historical)."""
        return obj.get_data_freshness()
    
    def get_authoritative_fight(self, obj):
        """Get authoritative fight summary if available."""
        return obj.get_authoritative_fight_summary()
    
    def get_data_conflicts(self, obj):
        """Get any conflicts between stored and authoritative data."""
        conflicts = obj.has_data_conflicts()
        if conflicts:
            return {
                'has_conflicts': True,
                'conflicts': conflicts,
                'resolution': 'Use sync_from_authoritative_fight() to resolve'
            }
        return {'has_conflicts': False}
    
    def get_fight_summary(self, obj):
        """Get a concise fight summary for display."""
        fighter_name = obj.fighter.get_display_name()
        opponent_name = self.get_opponent_name(obj)
        result = self.get_result(obj).upper()
        method = self.get_method(obj)
        
        summary = f"{fighter_name} {result} vs {opponent_name}"
        if method:
            summary += f" by {method}"
        
        if obj.ending_round and obj.ending_time:
            summary += f" (R{obj.ending_round} {obj.ending_time})"
        
        return summary
    
    def get_career_context(self, obj):
        """Get context about this fight in the fighter's career."""
        total_fights = FightHistory.objects.filter(
            fighter=obj.fighter
        ).count()
        
        context = {
            'fight_number': obj.fight_order,
            'total_career_fights': total_fights,
            'record_at_time': obj.fighter_record_at_time,
        }
        
        # Add significance indicators
        if obj.is_title_fight:
            context['significance'] = 'Title Fight'
        elif obj.fight_order == 1:
            context['significance'] = 'Professional Debut'
        elif obj.fight_order <= 5:
            context['significance'] = 'Early Career'
        
        return context


class FighterInterconnectedSerializer(serializers.ModelSerializer):
    """
    Enhanced fighter serializer that includes interconnected fight history
    with seamless legacy/live data integration.
    """
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    record_string = serializers.CharField(source='get_record_string', read_only=True)
    finish_rate = serializers.CharField(source='get_finish_rate', read_only=True)
    
    # Fight history with interconnected data
    fight_history = serializers.SerializerMethodField()
    recent_fights = serializers.SerializerMethodField()
    career_highlights = serializers.SerializerMethodField()
    
    # Data quality indicators
    interconnection_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Fighter
        fields = [
            # Basic information
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'birth_first_name', 'birth_last_name', 'nickname',
            'date_of_birth', 'birth_place', 'nationality',
            
            # Physical attributes
            'height_cm', 'weight_kg', 'reach_cm', 'stance',
            
            # Career information
            'fighting_out_of', 'team', 'years_active', 'is_active',
            
            # Media and links
            'profile_image_url', 'wikipedia_url', 'social_media',
            
            # Career statistics
            'wins', 'losses', 'draws', 'no_contests', 'record_string',
            'wins_by_ko', 'wins_by_tko', 'wins_by_submission', 'wins_by_decision',
            'finish_rate',
            
            # Interconnected data
            'fight_history', 'recent_fights', 'career_highlights',
            'interconnection_status',
            
            # Data quality
            'data_source', 'data_quality_score', 'last_data_update',
            'created_at', 'updated_at'
        ]
    
    def get_fight_history(self, obj):
        """Get complete fight history with interconnected data."""
        # Limit to recent fights in list view, allow full history in detail view
        request = self.context.get('request')
        is_detail_view = request and 'pk' in request.resolver_match.kwargs
        
        if is_detail_view:
            # Full history for detail view
            history = obj.fight_history.with_live_data().order_by('-fight_order')
        else:
            # Limited history for list view
            history = obj.fight_history.with_live_data().order_by('-fight_order')[:5]
        
        return InterconnectedFightHistorySerializer(
            history, 
            many=True, 
            context=self.context
        ).data
    
    def get_recent_fights(self, obj):
        """Get recent fights summary."""
        recent = obj.fight_history.recent(days=365).with_live_data()[:3]
        
        return [
            {
                'opponent': fight.get_live_opponent_name(),
                'result': fight.get_live_result(),
                'method': fight.get_live_method(),
                'date': fight.get_live_event_date(),
                'event': fight.get_live_event_name(),
                'is_interconnected': fight.is_interconnected()
            }
            for fight in recent
        ]
    
    def get_career_highlights(self, obj):
        """Get career highlights and significant fights."""
        highlights = []
        
        # Title fights
        title_fights = obj.fight_history.filter(is_title_fight=True).with_live_data()[:3]
        for fight in title_fights:
            highlights.append({
                'type': 'title_fight',
                'description': f"Title fight vs {fight.get_live_opponent_name()}",
                'result': fight.get_live_result(),
                'date': fight.get_live_event_date(),
                'is_interconnected': fight.is_interconnected()
            })
        
        # Debut fight
        debut = obj.fight_history.filter(fight_order=1).first()
        if debut:
            highlights.append({
                'type': 'debut',
                'description': f"Professional debut vs {debut.get_live_opponent_name()}",
                'result': debut.get_live_result(),
                'date': debut.get_live_event_date(),
                'is_interconnected': debut.is_interconnected()
            })
        
        # Notable finishes (KO/Sub wins)
        notable_finishes = obj.fight_history.filter(
            result='win'
        ).exclude(
            method__icontains='decision'
        ).with_live_data().order_by('-event_date')[:2]
        
        for fight in notable_finishes:
            highlights.append({
                'type': 'finish',
                'description': f"{fight.get_live_method()} win vs {fight.get_live_opponent_name()}",
                'result': fight.get_live_result(),
                'date': fight.get_live_event_date(),
                'is_interconnected': fight.is_interconnected()
            })
        
        return highlights[:5]  # Limit to 5 highlights
    
    def get_interconnection_status(self, obj):
        """Get status of fight history interconnection."""
        total_fights = obj.fight_history.count()
        interconnected_fights = obj.fight_history.interconnected().count()
        
        return {
            'total_fights': total_fights,
            'interconnected_fights': interconnected_fights,
            'interconnection_rate': (
                (interconnected_fights / total_fights * 100) 
                if total_fights > 0 else 0
            ),
            'legacy_only_fights': total_fights - interconnected_fights,
            'data_completeness': 'high' if interconnected_fights / total_fights > 0.8 else 
                                'medium' if interconnected_fights / total_fights > 0.5 else 'low'
        }


class FightInterconnectedSerializer(serializers.ModelSerializer):
    """
    Enhanced Fight serializer that shows connections to FightHistory perspectives.
    """
    
    event = EventSummarySerializer(read_only=True)
    participants = serializers.SerializerMethodField()
    history_perspectives = serializers.SerializerMethodField()
    weight_class_name = serializers.CharField(source='weight_class.name', read_only=True)
    organization_name = serializers.CharField(source='event.organization.name', read_only=True)
    
    class Meta:
        model = Fight
        fields = [
            'id', 'event', 'fight_order', 'weight_class_name', 'organization_name',
            'is_main_event', 'is_title_fight', 'is_interim_title', 'scheduled_rounds',
            'status', 'method', 'method_details', 'ending_round', 'ending_time',
            'referee', 'participants', 'history_perspectives',
            'performance_bonuses', 'notes', 'created_at', 'updated_at'
        ]
    
    def get_participants(self, obj):
        """Get fight participants with results."""
        participants = obj.participants.select_related('fighter').all()[:2]
        return [
            {
                'fighter': FighterSummarySerializer(p.fighter).data,
                'corner': p.corner,
                'result': p.result,
                'weigh_in_weight': p.weigh_in_weight,
                'purse': p.purse
            }
            for p in participants
        ]
    
    def get_history_perspectives(self, obj):
        """Get associated FightHistory perspectives for this fight."""
        perspectives = obj.get_history_perspectives()
        
        return [
            {
                'history_id': p.id,
                'fighter_id': p.perspective_fighter.id,
                'fighter_name': p.perspective_fighter.get_full_name(),
                'result': p.result,
                'data_source': p.data_source,
                'data_quality_score': float(p.data_quality_score),
                'has_conflicts': p.has_data_conflicts() is not None
            }
            for p in perspectives
        ]


class InterconnectionReportSerializer(serializers.Serializer):
    """Serializer for interconnection status reports."""
    
    summary = serializers.DictField()
    by_data_source = serializers.DictField()
    data_quality_distribution = serializers.DictField()
    recent_reconciliation_stats = serializers.DictField()
    
    # Additional computed fields
    recommendations = serializers.SerializerMethodField()
    next_steps = serializers.SerializerMethodField()
    
    def get_recommendations(self, obj):
        """Generate recommendations based on interconnection status."""
        summary = obj.get('summary', {})
        link_percentage = summary.get('link_percentage', 0)
        
        recommendations = []
        
        if link_percentage < 50:
            recommendations.append({
                'priority': 'high',
                'action': 'Run comprehensive reconciliation',
                'description': 'Low interconnection rate indicates many fights could be linked'
            })
        
        if link_percentage < 80:
            recommendations.append({
                'priority': 'medium', 
                'action': 'Create missing Fight records',
                'description': 'Some FightHistory records may not have corresponding Fight records'
            })
        
        if summary.get('unlinked_records', 0) > 100:
            recommendations.append({
                'priority': 'medium',
                'action': 'Review unlinked records',
                'description': 'Many records remain unlinked - may need manual review'
            })
        
        return recommendations
    
    def get_next_steps(self, obj):
        """Suggest next steps for improving interconnection."""
        return [
            'Run: python manage.py reconcile_fight_history',
            'Check consistency: python manage.py reconcile_fight_history --check-consistency',
            'Fix conflicts: python manage.py reconcile_fight_history --fix-conflicts',
            'Review manual matches needed for remaining unlinked records'
        ]