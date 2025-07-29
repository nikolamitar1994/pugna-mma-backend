"""
Fight deduplication service for interconnected network
"""
from datetime import timedelta
from django.db.models import Q
from django.db import transaction


class FightDeduplicator:
    """
    Service to detect and handle duplicate fight records in the interconnected network
    """
    
    @classmethod
    def find_potential_duplicates(cls, fighter_a, fighter_b, event_date, tolerance_days=7):
        """
        Find potential duplicate fights between two fighters within date tolerance
        """
        try:
            from events.models import Fight
            
            date_range_start = event_date - timedelta(days=tolerance_days)
            date_range_end = event_date + timedelta(days=tolerance_days)
            
            # Check for existing fights between these fighters in date range
            existing_fights = Fight.objects.filter(
                Q(fighter_a=fighter_a, fighter_b=fighter_b) |
                Q(fighter_a=fighter_b, fighter_b=fighter_a),
                event__date__range=[date_range_start, date_range_end]
            ).select_related('event')
            
            return existing_fights
        except ImportError:
            # Fight model might not exist yet
            return []
    
    @classmethod
    def merge_fight_histories(cls, primary_fight, duplicate_fight_histories):
        """
        Merge duplicate fight history records to point to primary fight
        """
        with transaction.atomic():
            for fh in duplicate_fight_histories:
                # Update the fight history to point to primary fight
                fh.fight = primary_fight
                fh.save()
        
        return len(duplicate_fight_histories)