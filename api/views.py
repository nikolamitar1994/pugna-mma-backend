from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, F

from fighters.models import Fighter, FighterNameVariation, FightHistory, FighterRanking, FighterStatistics, RankingHistory
from organizations.models import Organization, WeightClass
from events.models import Event, Fight, FightStatistics
from content.models import Article, Category, Tag, ArticleFighter, ArticleEvent, ArticleOrganization
from content.permissions import EditorialWorkflowPermission, CanManageCategories, CanManageTags
from content.mixins import (
    EditorialWorkflowMixin, BulkActionsMixin, ContentAnalyticsMixin,
    AuthorArticlesMixin, StatusFilterMixin
)
from .serializers import (
    FighterListSerializer, FighterDetailSerializer, FighterCreateUpdateSerializer,
    FightHistoryListSerializer, FightHistoryDetailSerializer, FightHistoryCreateUpdateSerializer,
    OrganizationSerializer, WeightClassSerializer,
    EventListSerializer, EventDetailSerializer,
    FightListSerializer, FightDetailSerializer,
    FightStatisticsSerializer,
    # Ranking serializers
    FighterRankingListSerializer, FighterRankingDetailSerializer,
    FighterStatisticsSerializer, RankingHistorySerializer,
    # Content serializers
    ArticleListSerializer, ArticleDetailSerializer, ArticleCreateUpdateSerializer,
    CategorySerializer, CategoryTreeSerializer, TagSerializer,
    ArticleFighterSerializer, ArticleEventSerializer, ArticleOrganizationSerializer,
    DivisionalRankingSerializer, PoundForPoundRankingSerializer,
    FighterRankingStatsSerializer
)


class FighterViewSet(viewsets.ModelViewSet):
    """ViewSet for Fighter CRUD operations with advanced search"""
    
    queryset = Fighter.objects.all().select_related().prefetch_related('name_variations')
    
    # Use different serializers for different actions
    def get_serializer_class(self):
        if self.action == 'list':
            return FighterListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FighterCreateUpdateSerializer
        return FighterDetailSerializer
    
    # Filtering and search configuration
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'nationality': ['exact', 'icontains'],
        'stance': ['exact'],
        'is_active': ['exact'],
        'data_source': ['exact'],
        'wins': ['exact', 'gte', 'lte'],
        'losses': ['exact', 'gte', 'lte'],
    }
    search_fields = ['first_name', 'last_name', 'nickname', 'display_name']
    ordering_fields = ['last_name', 'first_name', 'wins', 'losses', 'created_at']
    ordering = ['last_name', 'first_name']
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search with structured name matching and performance optimization"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': [], 'count': 0, 'query': ''})
        
        # Performance: Use select_related to avoid N+1 queries
        fighters = self.get_queryset().select_related().prefetch_related('name_variations')
        
        # Strategy 1: Exact name matches (highest priority)
        exact_matches = fighters.filter(
            Q(first_name__iexact=query) |
            Q(last_name__iexact=query) |
            Q(nickname__iexact=query) |
            Q(display_name__iexact=query)
        )
        
        # Strategy 2: Name variation matches
        variation_matches = fighters.filter(
            name_variations__full_name_variation__iexact=query
        ).distinct()
        
        # Strategy 3: Full-text search with ranking
        search_vector = SearchVector('first_name', 'last_name', 'nickname', 'display_name')
        search_query = SearchQuery(query)
        fulltext_matches = fighters.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query, rank__gte=0.1).order_by('-rank')
        
        # Strategy 4: Fuzzy matching (contains) - last resort
        fuzzy_matches = fighters.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(nickname__icontains=query) |
            Q(display_name__icontains=query)
        )
        
        # Strategy 5: Partial name matching (first + last)
        query_parts = query.split()
        partial_matches = fighters.none()
        if len(query_parts) == 2:
            first_part, last_part = query_parts[0], query_parts[1]
            partial_matches = fighters.filter(
                Q(first_name__icontains=first_part, last_name__icontains=last_part) |
                Q(first_name__icontains=last_part, last_name__icontains=first_part)  # Handle "Last First" queries
            )
        
        # Combine results with priority ordering
        seen_ids = set()
        results = []
        result_metadata = []
        
        # Priority 1: Exact matches
        for fighter in exact_matches[:10]:  # Limit to prevent oversized responses
            if fighter.id not in seen_ids:
                results.append(fighter)
                result_metadata.append({'match_type': 'exact', 'confidence': 1.0})
                seen_ids.add(fighter.id)
        
        # Priority 2: Name variation matches
        for fighter in variation_matches[:10]:
            if fighter.id not in seen_ids:
                results.append(fighter)
                result_metadata.append({'match_type': 'variation', 'confidence': 0.9})
                seen_ids.add(fighter.id)
        
        # Priority 3: Partial name matches
        for fighter in partial_matches[:10]:
            if fighter.id not in seen_ids:
                results.append(fighter)
                result_metadata.append({'match_type': 'partial', 'confidence': 0.8})
                seen_ids.add(fighter.id)
        
        # Priority 4: Full-text matches
        for fighter in fulltext_matches[:15]:
            if fighter.id not in seen_ids:
                results.append(fighter)
                confidence = float(getattr(fighter, 'rank', 0.5))
                result_metadata.append({'match_type': 'fulltext', 'confidence': confidence})
                seen_ids.add(fighter.id)
        
        # Priority 5: Fuzzy matches (limited to prevent noise)
        for fighter in fuzzy_matches[:10]:
            if fighter.id not in seen_ids and len(results) < 30:
                results.append(fighter)
                result_metadata.append({'match_type': 'fuzzy', 'confidence': 0.3})
                seen_ids.add(fighter.id)
        
        # Serialize results with enhanced metadata
        serializer = FighterListSerializer(results, many=True)
        response_data = {
            'results': [],
            'count': len(results),
            'query': query,
            'search_strategies_used': len([m for m in result_metadata if results]),
            'max_confidence': max([m['confidence'] for m in result_metadata], default=0)
        }
        
        # Add metadata to each result
        for i, fighter_data in enumerate(serializer.data):
            if i < len(result_metadata):
                fighter_data.update(result_metadata[i])
            response_data['results'].append(fighter_data)
        
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    def fights(self, request, pk=None):
        """Get all fights for a specific fighter"""
        fighter = self.get_object()
        fights = Fight.objects.filter(
            participants__fighter=fighter
        ).select_related('event', 'weight_class').prefetch_related(
            'participants__fighter'
        ).order_by('-event__date')
        
        serializer = FightListSerializer(fights, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def fight_history(self, request, pk=None):
        """Get complete fight history for a specific fighter"""
        fighter = self.get_object()
        history = fighter.fight_history.select_related(
            'opponent_fighter', 'event', 'organization', 'weight_class'
        ).all()
        
        # Apply optional filtering
        result_filter = request.query_params.get('result')
        if result_filter:
            history = history.filter(result=result_filter)
        
        method_filter = request.query_params.get('method')
        if method_filter:
            history = history.filter(method__icontains=method_filter)
        
        organization_filter = request.query_params.get('organization')
        if organization_filter:
            history = history.filter(organization__abbreviation__iexact=organization_filter)
        
        title_fights_only = request.query_params.get('title_fights_only')
        if title_fights_only and title_fights_only.lower() == 'true':
            history = history.filter(is_title_fight=True)
        
        # Pagination
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = FightHistoryListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FightHistoryListSerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get career statistics for a fighter"""
        fighter = self.get_object()
        
        # Calculate additional statistics
        stats = {
            'career_record': {
                'wins': fighter.wins,
                'losses': fighter.losses,
                'draws': fighter.draws,
                'no_contests': fighter.no_contests,
                'total_fights': fighter.total_fights,
            },
            'win_methods': {
                'ko': fighter.wins_by_ko,
                'tko': fighter.wins_by_tko,
                'submission': fighter.wins_by_submission,
                'decision': fighter.wins_by_decision,
            },
            'finish_rate': fighter.get_finish_rate(),
            'activity': {
                'years_active': fighter.years_active,
                'is_active': fighter.is_active,
            }
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active fighters"""
        active_fighters = self.get_queryset().filter(is_active=True)
        
        # Apply pagination
        page = self.paginate_queryset(active_fighters)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(active_fighters, many=True)
        return Response(serializer.data)


class FightHistoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Fight History CRUD operations with advanced filtering"""
    
    queryset = FightHistory.objects.all().select_related(
        'fighter', 'opponent_fighter', 'event', 'organization', 'weight_class'
    )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FightHistoryListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FightHistoryCreateUpdateSerializer
        return FightHistoryDetailSerializer
    
    # Filtering and search configuration
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'fighter': ['exact'],
        'result': ['exact'],
        'method': ['exact', 'icontains'],
        'organization': ['exact'],
        'is_title_fight': ['exact'],
        'event_date': ['exact', 'gte', 'lte'],
        'data_source': ['exact'],
        'data_quality_score': ['gte', 'lte'],
    }
    search_fields = [
        'fighter__first_name', 'fighter__last_name', 'fighter__nickname',
        'opponent_first_name', 'opponent_last_name', 'opponent_full_name',
        'event_name', 'organization_name', 'location'
    ]
    ordering_fields = ['event_date', 'fight_order', 'data_quality_score']
    ordering = ['-event_date', '-fight_order']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent fight history records"""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now().date() - timedelta(days=90)
        recent_history = self.get_queryset().filter(event_date__gte=recent_date)
        
        page = self.paginate_queryset(recent_history)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def title_fights(self, request):
        """Get all title fight history records"""
        title_fights = self.get_queryset().filter(is_title_fight=True)
        
        page = self.paginate_queryset(title_fights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(title_fights, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_method(self, request):
        """Get fight history grouped by method"""
        method = request.query_params.get('method')
        if not method:
            return Response({'error': 'Method parameter is required'}, status=400)
        
        fights = self.get_queryset().filter(method__icontains=method)
        
        page = self.paginate_queryset(fights)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(fights, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get aggregate statistics from fight history"""
        from django.db.models import Count, Avg
        
        stats = self.get_queryset().aggregate(
            total_fights=Count('id'),
            avg_data_quality=Avg('data_quality_score'),
            title_fights=Count('id', filter=Q(is_title_fight=True)),
            finishes=Count('id', filter=~Q(method__icontains='decision')),
        )
        
        # Method breakdown
        method_stats = self.get_queryset().values('method').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Organization breakdown
        org_stats = self.get_queryset().values(
            'organization__name', 'organization__abbreviation'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        
        stats.update({
            'finish_rate': round((stats['finishes'] / stats['total_fights']) * 100, 1) if stats['total_fights'] > 0 else 0,
            'title_fight_percentage': round((stats['title_fights'] / stats['total_fights']) * 100, 1) if stats['total_fights'] > 0 else 0,
            'method_breakdown': list(method_stats),
            'organization_breakdown': list(org_stats)
        })
        
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create fight history records"""
        if not isinstance(request.data, list):
            return Response(
                {'error': 'Expected a list of fight history records'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = FightHistoryCreateUpdateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            fight_histories = serializer.save()
            response_serializer = FightHistoryListSerializer(fight_histories, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def data_quality_report(self, request):
        """Get data quality report for fight history records"""
        from django.db.models import Count, Avg
        
        # Quality score distribution
        quality_ranges = [
            ('excellent', 0.9, 1.0),
            ('good', 0.7, 0.89),
            ('fair', 0.5, 0.69),
            ('poor', 0.0, 0.49)
        ]
        
        quality_distribution = {}
        for label, min_score, max_score in quality_ranges:
            count = self.get_queryset().filter(
                data_quality_score__gte=min_score,
                data_quality_score__lte=max_score
            ).count()
            quality_distribution[label] = count
        
        # Missing data analysis
        missing_data = {
            'missing_opponent_fighter_link': self.get_queryset().filter(opponent_fighter__isnull=True).count(),
            'missing_event_link': self.get_queryset().filter(event__isnull=True).count(),
            'missing_organization_link': self.get_queryset().filter(organization__isnull=True).count(),
            'missing_weight_class_link': self.get_queryset().filter(weight_class__isnull=True).count(),
            'missing_method': self.get_queryset().filter(method='').count(),
            'missing_location': self.get_queryset().filter(location='').count(),
        }
        
        report = {
            'total_records': self.get_queryset().count(),
            'average_quality_score': self.get_queryset().aggregate(avg=Avg('data_quality_score'))['avg'],
            'quality_distribution': quality_distribution,
            'missing_data_analysis': missing_data,
            'data_source_breakdown': list(
                self.get_queryset().values('data_source').annotate(count=Count('id')).order_by('-count')
            )
        }
        
        return Response(report)


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Organization read operations"""
    
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'abbreviation']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def weight_classes(self, request, pk=None):
        """Get weight classes for an organization"""
        organization = self.get_object()
        weight_classes = organization.weight_classes.filter(is_active=True)
        serializer = WeightClassSerializer(weight_classes, many=True)
        return Response(serializer.data)


class WeightClassViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WeightClass read operations"""
    
    queryset = WeightClass.objects.filter(is_active=True).select_related('organization')
    serializer_class = WeightClassSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['organization', 'gender']
    ordering = ['organization', 'weight_limit_kg']


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Event operations"""
    
    queryset = Event.objects.all().select_related('organization').prefetch_related(
        'fights__participants__fighter', 'fights__weight_class'
    )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        return EventDetailSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'organization': ['exact'],
        'status': ['exact'],
        'date': ['exact', 'gte', 'lte'],
        'country': ['exact', 'icontains'],
    }
    search_fields = ['name', 'location', 'venue']
    ordering_fields = ['date', 'name']
    ordering = ['-date']
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events"""
        from django.utils import timezone
        
        upcoming_events = self.get_queryset().filter(
            date__gte=timezone.now().date(),
            status__in=['scheduled', 'live']
        )
        
        serializer = self.get_serializer(upcoming_events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent completed events"""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now().date() - timedelta(days=30)
        recent_events = self.get_queryset().filter(
            date__gte=recent_date,
            date__lt=timezone.now().date(),
            status='completed'
        )
        
        serializer = self.get_serializer(recent_events, many=True)
        return Response(serializer.data)


class FightViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Fight operations"""
    
    queryset = Fight.objects.all().select_related(
        'event', 'weight_class', 'winner'
    ).prefetch_related('participants__fighter')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FightListSerializer
        return FightDetailSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'event': ['exact'],
        'status': ['exact'],
        'is_main_event': ['exact'],
        'is_title_fight': ['exact'],
        'method': ['exact', 'icontains'],
    }
    ordering_fields = ['event__date', 'fight_order']
    ordering = ['-event__date', 'fight_order']
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get detailed statistics for a fight"""
        fight = self.get_object()
        try:
            stats = fight.statistics
            serializer = FightStatisticsSerializer(stats)
            return Response(serializer.data)
        except FightStatistics.DoesNotExist:
            return Response(
                {'detail': 'Statistics not available for this fight.'},
                status=status.HTTP_404_NOT_FOUND
            )


# Ranking ViewSets

class FighterRankingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Fighter Rankings with comprehensive filtering"""
    
    queryset = FighterRanking.objects.all().select_related(
        'fighter', 'weight_class', 'organization'
    ).prefetch_related('history')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FighterRankingListSerializer
        return FighterRankingDetailSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'ranking_type': ['exact'],
        'weight_class': ['exact'],
        'organization': ['exact'],
        'is_champion': ['exact'],
        'is_interim_champion': ['exact'],
        'current_rank': ['exact', 'lte', 'gte'],
    }
    ordering_fields = ['current_rank', 'ranking_score', 'calculation_date']
    ordering = ['current_rank']
    
    @action(detail=False, methods=['get'])
    def divisional(self, request):
        """Get divisional rankings for specific weight class and organization"""
        weight_class_id = request.query_params.get('weight_class')
        organization_id = request.query_params.get('organization')
        
        if not weight_class_id:
            return Response(
                {'error': 'weight_class parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_class = WeightClass.objects.get(id=weight_class_id)
        except WeightClass.DoesNotExist:
            return Response(
                {'error': 'Weight class not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        organization = None
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return Response(
                    {'error': 'Organization not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get rankings
        rankings = self.get_queryset().filter(
            ranking_type='divisional',
            weight_class=weight_class,
            organization=organization
        ).order_by('current_rank')[:15]  # Top 15
        
        # Get champion
        champion = rankings.filter(is_champion=True).first()
        interim_champion = rankings.filter(is_interim_champion=True).first()
        
        data = {
            'weight_class': WeightClassSerializer(weight_class).data,
            'organization': OrganizationSerializer(organization).data if organization else None,
            'rankings': FighterRankingListSerializer(rankings, many=True).data,
            'champion': FighterRankingListSerializer(champion).data if champion else None,
            'interim_champion': FighterRankingListSerializer(interim_champion).data if interim_champion else None,
            'last_updated': rankings.first().calculation_date if rankings else None,
            'total_fighters': rankings.count()
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def pound_for_pound(self, request):
        """Get pound-for-pound rankings"""
        organization_id = request.query_params.get('organization')
        
        organization = None
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id)
            except Organization.DoesNotExist:
                return Response(
                    {'error': 'Organization not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        rankings = self.get_queryset().filter(
            ranking_type='p4p',
            organization=organization
        ).order_by('current_rank')[:15]  # Top 15 P4P
        
        data = {
            'rankings': FighterRankingListSerializer(rankings, many=True).data,
            'organization': OrganizationSerializer(organization).data if organization else None,
            'last_updated': rankings.first().calculation_date if rankings else None,
            'total_fighters': rankings.count()
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def champions(self, request):
        """Get all current champions across divisions"""
        organization_id = request.query_params.get('organization')
        
        champions_query = self.get_queryset().filter(
            is_champion=True,
            ranking_type='divisional'
        ).select_related('weight_class', 'organization')
        
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id)
                champions_query = champions_query.filter(organization=organization)
            except Organization.DoesNotExist:
                return Response(
                    {'error': 'Organization not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        champions = champions_query.order_by('weight_class__weight_limit_kg')
        
        serializer = FighterRankingListSerializer(champions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_fighter(self, request):
        """Get all rankings for a specific fighter"""
        fighter_id = request.query_params.get('fighter')
        
        if not fighter_id:
            return Response(
                {'error': 'fighter parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fighter = Fighter.objects.get(id=fighter_id)
        except Fighter.DoesNotExist:
            return Response(
                {'error': 'Fighter not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get current divisional rankings
        divisional_rankings = self.get_queryset().filter(
            fighter=fighter,
            ranking_type='divisional'
        ).select_related('weight_class', 'organization')
        
        # Get P4P ranking
        p4p_ranking = self.get_queryset().filter(
            fighter=fighter,
            ranking_type='p4p'
        ).first()
        
        # Get statistics
        statistics = None
        if hasattr(fighter, 'statistics'):
            statistics = fighter.statistics
        
        data = {
            'fighter': FighterListSerializer(fighter).data,
            'divisional_rankings': FighterRankingListSerializer(divisional_rankings, many=True).data,
            'p4p_ranking': FighterRankingListSerializer(p4p_ranking).data if p4p_ranking else None,
            'statistics': FighterStatisticsSerializer(statistics).data if statistics else None
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def ranking_changes(self, request):
        """Get recent ranking changes across all divisions"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Get rankings with significant changes in last 30 days
        recent_date = timezone.now().date() - timedelta(days=30)
        
        rankings_with_changes = self.get_queryset().filter(
            calculation_date__gte=recent_date,
            previous_rank__isnull=False
        ).exclude(
            current_rank=F('previous_rank')  # Exclude no-change rankings
        ).order_by('-calculation_date', 'current_rank')
        
        serializer = FighterRankingListSerializer(rankings_with_changes, many=True)
        return Response(serializer.data)


class FighterStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Fighter Statistics"""
    
    queryset = FighterStatistics.objects.all().select_related('fighter', 'primary_weight_class')
    serializer_class = FighterStatisticsSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'fighter': ['exact'],
        'needs_recalculation': ['exact'],
        'current_streak': ['exact', 'gte', 'lte'],
        'finish_rate': ['gte', 'lte'],
        'total_fights': ['gte', 'lte'],
    }
    ordering_fields = [
        'finish_rate', 'current_streak', 'total_fights', 'wins', 
        'last_fight_date', 'win_percentage'
    ]
    ordering = ['-total_fights']
    
    @action(detail=False, methods=['get'])
    def leaderboards(self, request):
        """Get statistical leaderboards"""
        
        # Define leaderboard categories
        leaderboards = {
            'highest_finish_rate': self.get_queryset().filter(
                total_fights__gte=5  # Minimum 5 fights
            ).order_by('-finish_rate')[:10],
            
            'longest_win_streaks': self.get_queryset().filter(
                current_streak__gt=0
            ).order_by('-current_streak')[:10],
            
            'most_active': self.get_queryset().order_by('-fights_last_12_months')[:10],
            
            'most_title_fights': self.get_queryset().filter(
                title_fights__gt=0
            ).order_by('-title_fights')[:10],
            
            'best_win_percentage': self.get_queryset().filter(
                total_fights__gte=10  # Minimum 10 fights
            ).order_by('-wins', 'losses')[:10],
            
            'most_experienced': self.get_queryset().order_by('-total_fights')[:10],
        }
        
        # Serialize each leaderboard
        serialized_leaderboards = {}
        for category, queryset in leaderboards.items():
            serialized_leaderboards[category] = FighterStatisticsSerializer(
                queryset, many=True
            ).data
        
        return Response(serialized_leaderboards)
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Compare statistics between two fighters"""
        fighter1_id = request.query_params.get('fighter1')
        fighter2_id = request.query_params.get('fighter2')
        
        if not fighter1_id or not fighter2_id:
            return Response(
                {'error': 'Both fighter1 and fighter2 parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stats1 = self.get_queryset().get(fighter__id=fighter1_id)
            stats2 = self.get_queryset().get(fighter__id=fighter2_id)
        except FighterStatistics.DoesNotExist:
            return Response(
                {'error': 'One or both fighters not found or no statistics available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate head-to-head if they've fought
        head_to_head = FightHistory.objects.filter(
            Q(fighter=stats1.fighter, opponent_fighter=stats2.fighter) |
            Q(fighter=stats2.fighter, opponent_fighter=stats1.fighter)
        ).order_by('-event_date')
        
        comparison = {
            'fighter1': FighterStatisticsSerializer(stats1).data,
            'fighter2': FighterStatisticsSerializer(stats2).data,
            'head_to_head': FightHistoryListSerializer(head_to_head, many=True).data,
            'comparison_metrics': {
                'experience_edge': 'fighter1' if stats1.total_fights > stats2.total_fights else 'fighter2',
                'activity_edge': 'fighter1' if stats1.fights_last_12_months > stats2.fights_last_12_months else 'fighter2',
                'finishing_edge': 'fighter1' if stats1.finish_rate > stats2.finish_rate else 'fighter2',
                'streak_edge': 'fighter1' if stats1.current_streak > stats2.current_streak else 'fighter2',
            }
        }
        
        return Response(comparison)
    
    @action(detail=False, methods=['post'])
    def recalculate(self, request):
        """Trigger recalculation of fighter statistics"""
        fighter_id = request.data.get('fighter_id')
        
        if fighter_id:
            try:
                stats = self.get_queryset().get(fighter__id=fighter_id)
                stats.calculate_all_statistics()
                return Response(
                    {'message': f'Statistics recalculated for {stats.fighter.get_full_name()}'}
                )
            except FighterStatistics.DoesNotExist:
                return Response(
                    {'error': 'Fighter statistics not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Recalculate all pending statistics
            pending_stats = self.get_queryset().filter(needs_recalculation=True)
            count = 0
            
            for stats in pending_stats:
                stats.calculate_all_statistics()
                count += 1
            
            return Response(
                {'message': f'Recalculated statistics for {count} fighters'}
            )


class RankingHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Ranking History"""
    
    queryset = RankingHistory.objects.all().select_related(
        'fighter_ranking__fighter', 'fighter_ranking__weight_class', 
        'fighter_ranking__organization', 'trigger_fight'
    )
    serializer_class = RankingHistorySerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'fighter_ranking__fighter': ['exact'],
        'fighter_ranking__weight_class': ['exact'],
        'fighter_ranking__organization': ['exact'],
        'rank_on_date': ['exact', 'lte', 'gte'],
        'calculation_date': ['exact', 'gte', 'lte'],
        'rank_change': ['exact', 'gte', 'lte'],
    }
    ordering_fields = ['calculation_date', 'rank_on_date', 'rank_change']
    ordering = ['-calculation_date']
    
    @action(detail=False, methods=['get'])
    def biggest_moves(self, request):
        """Get biggest ranking movements (up and down)"""
        from django.db.models import F, Case, When
        
        # Get significant ranking changes
        biggest_moves = self.get_queryset().annotate(
            abs_change=Case(
                When(rank_change__gte=0, then=F('rank_change')),
                default=F('rank_change') * -1
            )
        ).filter(abs_change__gte=3).order_by('-abs_change')[:20]
        
        serializer = self.get_serializer(biggest_moves, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Get ranking timeline for a specific fighter"""
        fighter_id = request.query_params.get('fighter')
        weight_class_id = request.query_params.get('weight_class')
        
        if not fighter_id:
            return Response(
                {'error': 'fighter parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timeline_query = self.get_queryset().filter(
            fighter_ranking__fighter__id=fighter_id
        )
        
        if weight_class_id:
            timeline_query = timeline_query.filter(
                fighter_ranking__weight_class__id=weight_class_id
            )
        
        timeline = timeline_query.order_by('calculation_date')
        
        serializer = self.get_serializer(timeline, many=True)
        return Response(serializer.data)


# Content Management ViewSets

class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing content categories with editorial permissions.
    Provides category hierarchy and article counts.
    """
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [CanManageCategories]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    
    def get_serializer_class(self):
        """Use tree serializer for tree action"""
        if self.action == 'tree':
            return CategoryTreeSerializer
        return CategorySerializer
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category hierarchy as a tree structure"""
        root_categories = Category.objects.filter(
            parent=None, is_active=True
        ).order_by('order', 'name')
        
        serializer = CategoryTreeSerializer(root_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def articles(self, request, pk=None):
        """Get articles in this category"""
        category = self.get_object()
        articles = Article.objects.filter(
            category=category,
            status='published'
        ).order_by('-published_at')
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing content tags with editorial permissions.
    Provides tag usage statistics and related articles.
    """
    
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [CanManageTags]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['color']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'usage_count', 'created_at']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags by usage"""
        popular_tags = Tag.objects.filter(
            usage_count__gt=0
        ).order_by('-usage_count')[:20]
        
        serializer = self.get_serializer(popular_tags, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def articles(self, request, pk=None):
        """Get articles with this tag"""
        tag = self.get_object()
        articles = tag.articles.filter(
            status='published'
        ).order_by('-published_at')
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)


class ArticleViewSet(
    EditorialWorkflowMixin,
    BulkActionsMixin,
    ContentAnalyticsMixin,
    AuthorArticlesMixin,
    StatusFilterMixin,
    viewsets.ModelViewSet
):
    """
    ViewSet for managing articles with comprehensive filtering, search, and editorial workflow.
    
    Includes editorial workflow actions, bulk operations, analytics, and role-based permissions.
    """
    
    queryset = Article.objects.select_related('category', 'author', 'editor').prefetch_related('tags')
    permission_classes = [EditorialWorkflowPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'article_type', 'category', 'author', 'is_featured', 
        'is_breaking', 'allow_comments'
    ]
    search_fields = ['title', 'excerpt', 'content', 'meta_title', 'meta_description']
    ordering_fields = ['title', 'published_at', 'created_at', 'view_count']
    ordering = ['-published_at']
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        # Use editorial serializers with role-based field filtering
        if self.action == 'list':
            from content.serializers import EditorialArticleListSerializer
            return EditorialArticleListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            from content.serializers import EditorialArticleCreateUpdateSerializer
            return EditorialArticleCreateUpdateSerializer
        else:
            from content.serializers import EditorialArticleDetailSerializer
            return EditorialArticleDetailSerializer
    
    def perform_create(self, serializer):
        """Set author to current user when creating article"""
        serializer.save(author=self.request.user)
        
        # Log the creation
        from users.models import EditorialWorkflowLog
        article = serializer.instance
        EditorialWorkflowLog.log_action(
            article=article,
            user=self.request.user,
            action='create',
            notes='Article created'
        )
    
    def perform_update(self, serializer):
        """Log article updates"""
        old_status = serializer.instance.status
        serializer.save()
        
        # Log the update
        from users.models import EditorialWorkflowLog
        EditorialWorkflowLog.log_action(
            article=serializer.instance,
            user=self.request.user,
            action='edit',
            notes='Article updated'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when article is retrieved"""
        instance = self.get_object()
        
        # Only increment for published articles and non-authors
        if instance.status == 'published' and instance.author != request.user:
            instance.increment_view_count()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured articles"""
        featured_articles = self.get_queryset().filter(
            is_featured=True,
            status='published'
        ).order_by('-published_at')[:10]
        
        serializer = ArticleListSerializer(featured_articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def breaking(self, request):
        """Get breaking news articles"""
        breaking_articles = self.get_queryset().filter(
            is_breaking=True,
            status='published'
        ).order_by('-published_at')[:5]
        
        serializer = ArticleListSerializer(breaking_articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending articles based on recent views"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Articles with high views in the last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        trending_articles = self.get_queryset().filter(
            status='published',
            published_at__gte=week_ago
        ).order_by('-view_count')[:10]
        
        serializer = ArticleListSerializer(trending_articles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """Get articles related to this one"""
        article = self.get_object()
        related_articles = article.get_related_articles(limit=10)
        
        serializer = ArticleListSerializer(related_articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search across articles with PostgreSQL full-text search"""
        query = request.query_params.get('q', '')
        
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Use PostgreSQL full-text search
        search_query = SearchQuery(query)
        search_vector = SearchVector('title', weight='A') + \
                       SearchVector('excerpt', weight='B') + \
                       SearchVector('content', weight='C')
        
        results = self.get_queryset().filter(
            status='published'
        ).annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(
            search=search_query
        ).order_by('-rank', '-published_at')
        
        # Apply pagination
        page = self.paginate_queryset(results)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_fighter(self, request):
        """Get articles related to a specific fighter"""
        fighter_id = request.query_params.get('fighter')
        
        if not fighter_id:
            return Response({'error': 'fighter parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        articles = self.get_queryset().filter(
            fighter_relationships__fighter__id=fighter_id,
            status='published'
        ).distinct().order_by('-published_at')
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get articles related to a specific event"""
        event_id = request.query_params.get('event')
        
        if not event_id:
            return Response({'error': 'event parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        articles = self.get_queryset().filter(
            event_relationships__event__id=event_id,
            status='published'
        ).distinct().order_by('-published_at')
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = ArticleListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)


# Relationship ViewSets

class ArticleFighterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing article-fighter relationships"""
    
    queryset = ArticleFighter.objects.select_related('article', 'fighter')
    serializer_class = ArticleFighterSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['article', 'fighter', 'relationship_type']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order']


class ArticleEventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing article-event relationships"""
    
    queryset = ArticleEvent.objects.select_related('article', 'event')
    serializer_class = ArticleEventSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['article', 'event', 'relationship_type']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order']


class ArticleOrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing article-organization relationships"""
    
    queryset = ArticleOrganization.objects.select_related('article', 'organization')
    serializer_class = ArticleOrganizationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['article', 'organization', 'relationship_type']
    ordering_fields = ['display_order', 'created_at']
    ordering = ['display_order']