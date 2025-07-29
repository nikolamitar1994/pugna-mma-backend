from rest_framework import serializers
from fighters.models import Fighter, FighterNameVariation, FightHistory, FighterRanking, FighterStatistics, RankingHistory
from organizations.models import Organization, WeightClass
from events.models import Event, Fight, FightParticipant, FightStatistics
from content.models import Article, Category, Tag, ArticleFighter, ArticleEvent, ArticleOrganization


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for MMA organizations"""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'abbreviation', 'founded_date',
            'headquarters', 'website', 'logo_url', 'is_active'
        ]


class WeightClassSerializer(serializers.ModelSerializer):
    """Serializer for weight classes"""
    
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = WeightClass
        fields = [
            'id', 'organization', 'name', 'weight_limit_lbs',
            'weight_limit_kg', 'gender', 'is_active'
        ]


class FighterNameVariationSerializer(serializers.ModelSerializer):
    """Serializer for fighter name variations"""
    
    class Meta:
        model = FighterNameVariation
        fields = [
            'id', 'first_name_variation', 'last_name_variation', 
            'full_name_variation', 'variation_type', 'source'
        ]


class FighterListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for fighter lists"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    record = serializers.CharField(source='get_record_string', read_only=True)
    finish_rate = serializers.DecimalField(
        source='get_finish_rate', max_digits=4, decimal_places=1, read_only=True
    )
    
    class Meta:
        model = Fighter
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'nickname',
            'nationality', 'record', 'finish_rate', 'is_active'
        ]


class FightHistoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for fight history lists"""
    
    opponent_display = serializers.CharField(source='get_opponent_display_name', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    finish_details = serializers.CharField(source='get_finish_details', read_only=True)
    is_finish = serializers.BooleanField(source='is_finish', read_only=True)
    
    class Meta:
        model = FightHistory
        fields = [
            'id', 'fight_order', 'result', 'fighter_record_at_time',
            'opponent_display', 'opponent_fighter', 'method', 'method_display',
            'event_name', 'event_date', 'ending_round', 'ending_time',
            'finish_details', 'is_finish', 'location_display',
            'is_title_fight', 'data_quality_score'
        ]


class FightHistoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual fight history records"""
    
    fighter = FighterListSerializer(read_only=True)
    opponent_display = serializers.CharField(source='get_opponent_display_name', read_only=True)
    opponent_fighter = FighterListSerializer(read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    finish_details = serializers.CharField(source='get_finish_details', read_only=True)
    is_finish = serializers.BooleanField(source='is_finish', read_only=True)
    organization = OrganizationSerializer(read_only=True)
    weight_class = WeightClassSerializer(read_only=True)
    event = serializers.SerializerMethodField()
    
    class Meta:
        model = FightHistory
        fields = [
            'id', 'fighter', 'fight_order', 'result', 'fighter_record_at_time',
            'opponent_first_name', 'opponent_last_name', 'opponent_display',
            'opponent_full_name', 'opponent_fighter', 'method', 'method_display',
            'method_details', 'event_name', 'event_date', 'event',
            'ending_round', 'ending_time', 'scheduled_rounds', 'finish_details',
            'is_finish', 'location', 'venue', 'city', 'state', 'country',
            'location_display', 'weight_class_name', 'weight_class',
            'is_title_fight', 'is_interim_title', 'title_belt',
            'organization_name', 'organization', 'notes', 'performance_bonuses',
            'data_source', 'source_url', 'data_quality_score',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'opponent_display', 'method_display', 'location_display',
            'finish_details', 'is_finish', 'data_quality_score',
            'created_at', 'updated_at'
        ]
    
    def get_event(self, obj):
        """Get event details if linked"""
        if obj.event:
            return {
                'id': obj.event.id,
                'name': obj.event.name,
                'date': obj.event.date,
                'organization': obj.event.organization.name if obj.event.organization else None
            }
        return None


class FightHistoryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating fight history records"""
    
    class Meta:
        model = FightHistory
        fields = [
            'fighter', 'fight_order', 'result', 'fighter_record_at_time',
            'opponent_first_name', 'opponent_last_name', 'opponent_full_name',
            'opponent_fighter', 'method', 'method_details', 'event_name',
            'event_date', 'event', 'ending_round', 'ending_time',
            'scheduled_rounds', 'location', 'venue', 'city', 'state', 'country',
            'weight_class_name', 'weight_class', 'is_title_fight',
            'is_interim_title', 'title_belt', 'organization_name',
            'organization', 'notes', 'performance_bonuses', 'data_source',
            'source_url'
        ]
    
    def validate_fight_order(self, value):
        """Validate fight order is unique for the fighter"""
        if value < 1:
            raise serializers.ValidationError("Fight order must be positive.")
        
        # Check uniqueness for the fighter
        fighter = self.initial_data.get('fighter')
        if fighter:
            existing = FightHistory.objects.filter(
                fighter=fighter, fight_order=value
            ).exclude(id=self.instance.id if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError(
                    f"Fight order {value} already exists for this fighter."
                )
        
        return value
    
    def validate_event_date(self, value):
        """Validate event date is reasonable"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Event date cannot be in the future.")
        if value.year < 1990:
            raise serializers.ValidationError("Event date must be after 1990.")
        return value
    
    def validate_ending_time(self, value):
        """Validate ending time format"""
        if value:
            import re
            if not re.match(r'^\d{1,2}:\d{2}$', value):
                raise serializers.ValidationError(
                    "Ending time must be in MM:SS format (e.g., '4:32')."
                )
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Ensure opponent name fields are consistent
        if not data.get('opponent_full_name'):
            first = data.get('opponent_first_name', '')
            last = data.get('opponent_last_name', '')
            if first and last:
                data['opponent_full_name'] = f"{first} {last}"
            elif first:
                data['opponent_full_name'] = first
            else:
                raise serializers.ValidationError(
                    "Either opponent_full_name or opponent_first_name must be provided."
                )
        
        return data


class FighterDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual fighter profiles"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    record = serializers.CharField(source='get_record_string', read_only=True)
    finish_rate = serializers.DecimalField(
        source='get_finish_rate', max_digits=4, decimal_places=1, read_only=True
    )
    name_variations = FighterNameVariationSerializer(many=True, read_only=True)
    fight_history = serializers.SerializerMethodField()
    recent_fights = serializers.SerializerMethodField()
    recent_articles = serializers.SerializerMethodField()
    
    class Meta:
        model = Fighter
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'birth_first_name', 'birth_last_name', 'nickname',
            'date_of_birth', 'birth_place', 'nationality',
            'height_cm', 'weight_kg', 'reach_cm', 'stance',
            'fighting_out_of', 'team', 'years_active', 'is_active',
            'profile_image_url', 'wikipedia_url', 'social_media',
            'total_fights', 'wins', 'losses', 'draws', 'no_contests',
            'wins_by_ko', 'wins_by_tko', 'wins_by_submission', 'wins_by_decision',
            'record', 'finish_rate', 'name_variations', 'fight_history',
            'recent_fights', 'recent_articles', 'data_source', 'data_quality_score',
            'last_data_update', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'full_name', 'display_name', 'record', 'finish_rate',
            'fight_history', 'recent_fights', 'created_at', 'updated_at',
            'last_data_update'
        ]
    
    def get_fight_history(self, obj):
        """Get complete fight history summary"""
        history = obj.fight_history.all()[:5]  # Last 5 fights
        return FightHistoryListSerializer(history, many=True).data
    
    def get_recent_fights(self, obj):
        """Get recent fights count by result"""
        recent_history = obj.fight_history.all()[:10]  # Last 10 fights
        results = {'wins': 0, 'losses': 0, 'draws': 0, 'no_contests': 0}
        
        for fight in recent_history:
            if fight.result in results:
                results[fight.result + 's'] += 1
        
        return results
    
    def get_recent_articles(self, obj):
        """Get recent articles about this fighter"""
        from content.models import Article
        recent_articles = Article.objects.filter(
            fighter_relationships__fighter=obj,
            status='published'
        ).order_by('-published_at')[:5]
        
        return [
            {
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'excerpt': article.excerpt,
                'published_at': article.published_at,
                'article_type': article.article_type
            }
            for article in recent_articles
        ]


class FighterCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating fighters with validation"""
    
    class Meta:
        model = Fighter
        fields = [
            'first_name', 'last_name', 'nickname',
            'birth_first_name', 'birth_last_name',
            'date_of_birth', 'birth_place', 'nationality',
            'height_cm', 'weight_kg', 'reach_cm', 'stance',
            'fighting_out_of', 'team', 'years_active', 'is_active',
            'profile_image_url', 'wikipedia_url', 'social_media'
        ]
    
    def validate_first_name(self, value):
        """Validate first name is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("First name is required.")
        return value.strip()
    
    def validate_height_cm(self, value):
        """Validate height is reasonable"""
        if value and (value < 120 or value > 250):
            raise serializers.ValidationError("Height must be between 120cm and 250cm.")
        return value
    
    def validate_weight_kg(self, value):
        """Validate weight is reasonable"""
        if value and (value < 40 or value > 200):
            raise serializers.ValidationError("Weight must be between 40kg and 200kg.")
        return value


class FightParticipantSerializer(serializers.ModelSerializer):
    """Serializer for fight participants"""
    
    fighter = FighterListSerializer(read_only=True)
    
    class Meta:
        model = FightParticipant
        fields = [
            'id', 'fighter', 'corner', 'result', 'weigh_in_weight', 'purse'
        ]


class FightListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for fight lists"""
    
    participants = FightParticipantSerializer(many=True, read_only=True)
    weight_class = WeightClassSerializer(read_only=True)
    winner = FighterListSerializer(read_only=True)
    
    class Meta:
        model = Fight
        fields = [
            'id', 'fight_order', 'weight_class', 'participants',
            'is_main_event', 'is_title_fight', 'scheduled_rounds',
            'status', 'winner', 'method', 'ending_round', 'ending_time'
        ]


class FightDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual fights"""
    
    participants = FightParticipantSerializer(many=True, read_only=True)
    weight_class = WeightClassSerializer(read_only=True)
    winner = FighterListSerializer(read_only=True)
    
    class Meta:
        model = Fight
        fields = [
            'id', 'fight_order', 'weight_class', 'participants',
            'is_main_event', 'is_title_fight', 'is_interim_title',
            'scheduled_rounds', 'status', 'winner', 'method', 'method_details',
            'ending_round', 'ending_time', 'referee', 'performance_bonuses',
            'notes', 'created_at', 'updated_at'
        ]


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for event lists"""
    
    organization = OrganizationSerializer(read_only=True)
    fight_count = serializers.IntegerField(source='get_fight_count', read_only=True)
    main_event = serializers.CharField(source='get_main_event', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'organization', 'name', 'event_number', 'date',
            'location', 'venue', 'status', 'fight_count', 'main_event'
        ]


class EventDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual events"""
    
    organization = OrganizationSerializer(read_only=True)
    fights = FightListSerializer(many=True, read_only=True)
    fight_count = serializers.IntegerField(source='get_fight_count', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'organization', 'name', 'event_number', 'date',
            'location', 'venue', 'city', 'state', 'country',
            'attendance', 'gate_revenue', 'ppv_buys', 'broadcast_info',
            'status', 'poster_url', 'wikipedia_url', 'fights', 'fight_count',
            'created_at', 'updated_at'
        ]


class FightStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for fight statistics"""
    
    fighter1 = FighterListSerializer(read_only=True)
    fighter2 = FighterListSerializer(read_only=True)
    
    class Meta:
        model = FightStatistics
        fields = [
            'id', 'fighter1', 'fighter2',
            'fighter1_strikes_landed', 'fighter1_strikes_attempted',
            'fighter2_strikes_landed', 'fighter2_strikes_attempted',
            'fighter1_takedowns', 'fighter1_takedown_attempts',
            'fighter2_takedowns', 'fighter2_takedown_attempts',
            'fighter1_control_time', 'fighter2_control_time',
            'detailed_stats'
        ]


# Ranking Serializers

class FighterStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for fighter statistics"""
    
    fighter = FighterListSerializer(read_only=True)
    record_display = serializers.CharField(source='get_record_display', read_only=True)
    win_percentage = serializers.DecimalField(
        source='get_win_percentage', max_digits=4, decimal_places=1, read_only=True
    )
    
    class Meta:
        model = FighterStatistics
        fields = [
            'id', 'fighter', 'total_fights', 'wins', 'losses', 'draws', 'no_contests',
            'record_display', 'win_percentage',
            'wins_ko', 'wins_tko', 'wins_submission', 'wins_decision', 'wins_other',
            'losses_ko', 'losses_tko', 'losses_submission', 'losses_decision', 'losses_other',
            'finish_rate', 'finish_resistance', 'average_fight_time',
            'current_streak', 'longest_win_streak', 'longest_losing_streak',
            'fights_last_12_months', 'fights_last_24_months', 'fights_last_36_months',
            'last_fight_date', 'days_since_last_fight',
            'title_fights', 'title_wins', 'main_events', 'top_5_wins', 'top_10_wins',
            'performance_bonuses', 'fight_bonuses', 'total_bonuses',
            'primary_weight_class', 'weight_classes_fought',
            'debut_date', 'career_length_days', 'age_at_debut', 'current_age',
            'strength_of_schedule', 'signature_wins', 'quality_losses',
            'last_calculated', 'needs_recalculation'
        ]


class RankingHistorySerializer(serializers.ModelSerializer):
    """Serializer for ranking history"""
    
    change_display = serializers.CharField(source='get_change_display', read_only=True)
    
    class Meta:
        model = RankingHistory
        fields = [
            'id', 'rank_on_date', 'ranking_score', 'calculation_date',
            'rank_change', 'change_display', 'trigger_event', 'trigger_fight'
        ]


class FighterRankingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ranking lists"""
    
    fighter = FighterListSerializer(read_only=True)
    weight_class = WeightClassSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    rank_change_display = serializers.CharField(source='get_rank_change_display', read_only=True)
    
    class Meta:
        model = FighterRanking
        fields = [
            'id', 'fighter', 'ranking_type', 'weight_class', 'organization',
            'current_rank', 'previous_rank', 'ranking_score', 'rank_change_display',
            'is_champion', 'is_interim_champion', 'calculation_date'
        ]


class FighterRankingDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual fighter rankings"""
    
    fighter = FighterDetailSerializer(read_only=True)
    weight_class = WeightClassSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    rank_change = serializers.IntegerField(source='get_rank_change', read_only=True)
    rank_change_display = serializers.CharField(source='get_rank_change_display', read_only=True)
    history = RankingHistorySerializer(many=True, read_only=True)
    fighter_statistics = serializers.SerializerMethodField()
    
    class Meta:
        model = FighterRanking
        fields = [
            'id', 'fighter', 'ranking_type', 'weight_class', 'organization',
            'current_rank', 'previous_rank', 'ranking_score', 'rank_change',
            'rank_change_display', 'record_score', 'opponent_quality_score',
            'activity_score', 'performance_score', 'calculation_date',
            'manual_adjustment', 'is_champion', 'is_interim_champion',
            'history', 'fighter_statistics', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'ranking_score', 'record_score', 'opponent_quality_score',
            'activity_score', 'performance_score', 'calculation_date',
            'rank_change', 'rank_change_display', 'history', 'fighter_statistics'
        ]
    
    def get_fighter_statistics(self, obj):
        """Get fighter statistics if available"""
        if hasattr(obj.fighter, 'statistics'):
            return FighterStatisticsSerializer(obj.fighter.statistics).data
        return None


class DivisionalRankingSerializer(serializers.Serializer):
    """Serializer for divisional ranking views"""
    
    weight_class = WeightClassSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    rankings = FighterRankingListSerializer(many=True, read_only=True)
    champion = FighterRankingListSerializer(read_only=True)
    interim_champion = FighterRankingListSerializer(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)
    total_fighters = serializers.IntegerField(read_only=True)


class PoundForPoundRankingSerializer(serializers.Serializer):
    """Serializer for pound-for-pound ranking views"""
    
    rankings = FighterRankingListSerializer(many=True, read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)
    total_fighters = serializers.IntegerField(read_only=True)


class FighterRankingStatsSerializer(serializers.Serializer):
    """Serializer for fighter ranking statistics and comparisons"""
    
    fighter = FighterListSerializer(read_only=True)
    divisional_rankings = FighterRankingListSerializer(many=True, read_only=True)
    p4p_ranking = FighterRankingListSerializer(read_only=True)
    statistics = FighterStatisticsSerializer(read_only=True)
    ranking_history_summary = serializers.SerializerMethodField()
    best_career_ranking = serializers.SerializerMethodField()
    
    def get_ranking_history_summary(self, obj):
        """Get summary of ranking changes"""
        fighter = obj['fighter'] if isinstance(obj, dict) else obj.fighter
        
        # Get recent ranking changes
        recent_history = RankingHistory.objects.filter(
            fighter_ranking__fighter=fighter
        ).order_by('-calculation_date')[:10]
        
        return RankingHistorySerializer(recent_history, many=True).data
    
    def get_best_career_ranking(self, obj):
        """Get best career ranking across all divisions"""
        fighter = obj['fighter'] if isinstance(obj, dict) else obj.fighter
        
        best_ranking = FighterRanking.objects.filter(
            fighter=fighter,
            ranking_type='divisional'
        ).order_by('current_rank').first()
        
        if best_ranking:
            return FighterRankingListSerializer(best_ranking).data
        return None


# Content Management Serializers

class TagSerializer(serializers.ModelSerializer):
    """Serializer for content tags"""
    
    class Meta:
        model = Tag
        fields = [
            'id', 'name', 'slug', 'description', 'color', 'usage_count'
        ]


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for content categories"""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    article_count = serializers.SerializerMethodField()
    full_path = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'order', 'is_active', 'article_count', 'full_path'
        ]
    
    def get_article_count(self, obj):
        """Get count of published articles in this category"""
        return obj.get_article_count()
    
    def get_full_path(self, obj):
        """Get full hierarchical path"""
        return obj.get_full_path()


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Serializer for category hierarchy (tree structure)"""
    
    children = serializers.SerializerMethodField()
    article_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'order', 
            'is_active', 'article_count', 'children'
        ]
    
    def get_children(self, obj):
        """Get child categories"""
        children = obj.children.filter(is_active=True).order_by('order', 'name')
        return CategoryTreeSerializer(children, many=True).data
    
    def get_article_count(self, obj):
        """Get count of published articles in this category"""
        return obj.get_article_count()


class ArticleListSerializer(serializers.ModelSerializer):
    """Serializer for article listings"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reading_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'category_name', 'tags',
            'article_type', 'status', 'author_name', 'featured_image',
            'is_featured', 'is_breaking', 'view_count', 'reading_time',
            'reading_time_display', 'published_at', 'created_at'
        ]
    
    def get_reading_time_display(self, obj):
        """Format reading time for display"""
        if obj.reading_time <= 1:
            return "< 1 min read"
        return f"{obj.reading_time} min read"


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual articles"""
    
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    editor_name = serializers.CharField(source='editor.get_full_name', read_only=True)
    
    # Related content
    related_fighters = serializers.SerializerMethodField()
    related_events = serializers.SerializerMethodField()
    related_organizations = serializers.SerializerMethodField()
    related_articles = serializers.SerializerMethodField()
    
    # SEO fields
    seo_title = serializers.CharField(source='get_seo_title', read_only=True)
    seo_description = serializers.CharField(source='get_seo_description', read_only=True)
    featured_image_url = serializers.CharField(source='get_featured_image_url', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'category', 'tags',
            'article_type', 'status', 'author_name', 'editor_name',
            'featured_image', 'featured_image_url', 'featured_image_alt', 'featured_image_caption',
            'is_featured', 'is_breaking', 'allow_comments', 'view_count', 'reading_time',
            'published_at', 'created_at', 'updated_at',
            'seo_title', 'seo_description',
            'related_fighters', 'related_events', 'related_organizations', 'related_articles'
        ]
    
    def get_related_fighters(self, obj):
        """Get fighters related to this article"""
        from .serializers import FighterListSerializer
        relationships = obj.fighter_relationships.select_related('fighter').order_by('display_order')
        return [
            {
                'fighter': FighterListSerializer(rel.fighter).data,
                'relationship_type': rel.relationship_type
            }
            for rel in relationships
        ]
    
    def get_related_events(self, obj):
        """Get events related to this article"""
        relationships = obj.event_relationships.select_related('event').order_by('display_order')
        return [
            {
                'event': {
                    'id': rel.event.id,
                    'name': rel.event.name,
                    'date': rel.event.date,
                    'location': rel.event.location
                },
                'relationship_type': rel.relationship_type
            }
            for rel in relationships
        ]
    
    def get_related_organizations(self, obj):
        """Get organizations related to this article"""
        relationships = obj.organization_relationships.select_related('organization').order_by('display_order')
        return [
            {
                'organization': OrganizationSerializer(rel.organization).data,
                'relationship_type': rel.relationship_type
            }
            for rel in relationships
        ]
    
    def get_related_articles(self, obj):
        """Get related articles"""
        related = obj.get_related_articles(limit=5)
        return ArticleListSerializer(related, many=True).data


class ArticleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating articles"""
    
    class Meta:
        model = Article
        fields = [
            'title', 'slug', 'excerpt', 'content', 'category', 'tags',
            'article_type', 'status', 'featured_image', 'featured_image_alt',
            'featured_image_caption', 'meta_title', 'meta_description',
            'is_featured', 'is_breaking', 'allow_comments', 'published_at'
        ]
        extra_kwargs = {
            'slug': {'required': False},  # Auto-generated if not provided
        }
    
    def create(self, validated_data):
        """Create article with current user as author"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        return super().create(validated_data)


# Relationship Serializers

class ArticleFighterSerializer(serializers.ModelSerializer):
    """Serializer for article-fighter relationships"""
    
    article_title = serializers.CharField(source='article.title', read_only=True)
    fighter_name = serializers.CharField(source='fighter.get_full_name', read_only=True)
    
    class Meta:
        model = ArticleFighter
        fields = [
            'id', 'article', 'article_title', 'fighter', 'fighter_name',
            'relationship_type', 'display_order'
        ]


class ArticleEventSerializer(serializers.ModelSerializer):
    """Serializer for article-event relationships"""
    
    article_title = serializers.CharField(source='article.title', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = ArticleEvent
        fields = [
            'id', 'article', 'article_title', 'event', 'event_name',
            'relationship_type', 'display_order'
        ]


class ArticleOrganizationSerializer(serializers.ModelSerializer):
    """Serializer for article-organization relationships"""
    
    article_title = serializers.CharField(source='article.title', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = ArticleOrganization
        fields = [
            'id', 'article', 'article_title', 'organization', 'organization_name',
            'relationship_type', 'display_order'
        ]