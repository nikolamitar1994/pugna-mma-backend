"""
Fight History Reconciliation Service

This service handles the linking of string-based FightHistory records 
with authoritative Fight records to create a fully interconnected data network.
"""

from django.db import transaction
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from fuzzywuzzy import fuzz
import logging
from typing import Dict, List, Optional, Tuple

from fighters.models import Fighter, FightHistory
from events.models import Fight, FightParticipant

logger = logging.getLogger(__name__)


class FightHistoryReconciliationService:
    """
    Service to reconcile string-based fight history with authoritative Fight records.
    
    This service implements multiple strategies to match existing FightHistory records
    with Fight records, creating bidirectional relationships and ensuring data consistency.
    """
    
    def __init__(self):
        self.stats = {
            'processed': 0,
            'linked': 0,
            'unmatched': 0,
            'conflicts': 0,
            'errors': 0,
            'skipped': 0
        }
        self.match_threshold = 80  # Minimum similarity score for automatic matching
        self.high_confidence_threshold = 95  # Auto-link threshold
    
    def reconcile_all_unlinked_history(self, dry_run: bool = False) -> Dict:
        """
        Reconcile all FightHistory records not yet linked to Fight records.
        
        Args:
            dry_run: If True, don't actually link records, just report what would be done
            
        Returns:
            Dictionary with reconciliation statistics
        """
        unlinked_records = FightHistory.objects.filter(
            authoritative_fight__isnull=True
        ).select_related(
            'fighter', 'event', 'opponent_fighter'
        ).prefetch_related(
            'fighter__fight_participations__fight__event'
        )
        
        total_count = unlinked_records.count()
        logger.info(f"Starting reconciliation of {total_count} unlinked records (dry_run={dry_run})")
        
        for history in unlinked_records:
            try:
                self._reconcile_single_history(history, dry_run=dry_run)
                self.stats['processed'] += 1
                
                # Log progress every 100 records
                if self.stats['processed'] % 100 == 0:
                    logger.info(f"Progress: {self.stats['processed']}/{total_count} processed")
                    
            except Exception as e:
                logger.error(f"Error reconciling history {history.id}: {e}")
                self.stats['errors'] += 1
        
        # Final statistics
        self.stats['success_rate'] = (
            self.stats['linked'] / self.stats['processed'] * 100 
            if self.stats['processed'] > 0 else 0
        )
        
        logger.info(f"Reconciliation complete: {self.stats}")
        return self.stats
    
    def reconcile_fighter_history(self, fighter: Fighter, dry_run: bool = False) -> Dict:
        """
        Reconcile fight history for a specific fighter.
        
        Args:
            fighter: Fighter instance to reconcile
            dry_run: If True, don't actually link records
            
        Returns:
            Dictionary with reconciliation statistics for this fighter
        """
        fighter_stats = {'processed': 0, 'linked': 0, 'unmatched': 0}
        
        unlinked_records = FightHistory.objects.filter(
            fighter=fighter,
            authoritative_fight__isnull=True
        ).select_related('event', 'opponent_fighter')
        
        logger.info(f"Reconciling {unlinked_records.count()} records for {fighter.get_full_name()}")
        
        for history in unlinked_records:
            try:
                result = self._reconcile_single_history(history, dry_run=dry_run)
                fighter_stats['processed'] += 1
                if result:
                    fighter_stats['linked'] += 1
                else:
                    fighter_stats['unmatched'] += 1
            except Exception as e:
                logger.error(f"Error reconciling history {history.id}: {e}")
        
        return fighter_stats
    
    def _reconcile_single_history(self, history: FightHistory, dry_run: bool = False) -> bool:
        """
        Reconcile a single FightHistory record with authoritative Fight records.
        
        Args:
            history: FightHistory record to reconcile
            dry_run: If True, don't actually create links
            
        Returns:
            True if successfully linked, False otherwise
        """
        # Skip if already linked
        if history.authoritative_fight:
            self.stats['skipped'] += 1
            return True
        
        # Strategy 1: Direct event and fighter match
        fight = self._find_fight_by_event_and_participants(history)
        if fight:
            confidence = self._calculate_match_confidence(fight, history)
            if confidence >= self.match_threshold:
                if not dry_run:
                    self._link_history_to_fight(history, fight, confidence)
                self.stats['linked'] += 1
                logger.debug(f"Linked history {history.id} to fight {fight.id} (confidence: {confidence})")
                return True
        
        # Strategy 2: Date and name-based matching
        fight = self._find_fight_by_date_and_names(history)
        if fight:
            confidence = self._calculate_match_confidence(fight, history)
            if confidence >= self.match_threshold:
                if not dry_run:
                    self._link_history_to_fight(history, fight, confidence)
                self.stats['linked'] += 1
                logger.debug(f"Linked history {history.id} to fight {fight.id} via date/names (confidence: {confidence})")
                return True
        
        # Strategy 3: Fuzzy matching across all fights for this fighter
        fight = self._find_fight_by_fuzzy_matching(history)
        if fight:
            confidence = self._calculate_match_confidence(fight, history)
            if confidence >= self.high_confidence_threshold:  # Higher threshold for fuzzy matches
                if not dry_run:
                    self._link_history_to_fight(history, fight, confidence)
                self.stats['linked'] += 1
                logger.debug(f"Linked history {history.id} to fight {fight.id} via fuzzy match (confidence: {confidence})")
                return True
        
        # No suitable match found
        self.stats['unmatched'] += 1
        logger.debug(f"Could not reconcile history: {history.id} - {history.fighter.get_full_name()} vs {history.opponent_full_name}")
        return False
    
    def _find_fight_by_event_and_participants(self, history: FightHistory) -> Optional[Fight]:
        """
        Find Fight by exact event and participant matching.
        This is the most reliable matching strategy.
        """
        if not history.event:
            return None
            
        fights = Fight.objects.filter(
            event=history.event,
            participants__fighter=history.fighter
        ).prefetch_related('participants__fighter').distinct()
        
        for fight in fights:
            if self._participants_match_history(fight, history):
                return fight
        
        return None
    
    def _find_fight_by_date_and_names(self, history: FightHistory) -> Optional[Fight]:
        """
        Find Fight by date and fighter/opponent name matching.
        """
        # Find fights on the same date with the same fighter
        date_fights = Fight.objects.filter(
            event__date=history.event_date,
            participants__fighter=history.fighter
        ).prefetch_related('participants__fighter').distinct()
        
        best_match = None
        best_score = 0
        
        for fight in date_fights:
            score = self._calculate_opponent_similarity(fight, history)
            if score > best_score and score >= self.match_threshold:
                best_match = fight
                best_score = score
        
        return best_match
    
    def _find_fight_by_fuzzy_matching(self, history: FightHistory) -> Optional[Fight]:
        """
        Find Fight using fuzzy matching across all fights for this fighter.
        This is the least reliable but most comprehensive strategy.
        """
        # Get all fights for this fighter within a reasonable date range
        date_range_start = history.event_date.replace(year=history.event_date.year - 1)
        date_range_end = history.event_date.replace(year=history.event_date.year + 1)
        
        potential_fights = Fight.objects.filter(
            participants__fighter=history.fighter,
            event__date__range=[date_range_start, date_range_end]
        ).prefetch_related('participants__fighter', 'event').distinct()
        
        best_match = None
        best_score = 0
        
        for fight in potential_fights:
            score = self._calculate_comprehensive_similarity(fight, history)
            if score > best_score:
                best_match = fight
                best_score = score
        
        return best_match if best_score >= self.high_confidence_threshold else None
    
    def _participants_match_history(self, fight: Fight, history: FightHistory) -> bool:
        """
        Check if fight participants match the history record.
        """
        participants = list(fight.participants.all())
        if len(participants) != 2:
            return False
        
        # Find the opponent (not the history's fighter)
        opponent_participant = None
        for p in participants:
            if p.fighter != history.fighter:
                opponent_participant = p
                break
        
        if not opponent_participant:
            return False
        
        # Check name similarity
        return self._names_match(
            history.opponent_full_name, 
            opponent_participant.fighter.get_full_name(),
            threshold=85
        )
    
    def _calculate_opponent_similarity(self, fight: Fight, history: FightHistory) -> float:
        """
        Calculate similarity score based on opponent name matching.
        """
        opponent_participant = fight.participants.exclude(
            fighter=history.fighter
        ).first()
        
        if not opponent_participant:
            return 0
        
        opponent_name = opponent_participant.fighter.get_full_name()
        
        # Multiple name matching strategies
        scores = []
        
        # Full name similarity
        scores.append(fuzz.ratio(
            history.opponent_full_name.lower(),
            opponent_name.lower()
        ))
        
        # Partial ratio (handles nicknames and variations)
        scores.append(fuzz.partial_ratio(
            history.opponent_full_name.lower(),
            opponent_name.lower()
        ))
        
        # Token sort ratio (handles word order differences)
        scores.append(fuzz.token_sort_ratio(
            history.opponent_full_name.lower(),
            opponent_name.lower()
        ))
        
        # Component matching (first name + last name)
        if history.opponent_first_name and history.opponent_last_name:
            component_match = (
                fuzz.ratio(history.opponent_first_name.lower(), opponent_participant.fighter.first_name.lower()) +
                fuzz.ratio(history.opponent_last_name.lower(), opponent_participant.fighter.last_name.lower())
            ) / 2
            scores.append(component_match)
        
        return max(scores)
    
    def _calculate_comprehensive_similarity(self, fight: Fight, history: FightHistory) -> float:
        """
        Calculate comprehensive similarity score considering multiple factors.
        """
        score = 0
        weight_sum = 0
        
        # Date similarity (within 30 days = 100%, further = linear decay)
        date_diff = abs((fight.event.date - history.event_date).days)
        if date_diff <= 30:
            date_score = max(0, 100 - (date_diff * 3))  # 3 points per day
            score += date_score * 0.3
            weight_sum += 0.3
        
        # Opponent name similarity (high weight)
        opponent_score = self._calculate_opponent_similarity(fight, history)
        score += opponent_score * 0.4
        weight_sum += 0.4
        
        # Method similarity
        if history.method and fight.method:
            method_similarity = fuzz.ratio(
                history.method.lower(),
                fight.method.lower()
            )
            score += method_similarity * 0.15
            weight_sum += 0.15
        
        # Event name similarity
        if history.event_name and fight.event.name:
            event_similarity = fuzz.partial_ratio(
                history.event_name.lower(),
                fight.event.name.lower()
            )
            score += event_similarity * 0.1
            weight_sum += 0.1
        
        # Round/time similarity
        if history.ending_round and fight.ending_round:
            if history.ending_round == fight.ending_round:
                score += 100 * 0.05
                weight_sum += 0.05
        
        return score / weight_sum if weight_sum > 0 else 0
    
    def _calculate_match_confidence(self, fight: Fight, history: FightHistory) -> float:
        """
        Calculate overall confidence in the match.
        """
        return self._calculate_comprehensive_similarity(fight, history)
    
    def _names_match(self, name1: str, name2: str, threshold: float = 85) -> bool:
        """
        Check if two names match above the given threshold.
        """
        return fuzz.ratio(name1.lower(), name2.lower()) >= threshold
    
    @transaction.atomic
    def _link_history_to_fight(self, history: FightHistory, fight: Fight, confidence: float):
        """
        Link FightHistory record to authoritative Fight with full data sync.
        """
        # Set the authoritative fight link
        history.authoritative_fight = fight
        history.perspective_fighter = history.fighter
        history.reconciled_at = timezone.now()
        
        # Update data source to indicate reconciliation
        history.data_source = 'reconciled'
        
        # Update opponent information from authoritative source
        opponent_participant = fight.participants.exclude(
            fighter=history.fighter
        ).first()
        
        if opponent_participant:
            history.opponent_fighter = opponent_participant.fighter
            # Update opponent names to match the authoritative record
            history.opponent_full_name = opponent_participant.fighter.get_full_name()
            history.opponent_first_name = opponent_participant.fighter.first_name
            history.opponent_last_name = opponent_participant.fighter.last_name
            
            # Update result from authoritative source
            our_participant = fight.participants.filter(fighter=history.fighter).first()
            if our_participant and our_participant.result:
                history.result = our_participant.result
        
        # Update event information from authoritative source
        if fight.event:
            history.event = fight.event
            history.event_name = fight.event.name
            history.event_date = fight.event.date
            history.location = fight.event.location
            history.venue = fight.event.venue
            history.city = fight.event.city
            history.state = fight.event.state
            history.country = fight.event.country
            history.organization = fight.event.organization
        
        # Update fight details from authoritative source
        if fight.method:
            history.method = fight.method
        if fight.method_details:
            history.method_details = fight.method_details
        if fight.ending_round:
            history.ending_round = fight.ending_round
        if fight.ending_time:
            history.ending_time = fight.ending_time
        if fight.scheduled_rounds:
            history.scheduled_rounds = fight.scheduled_rounds
        
        # Update title fight information
        history.is_title_fight = fight.is_title_fight
        history.is_interim_title = fight.is_interim_title
        
        # Update weight class information
        if fight.weight_class:
            history.weight_class = fight.weight_class
            history.weight_class_name = fight.weight_class.name
        
        # Recalculate data quality score (should be higher now)
        history.data_quality_score = history.calculate_data_quality()
        
        # Add reconciliation metadata
        if not history.parsed_data:
            history.parsed_data = {}
        history.parsed_data['reconciliation'] = {
            'linked_at': timezone.now().isoformat(),
            'confidence_score': confidence,
            'authoritative_fight_id': str(fight.id),
            'method': 'automatic_reconciliation'
        }
        
        history.save()
        
        logger.info(f"Successfully linked history {history.id} to fight {fight.id} (confidence: {confidence:.1f}%)")
    
    def generate_reconciliation_report(self) -> Dict:
        """
        Generate a comprehensive reconciliation report.
        """
        total_history = FightHistory.objects.count()
        linked_history = FightHistory.objects.filter(authoritative_fight__isnull=False).count()
        unlinked_history = total_history - linked_history
        
        # Get linking statistics by data source
        source_stats = {}
        for source_choice in FightHistory.DATA_SOURCE_CHOICES:
            source_code = source_choice[0]
            linked_count = FightHistory.objects.filter(
                data_source=source_code,
                authoritative_fight__isnull=False
            ).count()
            total_count = FightHistory.objects.filter(data_source=source_code).count()
            
            source_stats[source_code] = {
                'total': total_count,
                'linked': linked_count,
                'unlinked': total_count - linked_count,
                'link_rate': (linked_count / total_count * 100) if total_count > 0 else 0
            }
        
        # Get quality score distribution
        quality_ranges = [
            (0.0, 0.25, 'Poor'),
            (0.25, 0.5, 'Fair'), 
            (0.5, 0.75, 'Good'),
            (0.75, 1.0, 'Excellent')
        ]
        
        quality_stats = {}
        for min_score, max_score, label in quality_ranges:
            count = FightHistory.objects.filter(
                data_quality_score__gte=min_score,
                data_quality_score__lt=max_score
            ).count()
            quality_stats[label] = count
        
        return {
            'summary': {
                'total_history_records': total_history,
                'linked_records': linked_history,
                'unlinked_records': unlinked_history,
                'link_percentage': (linked_history / total_history * 100) if total_history > 0 else 0
            },
            'by_data_source': source_stats,
            'data_quality_distribution': quality_stats,
            'recent_reconciliation_stats': self.stats
        }


class FightHistoryConsistencyChecker:
    """
    Service to check and maintain data consistency in interconnected fight history.
    """
    
    def __init__(self):
        self.issues = []
    
    def check_all_consistency(self) -> List[Dict]:
        """
        Run all consistency checks and return list of issues found.
        """
        self.issues = []
        
        self._check_bidirectional_consistency()
        self._check_result_consistency()
        self._check_date_consistency()
        self._check_duplicate_perspectives()
        self._check_orphaned_relationships()
        
        return self.issues
    
    def _check_bidirectional_consistency(self):
        """
        Check that fights have consistent bidirectional history records.
        """
        # Find fights that should have 2 history perspectives but don't
        fights_with_history = Fight.objects.filter(
            history_views__isnull=False
        ).annotate(
            history_count=Count('history_views')
        ).filter(
            history_count=1  # Should have 2
        )
        
        for fight in fights_with_history:
            self.issues.append({
                'type': 'missing_perspective',
                'severity': 'high',
                'fight_id': fight.id,
                'message': f"Fight {fight.id} has only one history perspective, should have two",
                'details': {
                    'existing_perspectives': list(fight.history_views.values_list('perspective_fighter__id', flat=True))
                }
            })
    
    def _check_result_consistency(self):
        """
        Check that fight results are consistent between perspectives.
        """
        # Find fights where both perspectives have the same result (should be opposite)
        from django.db.models import Count, Q
        
        problematic_fights = Fight.objects.annotate(
            win_count=Count('history_views', filter=Q(history_views__result='win')),
            loss_count=Count('history_views', filter=Q(history_views__result='loss'))
        ).filter(
            Q(win_count=2) | Q(loss_count=2) | Q(win_count=0, loss_count=0)
        )
        
        for fight in problematic_fights:
            self.issues.append({
                'type': 'result_inconsistency',
                'severity': 'high',
                'fight_id': fight.id,
                'message': f"Fight {fight.id} has inconsistent results in history perspectives"
            })
    
    def _check_date_consistency(self):
        """
        Check that event dates match between Fight and FightHistory.
        """
        inconsistent_dates = FightHistory.objects.filter(
            authoritative_fight__isnull=False
        ).exclude(
            event_date=models.F('authoritative_fight__event__date')
        )
        
        for history in inconsistent_dates:
            self.issues.append({
                'type': 'date_inconsistency',
                'severity': 'medium',
                'history_id': history.id,
                'message': f"History {history.id} has date mismatch with authoritative fight",
                'details': {
                    'history_date': history.event_date.isoformat(),
                    'fight_date': history.authoritative_fight.event.date.isoformat()
                }
            })
    
    def _check_duplicate_perspectives(self):
        """
        Check for duplicate history perspectives for the same fight and fighter.
        """
        from django.db.models import Count
        
        duplicates = FightHistory.objects.filter(
            authoritative_fight__isnull=False
        ).values(
            'authoritative_fight', 'perspective_fighter'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        for duplicate in duplicates:
            self.issues.append({
                'type': 'duplicate_perspective',
                'severity': 'high',
                'message': f"Multiple history records for same fight/fighter perspective",
                'details': duplicate
            })
    
    def _check_orphaned_relationships(self):
        """
        Check for orphaned relationship references.
        """
        # Check for history records referencing non-existent fights
        orphaned_fight_refs = FightHistory.objects.filter(
            authoritative_fight__isnull=False,
            authoritative_fight__in=[]  # This will catch deleted fights
        )
        
        for history in orphaned_fight_refs:
            self.issues.append({
                'type': 'orphaned_fight_reference',
                'severity': 'high',
                'history_id': history.id,
                'message': f"History {history.id} references non-existent fight"
            })