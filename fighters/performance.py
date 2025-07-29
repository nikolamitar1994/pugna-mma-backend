"""
Fighter Profile Management - Performance Optimization Module

This module provides performance optimization utilities for fighter management,
including search optimization, database query optimization, and caching strategies.
"""

from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from fighters.models import Fighter, FighterNameVariation
import hashlib
import time
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FighterSearchOptimizer:
    """Optimized search functionality for fighters"""
    
    # Cache configuration
    SEARCH_CACHE_PREFIX = 'fighter_search'
    SEARCH_CACHE_TTL = 300  # 5 minutes
    PROFILE_CACHE_TTL = 1800  # 30 minutes
    
    @classmethod
    def get_search_cache_key(cls, query: str, filters: Dict = None) -> str:
        """Generate cache key for search results"""
        cache_data = {
            'query': query.lower().strip(),
            'filters': filters or {}
        }
        cache_string = str(sorted(cache_data.items()))
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"{cls.SEARCH_CACHE_PREFIX}:{cache_hash}"
    
    @classmethod
    def get_optimized_queryset(cls):
        """Get optimized queryset with proper joins"""
        return Fighter.objects.select_related().prefetch_related(
            Prefetch(
                'name_variations',
                queryset=FighterNameVariation.objects.select_related('fighter')
            )
        )
    
    @classmethod
    def search_fighters_cached(cls, query: str, limit: int = 30) -> Dict:
        """Cached fighter search with performance monitoring"""
        start_time = time.time()
        
        if not query or not query.strip():
            return {
                'results': [],
                'count': 0,
                'query': query,
                'cache_hit': False,
                'search_time_ms': 0
            }
        
        query = query.strip()
        cache_key = cls.get_search_cache_key(query)
        
        # Try cache first
        cached_results = cache.get(cache_key)
        if cached_results:
            cached_results.update({
                'cache_hit': True,
                'search_time_ms': round((time.time() - start_time) * 1000, 2)
            })
            return cached_results
        
        # Perform search with optimized queryset
        fighters = cls.get_optimized_queryset()
        search_results = cls._perform_multi_strategy_search(fighters, query, limit)
        
        # Calculate search time
        search_time = round((time.time() - start_time) * 1000, 2)
        
        result_data = {
            'results': search_results,
            'count': len(search_results),
            'query': query,
            'cache_hit': False,
            'search_time_ms': search_time
        }
        
        # Cache results
        cache.set(cache_key, result_data, cls.SEARCH_CACHE_TTL)
        
        # Log performance
        logger.info(
            f"Fighter search: query='{query}', results={len(search_results)}, "
            f"time={search_time}ms, cached=False"
        )
        
        return result_data
    
    @classmethod
    def _perform_multi_strategy_search(cls, fighters, query: str, limit: int) -> List[Dict]:
        """Perform multi-strategy search with performance optimization"""
        results = []
        seen_ids = set()
        
        # Strategy 1: Exact matches (highest priority, fastest)
        exact_matches = fighters.filter(
            Q(first_name__iexact=query) |
            Q(last_name__iexact=query) |
            Q(nickname__iexact=query) |
            Q(display_name__iexact=query)
        )[:10]
        
        for fighter in exact_matches:
            if fighter.id not in seen_ids:
                results.append(cls._fighter_to_search_result(fighter, 'exact', 1.0))
                seen_ids.add(fighter.id)
        
        # Strategy 2: Name variation matches
        if len(results) < limit:
            variation_matches = fighters.filter(
                name_variations__full_name_variation__iexact=query
            ).distinct()[:10]
            
            for fighter in variation_matches:
                if fighter.id not in seen_ids:
                    results.append(cls._fighter_to_search_result(fighter, 'variation', 0.9))
                    seen_ids.add(fighter.id)
        
        # Strategy 3: Partial name matching (first + last)
        if len(results) < limit:
            query_parts = query.split()
            if len(query_parts) == 2:
                first_part, last_part = query_parts[0], query_parts[1]
                partial_matches = fighters.filter(
                    Q(first_name__icontains=first_part, last_name__icontains=last_part) |
                    Q(first_name__icontains=last_part, last_name__icontains=first_part)
                )[:10]
                
                for fighter in partial_matches:
                    if fighter.id not in seen_ids:
                        results.append(cls._fighter_to_search_result(fighter, 'partial', 0.8))
                        seen_ids.add(fighter.id)
        
        # Strategy 4: Full-text search (PostgreSQL only)
        if len(results) < limit:
            try:
                search_vector = SearchVector('first_name', 'last_name', 'nickname', 'display_name')
                search_query = SearchQuery(query)
                fulltext_matches = fighters.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query)
                ).filter(search=search_query, rank__gte=0.1).order_by('-rank')[:15]
                
                for fighter in fulltext_matches:
                    if fighter.id not in seen_ids:
                        confidence = float(getattr(fighter, 'rank', 0.5))
                        results.append(cls._fighter_to_search_result(fighter, 'fulltext', confidence))
                        seen_ids.add(fighter.id)
            except Exception as e:
                logger.warning(f"Full-text search failed: {e}")
        
        # Strategy 5: Fuzzy matching (last resort, limited results)
        if len(results) < limit:
            fuzzy_matches = fighters.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(nickname__icontains=query) |
                Q(display_name__icontains=query)
            )[:10]
            
            for fighter in fuzzy_matches:
                if fighter.id not in seen_ids and len(results) < limit:
                    results.append(cls._fighter_to_search_result(fighter, 'fuzzy', 0.3))
                    seen_ids.add(fighter.id)
        
        return results[:limit]
    
    @classmethod
    def _fighter_to_search_result(cls, fighter, match_type: str, confidence: float) -> Dict:
        """Convert fighter to search result dict"""
        return {
            'id': str(fighter.id),
            'first_name': fighter.first_name,
            'last_name': fighter.last_name,
            'full_name': fighter.get_full_name(),
            'nickname': fighter.nickname,
            'nationality': fighter.nationality,
            'record': fighter.get_record_string(),
            'finish_rate': fighter.get_finish_rate(),
            'is_active': fighter.is_active,
            'match_type': match_type,
            'confidence': confidence
        }


class FighterProfileCache:
    """Caching utilities for fighter profiles"""
    
    PROFILE_CACHE_PREFIX = 'fighter_profile'
    STATISTICS_CACHE_PREFIX = 'fighter_stats'
    CACHE_TTL = 1800  # 30 minutes
    
    @classmethod
    def get_profile_cache_key(cls, fighter_id: str) -> str:
        """Generate cache key for fighter profile"""
        return f"{cls.PROFILE_CACHE_PREFIX}:{fighter_id}"
    
    @classmethod
    def get_statistics_cache_key(cls, fighter_id: str) -> str:
        """Generate cache key for fighter statistics"""
        return f"{cls.STATISTICS_CACHE_PREFIX}:{fighter_id}"
    
    @classmethod
    def get_cached_profile(cls, fighter_id: str) -> Optional[Dict]:
        """Get cached fighter profile"""
        cache_key = cls.get_profile_cache_key(fighter_id)
        return cache.get(cache_key)
    
    @classmethod
    def cache_profile(cls, fighter_id: str, profile_data: Dict) -> None:
        """Cache fighter profile data"""
        cache_key = cls.get_profile_cache_key(fighter_id)
        cache.set(cache_key, profile_data, cls.CACHE_TTL)
    
    @classmethod
    def invalidate_profile_cache(cls, fighter_id: str) -> None:
        """Invalidate cached fighter profile"""
        profile_key = cls.get_profile_cache_key(fighter_id)
        stats_key = cls.get_statistics_cache_key(fighter_id)
        cache.delete_many([profile_key, stats_key])
    
    @classmethod
    def get_cached_statistics(cls, fighter_id: str) -> Optional[Dict]:
        """Get cached fighter statistics"""
        cache_key = cls.get_statistics_cache_key(fighter_id)
        return cache.get(cache_key)
    
    @classmethod
    def cache_statistics(cls, fighter_id: str, stats_data: Dict) -> None:
        """Cache fighter statistics"""
        cache_key = cls.get_statistics_cache_key(fighter_id)
        cache.set(cache_key, stats_data, cls.CACHE_TTL)


class DatabaseOptimizer:
    """Database optimization utilities for fighter queries"""
    
    @classmethod
    def get_active_fighters_queryset(cls):
        """Optimized queryset for active fighters"""
        return Fighter.objects.filter(
            is_active=True
        ).select_related().prefetch_related('name_variations').order_by(
            'last_name', 'first_name'
        )
    
    @classmethod
    def get_fighters_by_nationality_queryset(cls, nationality: str):
        """Optimized queryset for fighters by nationality"""
        return Fighter.objects.filter(
            nationality__iexact=nationality
        ).select_related().prefetch_related('name_variations').order_by(
            'last_name', 'first_name'
        )
    
    @classmethod
    def get_top_fighters_queryset(cls, limit: int = 50):
        """Optimized queryset for top fighters by wins"""
        return Fighter.objects.filter(
            is_active=True,
            wins__gt=0
        ).select_related().prefetch_related('name_variations').order_by(
            '-wins', '-data_quality_score'
        )[:limit]
    
    @classmethod
    def bulk_update_data_quality(cls, batch_size: int = 100):
        """Bulk update data quality scores for all fighters"""
        fighters = Fighter.objects.all()
        updated_count = 0
        
        for i in range(0, fighters.count(), batch_size):
            batch = fighters[i:i + batch_size]
            updates = []
            
            for fighter in batch:
                # Calculate data quality score
                filled_fields = sum([
                    1 for field in [
                        'date_of_birth', 'birth_place', 'nationality',
                        'height_cm', 'weight_kg', 'reach_cm', 'stance',
                        'fighting_out_of', 'team', 'wikipedia_url', 'profile_image_url'
                    ]
                    if getattr(fighter, field)
                ])
                
                fighter.data_quality_score = round(filled_fields / 11, 2)
                updates.append(fighter)
            
            # Bulk update
            Fighter.objects.bulk_update(
                updates, 
                ['data_quality_score'], 
                batch_size=batch_size
            )
            updated_count += len(updates)
        
        logger.info(f"Updated data quality scores for {updated_count} fighters")
        return updated_count


class PerformanceMonitor:
    """Performance monitoring for fighter operations"""
    
    @classmethod
    def log_search_performance(cls, query: str, result_count: int, 
                             search_time_ms: float, cache_hit: bool):
        """Log search performance metrics"""
        logger.info(
            f"SEARCH_PERFORMANCE: query_length={len(query)}, "
            f"results={result_count}, time_ms={search_time_ms}, "
            f"cached={cache_hit}"
        )
    
    @classmethod
    def log_database_performance(cls, operation: str, record_count: int, 
                                execution_time_ms: float):
        """Log database operation performance"""
        logger.info(
            f"DB_PERFORMANCE: operation={operation}, "
            f"records={record_count}, time_ms={execution_time_ms}"
        )
    
    @classmethod
    def monitor_query_performance(cls, func):
        """Decorator to monitor query performance"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = round((time.time() - start_time) * 1000, 2)
            
            cls.log_database_performance(
                func.__name__, 
                len(result) if hasattr(result, '__len__') else 1,
                execution_time
            )
            
            return result
        return wrapper


# Usage examples and integration points
class FighterSearchIntegration:
    """Integration class for using optimized search in views"""
    
    @staticmethod
    def search_with_caching(query: str, limit: int = 30) -> Dict:
        """Main search method with all optimizations"""
        return FighterSearchOptimizer.search_fighters_cached(query, limit)
    
    @staticmethod
    def get_fighter_profile_optimized(fighter_id: str) -> Optional[Dict]:
        """Get fighter profile with caching"""
        # Try cache first
        cached_profile = FighterProfileCache.get_cached_profile(fighter_id)
        if cached_profile:
            return cached_profile
        
        # Query database with optimization
        try:
            fighter = Fighter.objects.select_related().prefetch_related(
                'name_variations'
            ).get(id=fighter_id)
            
            profile_data = {
                'id': str(fighter.id),
                'first_name': fighter.first_name,
                'last_name': fighter.last_name,
                'full_name': fighter.get_full_name(),
                'nickname': fighter.nickname,
                'nationality': fighter.nationality,
                'height_cm': fighter.height_cm,
                'weight_kg': float(fighter.weight_kg) if fighter.weight_kg else None,
                'reach_cm': fighter.reach_cm,
                'stance': fighter.stance,
                'wins': fighter.wins,
                'losses': fighter.losses,
                'draws': fighter.draws,
                'record': fighter.get_record_string(),
                'finish_rate': fighter.get_finish_rate(),
                'is_active': fighter.is_active,
                'data_quality_score': float(fighter.data_quality_score)
            }
            
            # Cache for future requests
            FighterProfileCache.cache_profile(fighter_id, profile_data)
            
            return profile_data
        
        except Fighter.DoesNotExist:
            return None