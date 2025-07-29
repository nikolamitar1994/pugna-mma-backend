"""
Fighter ranking calculation service.
Implements sophisticated algorithms for calculating fighter rankings based on:
- Win/loss record and streaks (40% weight)
- Opponent quality/strength of schedule (25% weight)  
- Recent activity levels (20% weight)
- Performance bonuses and methods (15% weight)
"""

import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q, Count, Avg, F, Case, When, Value, DecimalField
from django.utils import timezone

from .models import Fighter, FighterRanking, FighterStatistics, RankingHistory
from organizations.models import WeightClass, Organization
from events.models import Fight

logger = logging.getLogger(__name__)


class RankingCalculationService:
    """
    Service for calculating and updating fighter rankings.
    Implements multi-factor ranking algorithm with configurable weights.
    """
    
    # Ranking algorithm weights (should sum to 1.0)
    WEIGHTS = {
        'record': 0.40,      # Win/loss record and streaks
        'opponents': 0.25,    # Quality of opponents faced
        'activity': 0.20,     # Recent fight activity
        'performance': 0.15   # Performance bonuses and finish rate
    }
    
    # Activity scoring parameters
    ACTIVITY_DECAY_MONTHS = 18  # Full activity score decay period
    MIN_FIGHTS_12_MONTHS = 1    # Minimum fights for full activity score
    MAX_FIGHTS_BONUS = 3        # Maximum fights for bonus activity score
    
    # Performance bonuses
    FINISH_BONUS = 1.2      # Multiplier for finish wins
    TITLE_FIGHT_BONUS = 1.5 # Multiplier for title fights
    TOP_5_WIN_BONUS = 1.3   # Multiplier for top 5 wins
    TOP_10_WIN_BONUS = 1.15 # Multiplier for top 10 wins
    
    def __init__(self):
        self.calculation_date = timezone.now().date()
    
    def calculate_all_rankings(self, weight_class: WeightClass = None, 
                             organization: Organization = None) -> Dict[str, int]:
        """
        Calculate rankings for all fighters in specified context.
        Returns dict with calculation statistics.
        """
        logger.info(f"Starting ranking calculation for {weight_class or 'all weight classes'}")
        
        with transaction.atomic():
            # Get eligible fighters
            fighters = self._get_eligible_fighters(weight_class, organization)
            
            if not fighters:
                logger.warning("No eligible fighters found for ranking calculation")
                return {'fighters_processed': 0, 'rankings_updated': 0}
            
            # Update fighter statistics first
            stats_updated = self._update_fighter_statistics(fighters)
            
            # Calculate ranking scores
            fighter_scores = self._calculate_ranking_scores(fighters, weight_class, organization)
            
            # Update rankings
            rankings_updated = self._update_rankings(fighter_scores, weight_class, organization)
            
            logger.info(f"Ranking calculation complete: {len(fighters)} fighters, {rankings_updated} rankings updated")
            
            return {
                'fighters_processed': len(fighters),
                'statistics_updated': stats_updated,
                'rankings_updated': rankings_updated
            }
    
    def calculate_fighter_ranking(self, fighter: Fighter, weight_class: WeightClass,
                                organization: Organization = None) -> Decimal:
        """Calculate ranking score for a single fighter."""
        
        # Get or create fighter statistics
        stats, created = FighterStatistics.objects.get_or_create(fighter=fighter)
        if created or stats.needs_recalculation:
            stats.calculate_all_statistics()
        
        # Calculate component scores
        record_score = self._calculate_record_score(fighter, stats)
        opponent_score = self._calculate_opponent_quality_score(fighter, weight_class, organization)
        activity_score = self._calculate_activity_score(fighter, stats)
        performance_score = self._calculate_performance_score(fighter, stats)
        
        # Weighted total score
        total_score = (
            record_score * self.WEIGHTS['record'] +
            opponent_score * self.WEIGHTS['opponents'] +
            activity_score * self.WEIGHTS['activity'] +
            performance_score * self.WEIGHTS['performance']
        )
        
        return round(total_score, 4)
    
    def _get_eligible_fighters(self, weight_class: WeightClass = None,
                             organization: Organization = None) -> List[Fighter]:
        """Get fighters eligible for ranking in the specified context."""
        
        # Base query - active fighters with at least one fight
        fighters = Fighter.objects.filter(
            is_active=True,
            total_fights__gt=0
        ).prefetch_related('fight_history', 'statistics')
        
        # Filter by weight class activity if specified
        if weight_class:
            # Get fighters who have fought in this weight class recently
            fighters = fighters.filter(
                fight_history__weight_class=weight_class,
                fight_history__event_date__gte=self.calculation_date - timedelta(days=730)  # 2 years
            ).distinct()
        
        # Filter by organization if specified  
        if organization:
            fighters = fighters.filter(
                fight_history__organization=organization,
                fight_history__event_date__gte=self.calculation_date - timedelta(days=730)
            ).distinct()
        
        return list(fighters)
    
    def _update_fighter_statistics(self, fighters: List[Fighter]) -> int:
        """Update statistics for fighters that need recalculation."""
        updated_count = 0
        
        for fighter in fighters:
            stats, created = FighterStatistics.objects.get_or_create(fighter=fighter)
            if created or stats.needs_recalculation:
                stats.calculate_all_statistics()
                updated_count += 1
        
        return updated_count
    
    def _calculate_ranking_scores(self, fighters: List[Fighter], 
                                weight_class: WeightClass = None,
                                organization: Organization = None) -> List[Tuple[Fighter, Decimal, Dict]]:
        """Calculate ranking scores for all fighters and return sorted list."""
        
        fighter_scores = []
        
        for fighter in fighters:
            try:
                # Calculate total score
                total_score = self.calculate_fighter_ranking(fighter, weight_class, organization)
                
                # Calculate component scores for transparency
                stats = fighter.statistics
                components = {
                    'record_score': self._calculate_record_score(fighter, stats),
                    'opponent_score': self._calculate_opponent_quality_score(fighter, weight_class, organization),
                    'activity_score': self._calculate_activity_score(fighter, stats),
                    'performance_score': self._calculate_performance_score(fighter, stats)
                }
                
                fighter_scores.append((fighter, total_score, components))
                
            except Exception as e:
                logger.error(f"Error calculating score for {fighter.get_full_name()}: {e}")
                continue
        
        # Sort by score (highest first)
        fighter_scores.sort(key=lambda x: x[1], reverse=True)
        
        return fighter_scores
    
    def _calculate_record_score(self, fighter: Fighter, stats: FighterStatistics) -> Decimal:
        """Calculate score based on win/loss record and streaks."""
        
        if stats.total_fights == 0:
            return Decimal('0.0')
        
        # Base win percentage (0-100)
        win_percentage = stats.get_win_percentage()
        base_score = win_percentage
        
        # Streak bonus/penalty
        streak_bonus = 0
        if stats.current_streak > 0:
            # Win streak bonus (diminishing returns)
            streak_bonus = min(stats.current_streak * 5, 25)  # Max 25 point bonus
        elif stats.current_streak < 0:
            # Loss streak penalty
            streak_bonus = max(stats.current_streak * 3, -15)  # Max 15 point penalty
        
        # Quality of record bonus (more fights = more reliable)
        experience_bonus = min(stats.total_fights * 0.5, 10)  # Max 10 point bonus
        
        # Title fight bonus
        title_bonus = stats.title_wins * 3  # 3 points per title win
        
        total_score = base_score + streak_bonus + experience_bonus + title_bonus
        
        # Normalize to 0-100 range
        return Decimal(str(max(0, min(100, total_score))))
    
    def _calculate_opponent_quality_score(self, fighter: Fighter, 
                                        weight_class: WeightClass = None,
                                        organization: Organization = None) -> Decimal:
        """Calculate score based on quality of opponents faced."""
        
        # Get recent fights (last 3 years)
        recent_fights = fighter.fight_history.filter(
            event_date__gte=self.calculation_date - timedelta(days=1095)
        ).order_by('-event_date')
        
        if not recent_fights.exists():
            return Decimal('0.0')
        
        total_opponent_score = 0
        fight_count = 0
        
        for fight in recent_fights[:10]:  # Consider last 10 fights max
            opponent_score = self._get_opponent_strength_score(fight, weight_class, organization)
            
            # Weight recent fights more heavily
            months_ago = (self.calculation_date - fight.event_date).days / 30
            time_weight = max(0.3, 1.0 - (months_ago / 36))  # Decay over 3 years
            
            total_opponent_score += opponent_score * time_weight
            fight_count += time_weight
        
        if fight_count == 0:
            return Decimal('0.0')
        
        # Average opponent strength (0-100)
        avg_opponent_score = total_opponent_score / fight_count
        
        # Bonus for beating highly ranked opponents
        top_wins_bonus = (fighter.statistics.top_5_wins * 10 + 
                         fighter.statistics.top_10_wins * 5)
        
        final_score = avg_opponent_score + top_wins_bonus
        
        return Decimal(str(max(0, min(100, final_score))))
    
    def _get_opponent_strength_score(self, fight, weight_class: WeightClass = None,
                                   organization: Organization = None) -> float:
        """Get strength score for a specific opponent."""
        
        # Try to find opponent's current ranking
        if fight.opponent_fighter:
            opponent_ranking = FighterRanking.objects.filter(
                fighter=fight.opponent_fighter,
                weight_class=weight_class,
                organization=organization
            ).first()
            
            if opponent_ranking:
                # Convert rank to score (rank 1 = 100, rank 15 = 0)
                rank_score = max(0, 100 - (opponent_ranking.current_rank - 1) * 6.67)
                return rank_score
        
        # Fallback: Use opponent's record at fight time if available
        if fight.opponent_fighter and hasattr(fight.opponent_fighter, 'statistics'):
            opponent_stats = fight.opponent_fighter.statistics
            return opponent_stats.get_win_percentage()
        
        # Default opponent strength (average fighter)
        return 50.0
    
    def _calculate_activity_score(self, fighter: Fighter, stats: FighterStatistics) -> Decimal:
        """Calculate score based on recent fight activity."""
        
        # Base activity score from fights in last 12 months
        fights_12_months = stats.fights_last_12_months
        
        if fights_12_months == 0:
            base_score = 0
        elif fights_12_months >= self.MIN_FIGHTS_12_MONTHS:
            base_score = min(100, fights_12_months * 50)  # 50 points per fight, max 100
        else:
            base_score = fights_12_months * 30  # Partial credit
        
        # Penalty for inactivity
        if stats.days_since_last_fight:
            days_inactive = stats.days_since_last_fight
            months_inactive = days_inactive / 30
            
            if months_inactive > 12:
                # Decay after 12 months of inactivity
                decay_factor = max(0.1, 1.0 - ((months_inactive - 12) / self.ACTIVITY_DECAY_MONTHS))
                base_score *= decay_factor
        
        # Bonus for frequent activity
        if fights_12_months >= self.MAX_FIGHTS_BONUS:
            base_score *= 1.1  # 10% bonus for high activity
        
        return Decimal(str(max(0, min(100, base_score))))
    
    def _calculate_performance_score(self, fighter: Fighter, stats: FighterStatistics) -> Decimal:
        """Calculate score based on performance metrics and bonuses."""
        
        # Base score from finish rate
        finish_rate_score = stats.finish_rate  # 0-100 based on finish percentage
        
        # Bonus for performance bonuses received
        bonus_score = min(stats.total_bonuses * 5, 20)  # 5 points per bonus, max 20
        
        # Finish resistance bonus (surviving to decision when losing)
        resistance_bonus = stats.finish_resistance * 0.2  # Up to 20 points
        
        # Title fight experience bonus
        title_experience = min(stats.title_fights * 3, 15)  # Max 15 points
        
        # Recent performance emphasis (wins in last 12 months)
        recent_wins = fighter.fight_history.filter(
            result='win',
            event_date__gte=self.calculation_date - timedelta(days=365)
        ).count()
        recent_performance = min(recent_wins * 10, 30)  # Max 30 points
        
        total_score = (finish_rate_score + bonus_score + resistance_bonus + 
                      title_experience + recent_performance)
        
        return Decimal(str(max(0, min(100, total_score))))
    
    def _update_rankings(self, fighter_scores: List[Tuple[Fighter, Decimal, Dict]],
                        weight_class: WeightClass = None,
                        organization: Organization = None) -> int:
        """Update FighterRanking records with new scores and positions."""
        
        updated_count = 0
        
        for rank, (fighter, total_score, components) in enumerate(fighter_scores, 1):
            try:
                # Get or create ranking record
                ranking, created = FighterRanking.objects.get_or_create(
                    fighter=fighter,
                    weight_class=weight_class,
                    organization=organization,
                    ranking_type='divisional',
                    defaults={
                        'current_rank': rank,
                        'ranking_score': total_score,
                        'record_score': components['record_score'],
                        'opponent_quality_score': components['opponent_score'],
                        'activity_score': components['activity_score'],
                        'performance_score': components['performance_score']
                    }
                )
                
                if not created:
                    # Update existing ranking
                    old_rank = ranking.current_rank
                    ranking.previous_rank = old_rank
                    ranking.current_rank = rank
                    ranking.ranking_score = total_score
                    ranking.record_score = components['record_score']
                    ranking.opponent_quality_score = components['opponent_score']
                    ranking.activity_score = components['activity_score']
                    ranking.performance_score = components['performance_score']
                    ranking.save()
                    
                    # Create history record if rank changed
                    if old_rank != rank:
                        RankingHistory.objects.create(
                            fighter_ranking=ranking,
                            rank_on_date=rank,
                            ranking_score=total_score,
                            calculation_date=self.calculation_date,
                            rank_change=old_rank - rank,
                            trigger_event=f"Ranking recalculation on {self.calculation_date}"
                        )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating ranking for {fighter.get_full_name()}: {e}")
                continue
        
        return updated_count
    
    def recalculate_pound_for_pound(self) -> Dict[str, int]:
        """Calculate pound-for-pound rankings across all weight classes."""
        
        logger.info("Starting pound-for-pound ranking calculation")
        
        with transaction.atomic():
            # Get top fighters from each weight class
            p4p_candidates = []
            
            # Get top 3 from each active weight class
            weight_classes = WeightClass.objects.filter(is_active=True)
            
            for weight_class in weight_classes:
                top_fighters = FighterRanking.objects.filter(
                    weight_class=weight_class,
                    ranking_type='divisional',
                    current_rank__lte=3
                ).select_related('fighter')[:3]
                
                for ranking in top_fighters:
                    # Calculate P4P score (divisional score + cross-division adjustments)
                    p4p_score = self._calculate_p4p_score(ranking)
                    p4p_candidates.append((ranking.fighter, p4p_score))
            
            # Sort by P4P score
            p4p_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Update P4P rankings
            rankings_updated = 0
            for rank, (fighter, score) in enumerate(p4p_candidates[:15], 1):  # Top 15 P4P
                ranking, created = FighterRanking.objects.get_or_create(
                    fighter=fighter,
                    ranking_type='p4p',
                    weight_class=None,
                    organization=None,
                    defaults={
                        'current_rank': rank,
                        'ranking_score': score
                    }
                )
                
                if not created and ranking.current_rank != rank:
                    ranking.previous_rank = ranking.current_rank
                    ranking.current_rank = rank
                    ranking.ranking_score = score
                    ranking.save()
                
                rankings_updated += 1
            
            logger.info(f"P4P ranking calculation complete: {rankings_updated} rankings updated")
            
            return {'p4p_rankings_updated': rankings_updated}
    
    def _calculate_p4p_score(self, divisional_ranking: FighterRanking) -> Decimal:
        """Calculate pound-for-pound score based on divisional performance."""
        
        # Base score from divisional ranking
        base_score = divisional_ranking.ranking_score
        
        # Adjust for division strength/depth
        division_modifier = self._get_division_strength_modifier(divisional_ranking.weight_class)
        
        # Cross-division achievements bonus
        cross_division_bonus = self._calculate_cross_division_bonus(divisional_ranking.fighter)
        
        # Title reign bonus
        title_bonus = 20 if divisional_ranking.is_champion else 0
        
        p4p_score = base_score * division_modifier + cross_division_bonus + title_bonus
        
        return Decimal(str(max(0, p4p_score)))
    
    def _get_division_strength_modifier(self, weight_class: WeightClass) -> float:
        """Get modifier based on division strength/depth."""
        
        # Count active fighters in the division
        division_depth = Fighter.objects.filter(
            is_active=True,
            fight_history__weight_class=weight_class,
            fight_history__event_date__gte=self.calculation_date - timedelta(days=730)
        ).distinct().count()
        
        # More competitive divisions get higher modifiers
        if division_depth >= 50:
            return 1.1  # Very deep division
        elif division_depth >= 30:
            return 1.05  # Deep division
        elif division_depth >= 15:
            return 1.0   # Average division
        else:
            return 0.95  # Shallow division
    
    def _calculate_cross_division_bonus(self, fighter: Fighter) -> float:
        """Calculate bonus for fighting across multiple weight classes."""
        
        if hasattr(fighter, 'statistics'):
            weight_classes_fought = fighter.statistics.weight_classes_fought
            if weight_classes_fought > 1:
                return min((weight_classes_fought - 1) * 5, 15)  # Max 15 point bonus
        
        return 0.0


# Service instance
ranking_service = RankingCalculationService()