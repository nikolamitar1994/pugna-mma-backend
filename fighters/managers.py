"""
Enhanced managers for interconnected fight history system.

These managers provide seamless access to both legacy string-based data
and new interconnected Fight relationships.
"""

from django.db import models
from django.db.models import Q, F, Case, When, Value, Subquery, OuterRef
from django.db.models.functions import Coalesce


class InterconnectedFightHistoryManager(models.Manager):
    """
    Manager that seamlessly handles both legacy string-based data 
    and new interconnected Fight relationships.
    
    This manager provides methods to query fight history with automatic
    fallback between authoritative Fight data and stored string data.
    """
    
    def get_queryset(self):
        """Optimized queryset with all necessary relationships pre-loaded."""
        return super().get_queryset().select_related(
            'fighter',
            'perspective_fighter', 
            'authoritative_fight__event__organization',
            'opponent_fighter',
            'event__organization',
            'organization',
            'weight_class'
        ).prefetch_related(
            'authoritative_fight__participants__fighter'
        )
    
    def for_fighter(self, fighter):
        """
        Get all fight history for a fighter from both legacy and interconnected sources.
        
        Args:
            fighter: Fighter instance or fighter ID
            
        Returns:
            QuerySet of FightHistory records for this fighter
        """
        fighter_id = fighter.id if hasattr(fighter, 'id') else fighter
        
        return self.filter(
            Q(fighter_id=fighter_id) | Q(perspective_fighter_id=fighter_id)
        ).distinct()
    
    def interconnected(self):
        """Get only records linked to authoritative Fight records."""
        return self.filter(authoritative_fight__isnull=False)
    
    def legacy_only(self):
        """Get only legacy string-based records (not yet linked)."""
        return self.filter(authoritative_fight__isnull=True)
    
    def with_live_data(self):
        """
        Annotate queryset with live data from Fight records where available,
        falling back to stored string data.
        
        This provides a unified view where users get the most up-to-date
        information without knowing whether it comes from Fight or FightHistory.
        """
        from events.models import FightParticipant
        
        return self.annotate(
            # Live opponent name (from Fight if available, else stored name)
            live_opponent_name=Case(
                When(
                    authoritative_fight__isnull=False,
                    then=Subquery(
                        # Get opponent's name from the Fight participants
                        models.Model.objects.raw("""
                            SELECT f.display_name 
                            FROM fighters_fighter f
                            JOIN events_fightparticipant fp ON f.id = fp.fighter_id
                            WHERE fp.fight_id = %s 
                            AND f.id != %s
                            LIMIT 1
                        """, [OuterRef('authoritative_fight_id'), OuterRef('perspective_fighter_id')])
                    )
                ),
                default=F('opponent_full_name'),
                output_field=models.CharField()
            ),
            
            # Live event name (from Fight.event if available, else stored)
            live_event_name=Coalesce(
                'authoritative_fight__event__name',
                'event_name'
            ),
            
            # Live event date (from Fight.event if available, else stored)
            live_event_date=Coalesce(
                'authoritative_fight__event__date',
                'event_date'
            ),
            
            # Live result (from FightParticipant if available, else stored)
            live_result=Case(
                When(
                    authoritative_fight__isnull=False,
                    then=Subquery(
                        FightParticipant.objects.filter(
                            fight=OuterRef('authoritative_fight'),
                            fighter=OuterRef('perspective_fighter')
                        ).values('result')[:1]
                    )
                ),
                default=F('result'),
                output_field=models.CharField()
            ),
            
            # Live method (from Fight if available, else stored)
            live_method=Coalesce(
                'authoritative_fight__method',
                'method'
            ),
            
            # Live location (from Fight.event if available, else stored)
            live_location=Coalesce(
                'authoritative_fight__event__location',
                'location'
            ),
            
            # Data freshness indicator
            data_freshness=Case(
                When(authoritative_fight__isnull=False, then=Value('live')),
                default=Value('historical'),
                output_field=models.CharField()
            ),
            
            # Interconnection status
            is_interconnected=Case(
                When(authoritative_fight__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            )
        )
    
    def recent(self, days=90):
        """Get recent fight history within specified days."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() - timedelta(days=days)
        return self.filter(
            Q(event_date__gte=cutoff_date) |
            Q(authoritative_fight__event__date__gte=cutoff_date)
        )
    
    def title_fights(self):
        """Get only title fight records."""
        return self.filter(
            Q(is_title_fight=True) |
            Q(authoritative_fight__is_title_fight=True)
        )
    
    def by_method(self, method):
        """Filter by fight method, checking both stored and live data."""
        return self.filter(
            Q(method__icontains=method) |
            Q(authoritative_fight__method__icontains=method)
        )
    
    def by_result(self, result):
        """Filter by fight result, checking both stored and live data."""
        return self.filter(result=result)  # Result should always be from perspective
    
    def by_organization(self, organization):
        """Filter by organization, checking both stored and live data."""
        if hasattr(organization, 'id'):
            org_id = organization.id
        else:
            org_id = organization
            
        return self.filter(
            Q(organization_id=org_id) |
            Q(authoritative_fight__event__organization_id=org_id)
        )
    
    def inconsistent_data(self):
        """
        Find records where stored data conflicts with authoritative data.
        Useful for data quality monitoring.
        """
        return self.filter(
            authoritative_fight__isnull=False
        ).exclude(
            # Check for date consistency
            event_date=F('authoritative_fight__event__date')
        ).union(
            # Check for method consistency  
            self.filter(
                authoritative_fight__isnull=False,
                authoritative_fight__method__isnull=False
            ).exclude(
                method=F('authoritative_fight__method')
            )
        )
    
    def needs_reconciliation(self):
        """
        Get records that could potentially be linked to Fight records
        but aren't yet linked.
        """
        return self.filter(
            authoritative_fight__isnull=True,
            event__isnull=False  # Has event reference for matching
        )
    
    def data_quality_report(self):
        """
        Get aggregated data quality statistics.
        """
        from django.db.models import Avg, Count, Q
        
        return self.aggregate(
            total_records=Count('id'),
            interconnected_count=Count('id', filter=Q(authoritative_fight__isnull=False)),
            legacy_count=Count('id', filter=Q(authoritative_fight__isnull=True)),
            avg_quality_score=Avg('data_quality_score'),
            high_quality_count=Count('id', filter=Q(data_quality_score__gte=0.8)),
            low_quality_count=Count('id', filter=Q(data_quality_score__lt=0.5))
        )


class FighterQuerySet(models.QuerySet):
    """Enhanced QuerySet for Fighter model with fight history optimization."""
    
    def with_fight_stats(self):
        """Annotate fighters with calculated fight statistics."""
        return self.annotate(
            total_fight_history=Count('fight_history'),
            interconnected_fights=Count(
                'fight_history', 
                filter=Q(fight_history__authoritative_fight__isnull=False)
            ),
            recent_fights=Count(
                'fight_history',
                filter=Q(fight_history__event_date__gte=timezone.now().date() - timezone.timedelta(days=365))
            )
        )
    
    def with_complete_profiles(self):
        """Filter fighters with complete profile data."""
        return self.filter(
            data_quality_score__gte=0.8,
            total_fights__gt=0
        )


class FighterManager(models.Manager):
    """Enhanced manager for Fighter model."""
    
    def get_queryset(self):
        return FighterQuerySet(self.model, using=self._db)
    
    def with_fight_stats(self):
        return self.get_queryset().with_fight_stats()
    
    def with_complete_profiles(self):
        return self.get_queryset().with_complete_profiles()
    
    def active_fighters(self):
        """Get active fighters with recent fight activity."""
        from django.utils import timezone
        from datetime import timedelta
        
        recent_date = timezone.now().date() - timedelta(days=730)  # 2 years
        
        return self.filter(
            Q(is_active=True) |
            Q(fight_history__event_date__gte=recent_date)
        ).distinct()
    
    def search_by_name(self, query):
        """Enhanced name search including variations."""
        return self.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(display_name__icontains=query) |
            Q(nickname__icontains=query) |
            Q(name_variations__full_name_variation__icontains=query)
        ).distinct()