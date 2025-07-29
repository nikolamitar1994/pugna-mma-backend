"""
Fighter matching service for interconnected network operations
"""
import re
from typing import Tuple, Optional, List
from django.db.models import Q
from django.db import connection
from ..models import Fighter, FighterNameVariation


class FighterMatcher:
    """
    Service to match opponent names from fight history to actual Fighter records.
    Uses multiple matching strategies with confidence scoring.
    """
    
    @classmethod
    def find_fighter_by_name(cls, first_name: str, last_name: str, 
                           event_date=None, context_data=None) -> Tuple[Optional[Fighter], float]:
        """
        Find fighter by name with multiple matching strategies
        
        Args:
            first_name: Fighter's first name
            last_name: Fighter's last name  
            event_date: Optional date context for better matching
            context_data: Optional additional context (nationality, etc.)
            
        Returns:
            Tuple of (Fighter object or None, confidence score 0.0-1.0)
        """
        if not first_name:
            return None, 0.0
        
        first_name = first_name.strip()
        last_name = (last_name or '').strip()
        
        # Strategy 1: Exact match
        fighter, confidence = cls._exact_match(first_name, last_name)
        if fighter and confidence >= 0.95:
            return fighter, confidence
        
        # Strategy 2: Name variations match
        variation_fighter, variation_confidence = cls._name_variation_match(first_name, last_name)
        if variation_fighter and variation_confidence > confidence:
            fighter, confidence = variation_fighter, variation_confidence
        
        # Strategy 3: Fuzzy matching with PostgreSQL similarity
        fuzzy_fighter, fuzzy_confidence = cls._fuzzy_match(first_name, last_name)
        if fuzzy_fighter and fuzzy_confidence > confidence:
            fighter, confidence = fuzzy_fighter, fuzzy_confidence
        
        # Strategy 4: Nickname matching
        nickname_fighter, nickname_confidence = cls._nickname_match(first_name, last_name)
        if nickname_fighter and nickname_confidence > confidence:
            fighter, confidence = nickname_fighter, nickname_confidence
        
        # Apply context-based confidence boosting
        if fighter and context_data:
            confidence = cls._apply_context_boost(fighter, context_data, confidence)
        
        return fighter, confidence
    
    @classmethod
    def _exact_match(cls, first_name: str, last_name: str) -> Tuple[Optional[Fighter], float]:
        """Strategy 1: Exact name match"""
        try:
            fighter = Fighter.objects.get(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            )
            return fighter, 1.0
        except Fighter.DoesNotExist:
            return None, 0.0
        except Fighter.MultipleObjectsReturned:
            # Multiple fighters with same name - return first, lower confidence
            fighter = Fighter.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
            return fighter, 0.85
    
    @classmethod
    def _name_variation_match(cls, first_name: str, last_name: str) -> Tuple[Optional[Fighter], float]:
        """Strategy 2: Name variations match"""
        variations = FighterNameVariation.objects.filter(
            Q(first_name_variation__iexact=first_name, last_name_variation__iexact=last_name) |
            Q(full_name_variation__iexact=f"{first_name} {last_name}".strip())
        ).select_related('fighter')
        
        if variations.exists():
            variation = variations.first()
            return variation.fighter, 0.9
        
        return None, 0.0
    
    @classmethod
    def _fuzzy_match(cls, first_name: str, last_name: str) -> Tuple[Optional[Fighter], float]:
        """Strategy 3: PostgreSQL similarity matching"""
        full_name = f"{first_name} {last_name}".strip()
        
        try:
            with connection.cursor() as cursor:
                # Use simple icontains matching since pg_trgm might not be available
                cursor.execute("""
                    SELECT id, first_name, last_name
                    FROM fighters 
                    WHERE LOWER(CONCAT(first_name, ' ', last_name)) LIKE %s
                    OR LOWER(first_name) LIKE %s
                    OR LOWER(last_name) LIKE %s
                    LIMIT 5
                """, [f"%{full_name.lower()}%", f"%{first_name.lower()}%", f"%{last_name.lower()}%"])
                
                results = cursor.fetchall()
                if results:
                    # Simple scoring based on exact component matches
                    best_fighter = None
                    best_score = 0.0
                    
                    for row in results:
                        fighter = Fighter.objects.get(id=row[0])
                        score = cls._calculate_name_similarity(full_name, fighter.get_full_name())
                        if score > best_score:
                            best_fighter = fighter
                            best_score = score
                    
                    if best_score > 0.6:
                        return best_fighter, min(best_score, 0.85)
                    
        except Exception:
            # Fallback to Django ORM icontains matching
            fighters = Fighter.objects.filter(
                Q(first_name__icontains=first_name) | 
                Q(last_name__icontains=last_name)
            )
            
            if fighters.exists():
                # Simple scoring based on character overlap
                best_fighter = None
                best_score = 0.0
                
                for fighter in fighters:
                    score = cls._calculate_name_similarity(
                        full_name, 
                        fighter.get_full_name()
                    )
                    if score > best_score:
                        best_fighter = fighter
                        best_score = score
                
                if best_score > 0.6:
                    return best_fighter, min(best_score, 0.8)
        
        return None, 0.0
    
    @classmethod
    def _nickname_match(cls, first_name: str, last_name: str) -> Tuple[Optional[Fighter], float]:
        """Strategy 4: Check if first_name might be a nickname"""
        nickname_fighters = Fighter.objects.filter(
            Q(nickname__iexact=first_name) |
            Q(nickname__icontains=first_name)
        )
        
        if last_name:
            nickname_fighters = nickname_fighters.filter(last_name__iexact=last_name)
        
        if nickname_fighters.exists():
            return nickname_fighters.first(), 0.75
        
        return None, 0.0
    
    @classmethod
    def _calculate_name_similarity(cls, name1: str, name2: str) -> float:
        """Simple character-based similarity calculation"""
        name1 = name1.lower()
        name2 = name2.lower()
        
        # Simple Jaccard similarity on character sets
        set1 = set(name1.replace(' ', ''))
        set2 = set(name2.replace(' ', ''))
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union
    
    @classmethod
    def _apply_context_boost(cls, fighter: Fighter, context_data: dict, base_confidence: float) -> float:
        """Apply confidence boost based on additional context"""
        boost = 0.0
        
        # Nationality match
        if context_data.get('nationality') and fighter.nationality:
            if context_data['nationality'].lower() == fighter.nationality.lower():
                boost += 0.05
        
        # Event date context (fighter should be active around that time)
        if context_data.get('event_date') and fighter.date_of_birth:
            event_date = context_data['event_date']
            fighter_age_at_event = (event_date - fighter.date_of_birth).days / 365.25
            
            # Reasonable fighting age range
            if 18 <= fighter_age_at_event <= 45:
                boost += 0.03
            elif fighter_age_at_event > 45 or fighter_age_at_event < 18:
                boost -= 0.1  # Penalty for unrealistic age
        
        return min(base_confidence + boost, 1.0)
    
    @classmethod
    def bulk_match_opponents(cls, fight_histories, min_confidence=0.8) -> dict:
        """
        Bulk match opponents for multiple fight history records
        
        Returns:
            dict with statistics and results
        """
        results = {
            'total_processed': 0,
            'successful_matches': 0,
            'high_confidence_matches': 0,
            'failed_matches': 0,
            'matches': []
        }
        
        for fh in fight_histories:
            results['total_processed'] += 1
            
            # Skip if already linked
            if fh.opponent_fighter:
                continue
            
            opponent_fighter, confidence = cls.find_fighter_by_name(
                fh.opponent_first_name,
                fh.opponent_last_name,
                event_date=fh.event_date,
                context_data={
                    'nationality': getattr(fh, 'opponent_nationality', None),
                    'event_date': fh.event_date
                }
            )
            
            if opponent_fighter and confidence >= min_confidence:
                results['successful_matches'] += 1
                if confidence >= 0.9:
                    results['high_confidence_matches'] += 1
                
                results['matches'].append({
                    'fight_history': fh,
                    'opponent_fighter': opponent_fighter,
                    'confidence': confidence
                })
            else:
                results['failed_matches'] += 1
        
        return results