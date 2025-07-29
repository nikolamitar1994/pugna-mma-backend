"""
Network consistency validation service
"""
from typing import List
from django.db.models import Q, F


class NetworkConsistencyValidator:
    """
    Service to validate the integrity of the interconnected fighter network
    """
    
    @classmethod
    def validate_fight_network(cls) -> List[dict]:
        """
        Run comprehensive validation checks on the interconnected network
        
        Returns:
            List of issues found with details
        """
        issues = []
        
        # Check 1: Orphaned FightHistory records without opponent fighters
        from ..models import FightHistory
        orphaned = FightHistory.objects.filter(
            opponent_fighter__isnull=True,
            opponent_first_name__isnull=False
        )
        
        if orphaned.exists():
            issues.append({
                'type': 'orphaned_fight_histories',
                'count': orphaned.count(),
                'description': f'Found {orphaned.count()} fight histories without linked opponent fighters',
                'severity': 'medium'
            })
        
        # Check 2: FightHistory records without Fight links
        unlinked = FightHistory.objects.filter(fight__isnull=True)
        if unlinked.exists():
            issues.append({
                'type': 'unlinked_fight_histories', 
                'count': unlinked.count(),
                'description': f'Found {unlinked.count()} fight histories without Fight record links',
                'severity': 'high'
            })
        
        # Check 3: Inconsistent fight results (if Fight model exists)
        try:
            from events.models import Fight
            
            inconsistent = Fight.objects.filter(
                ~Q(fighter_a_result='draw'),
                ~Q(fighter_a_result='no_contest'),
                fighter_a_result=F('fighter_b_result')
            )
            
            if inconsistent.exists():
                issues.append({
                    'type': 'inconsistent_fight_results',
                    'count': inconsistent.count(), 
                    'description': f'Found {inconsistent.count()} fights with inconsistent results',
                    'severity': 'critical'
                })
        except ImportError:
            # Fight model might not exist yet
            pass
        
        return issues
    
    @classmethod
    def get_network_statistics(cls) -> dict:
        """
        Get statistics about the interconnected network coverage
        """
        from ..models import FightHistory
        
        total_fight_histories = FightHistory.objects.count()
        linked_opponents = FightHistory.objects.filter(opponent_fighter__isnull=False).count()
        linked_fights = FightHistory.objects.filter(fight__isnull=False).count()
        
        return {
            'total_fight_histories': total_fight_histories,
            'linked_opponents': linked_opponents,
            'linked_fights': linked_fights,
            'opponent_link_percentage': (linked_opponents / total_fight_histories * 100) if total_fight_histories > 0 else 0,
            'fight_link_percentage': (linked_fights / total_fight_histories * 100) if total_fight_histories > 0 else 0
        }