"""
Scraping integration service for pending entities workflow.
Provides hooks and utilities for integrating scraped data with the pending entities system.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.utils import timezone

from ..models import PendingFighter, Fighter
from .matching import FighterMatcher
from events.models import Event

logger = logging.getLogger(__name__)


class ScrapingIntegrationService:
    """
    Service for integrating scraped data with the pending entities workflow.
    Handles automatic fighter discovery, matching, and pending entity creation.
    """
    
    def __init__(self):
        self.stats = {
            'fighters_processed': 0,
            'new_pending_created': 0,
            'existing_pending_updated': 0,
            'duplicates_found': 0,
            'errors': 0
        }
        
        # Confidence thresholds for automatic processing
        self.auto_match_threshold = 0.95  # Auto-mark as duplicate
        self.manual_review_threshold = 0.8  # Flag for manual review
        self.new_fighter_threshold = 0.6   # Below this, likely new fighter
    
    def process_scraped_event_fighters(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process fighters discovered during event scraping.
        
        Args:
            event_data: Dictionary containing event info and fighter list
            
        Returns:
            Processing results and statistics
        """
        event_name = event_data.get('name', 'Unknown Event')
        fighters_list = event_data.get('fighters', [])
        event_url = event_data.get('url', '')
        event_date = event_data.get('date')
        
        logger.info(f"Processing {len(fighters_list)} fighters from {event_name}")
        
        # Try to find existing event
        event_obj = self.find_or_create_event(event_data)
        
        results = {
            'event_name': event_name,
            'event_obj': event_obj,
            'processed_fighters': [],
            'pending_fighters_created': [],
            'duplicates_identified': [],
            'errors': []
        }
        
        for fighter_data in fighters_list:
            try:
                result = self.process_single_scraped_fighter(
                    fighter_data, 
                    event_obj, 
                    event_url
                )
                
                results['processed_fighters'].append(result)
                
                if result['action'] == 'created_pending':
                    results['pending_fighters_created'].append(result['pending_fighter'])
                elif result['action'] == 'identified_duplicate':
                    results['duplicates_identified'].append(result)
                
                self.stats['fighters_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing fighter {fighter_data.get('name', 'Unknown')}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                self.stats['errors'] += 1
        
        return results
    
    def process_single_scraped_fighter(
        self, 
        fighter_data: Dict[str, Any], 
        event_obj: Optional[Event], 
        source_url: str
    ) -> Dict[str, Any]:
        """
        Process a single scraped fighter.
        
        Args:
            fighter_data: Fighter information from scraper
            event_obj: Event object if found/created
            source_url: URL where fighter was discovered
            
        Returns:
            Processing result with action taken
        """
        fighter_name = fighter_data.get('name', '').strip()
        if not fighter_name:
            raise ValueError("Fighter name is required")
        
        # Parse name components
        name_parts = self.parse_fighter_name(fighter_name)
        
        # Check for existing fighters first
        existing_match = self.find_existing_fighter(name_parts, fighter_data)
        
        if existing_match['fighter'] and existing_match['confidence'] >= self.auto_match_threshold:
            # High confidence match - this is an existing fighter
            return {
                'action': 'identified_duplicate',
                'fighter_name': fighter_name,
                'existing_fighter': existing_match['fighter'],
                'confidence': existing_match['confidence'],
                'pending_fighter': None
            }
        
        # Check for existing pending fighter
        existing_pending = self.find_existing_pending_fighter(name_parts, event_obj)
        
        if existing_pending:
            # Update existing pending fighter with new information
            self.update_pending_fighter(existing_pending, fighter_data, event_obj, source_url)
            
            return {
                'action': 'updated_pending',
                'fighter_name': fighter_name,
                'pending_fighter': existing_pending,
                'was_updated': True
            }
        
        # Create new pending fighter
        pending_fighter = self.create_pending_fighter(
            name_parts, 
            fighter_data, 
            event_obj, 
            source_url
        )
        
        # Run fuzzy matching to find potential duplicates
        self.run_matching_analysis(pending_fighter, existing_match)
        
        return {
            'action': 'created_pending',
            'fighter_name': fighter_name,
            'pending_fighter': pending_fighter,
            'potential_matches': pending_fighter.potential_matches
        }
    
    def parse_fighter_name(self, fighter_name: str) -> Dict[str, str]:
        """
        Parse fighter name into components.
        Handles various name formats including nicknames.
        """
        # Remove common prefixes/suffixes
        cleaned_name = fighter_name.strip()
        
        # Handle nickname patterns like: John "The Rock" Doe
        nickname = ''
        if '"' in cleaned_name:
            parts = cleaned_name.split('"')
            if len(parts) >= 3:
                nickname = parts[1]
                # Reconstruct name without nickname
                cleaned_name = (parts[0] + ' ' + ' '.join(parts[2:])).strip()
        
        # Handle nickname patterns like: John (The Rock) Doe
        elif '(' in cleaned_name and ')' in cleaned_name:
            start = cleaned_name.find('(')
            end = cleaned_name.find(')')
            if start < end:
                nickname = cleaned_name[start+1:end]
                cleaned_name = (cleaned_name[:start] + ' ' + cleaned_name[end+1:]).strip()
        
        # Split into name parts
        name_parts = cleaned_name.split()
        
        if len(name_parts) == 1:
            # Single name (like "Shogun")
            first_name = name_parts[0]
            last_name = ''
        elif len(name_parts) == 2:
            # First and last name
            first_name = name_parts[0]
            last_name = name_parts[1]
        else:
            # Multiple parts - first is first name, rest is last name
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'nickname': nickname,
            'full_name_raw': fighter_name
        }
    
    def find_existing_fighter(
        self, 
        name_parts: Dict[str, str], 
        fighter_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Find existing fighter using fuzzy matching.
        """
        # Use the existing FighterMatcher service
        fighter, confidence = FighterMatcher.find_fighter_by_name(
            name_parts['first_name'],
            name_parts['last_name'],
            context_data={
                'nationality': fighter_data.get('nationality'),
                'weight_class': fighter_data.get('weight_class')
            }
        )
        
        return {
            'fighter': fighter,
            'confidence': confidence
        }
    
    def find_existing_pending_fighter(
        self, 
        name_parts: Dict[str, str], 
        event_obj: Optional[Event]
    ) -> Optional[PendingFighter]:
        """
        Find existing pending fighter for the same person.
        """
        # Look for pending fighters with same name
        candidates = PendingFighter.objects.filter(
            first_name__iexact=name_parts['first_name'],
            last_name__iexact=name_parts['last_name'],
            status__in=['pending', 'approved']
        )
        
        # If multiple candidates, prefer ones from the same event
        if event_obj and candidates.count() > 1:
            same_event_candidates = candidates.filter(source_event=event_obj)
            if same_event_candidates.exists():
                return same_event_candidates.first()
        
        return candidates.first()
    
    def create_pending_fighter(
        self, 
        name_parts: Dict[str, str], 
        fighter_data: Dict[str, Any], 
        event_obj: Optional[Event], 
        source_url: str
    ) -> PendingFighter:
        """
        Create new pending fighter from scraped data.
        """
        with transaction.atomic():
            pending_fighter = PendingFighter.objects.create(
                first_name=name_parts['first_name'],
                last_name=name_parts['last_name'],
                full_name_raw=name_parts['full_name_raw'],
                nickname=name_parts['nickname'],
                nationality=fighter_data.get('nationality', ''),
                weight_class_name=fighter_data.get('weight_class', ''),
                record_text=fighter_data.get('record', ''),
                source='scraper',
                source_event=event_obj,
                source_url=source_url,
                source_data=fighter_data,
                confidence_level='medium'  # Will be refined by matching
            )
            
            self.stats['new_pending_created'] += 1
            
        return pending_fighter
    
    def update_pending_fighter(
        self, 
        pending_fighter: PendingFighter, 
        fighter_data: Dict[str, Any], 
        event_obj: Optional[Event], 
        source_url: str
    ):
        """
        Update existing pending fighter with new scraped data.
        """
        updated_fields = []
        
        # Update nationality if not set
        if not pending_fighter.nationality and fighter_data.get('nationality'):
            pending_fighter.nationality = fighter_data['nationality']
            updated_fields.append('nationality')
        
        # Update weight class if not set
        if not pending_fighter.weight_class_name and fighter_data.get('weight_class'):
            pending_fighter.weight_class_name = fighter_data['weight_class']
            updated_fields.append('weight_class_name')
        
        # Update record if not set
        if not pending_fighter.record_text and fighter_data.get('record'):
            pending_fighter.record_text = fighter_data['record']
            updated_fields.append('record_text')
        
        # Add to source data
        if not pending_fighter.source_data:
            pending_fighter.source_data = {}
        
        # Merge source data
        pending_fighter.source_data.update({
            'additional_discovery': {
                'event': event_obj.name if event_obj else '',
                'url': source_url,
                'data': fighter_data,
                'discovered_at': timezone.now().isoformat()
            }
        })
        
        # Update source event if from a different event
        if event_obj and pending_fighter.source_event != event_obj:
            pending_fighter.source_data['multiple_events'] = True
        
        if updated_fields:
            pending_fighter.save()
            self.stats['existing_pending_updated'] += 1
            
            logger.info(
                f"Updated pending fighter {pending_fighter.get_display_name()} "
                f"with fields: {', '.join(updated_fields)}"
            )
    
    def run_matching_analysis(
        self, 
        pending_fighter: PendingFighter, 
        existing_match: Dict[str, Any]
    ):
        """
        Run comprehensive matching analysis on pending fighter.
        """
        # The pending fighter already runs fuzzy matching in its save method
        # But we can enhance it with the existing match data
        
        if existing_match['fighter'] and existing_match['confidence'] > 0.6:
            # Add the found match to potential matches if not already there
            match_data = {
                'fighter_id': str(existing_match['fighter'].id),
                'name': existing_match['fighter'].get_full_name(),
                'confidence': existing_match['confidence'],
                'nationality': existing_match['fighter'].nationality,
                'record': existing_match['fighter'].get_record_string(),
                'source': 'scraping_integration'
            }
            
            if not pending_fighter.potential_matches:
                pending_fighter.potential_matches = []
            
            # Check if this match is already in potential matches
            existing_ids = [m.get('fighter_id') for m in pending_fighter.potential_matches]
            if str(existing_match['fighter'].id) not in existing_ids:
                pending_fighter.potential_matches.append(match_data)
            
            # Update confidence level based on match quality
            if existing_match['confidence'] >= self.manual_review_threshold:
                pending_fighter.confidence_level = 'low'  # Needs manual review
                
                if existing_match['confidence'] >= self.auto_match_threshold:
                    # Very high confidence - auto-mark as duplicate
                    pending_fighter.status = 'duplicate'
                    pending_fighter.matched_fighter = existing_match['fighter']
            else:
                pending_fighter.confidence_level = 'high'  # Likely new fighter
            
            pending_fighter.save()
    
    def find_or_create_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """
        Find or create event from scraped data.
        """
        event_name = event_data.get('name', '').strip()
        event_date = event_data.get('date')
        organization_name = event_data.get('organization', '')
        
        if not event_name:
            return None
        
        try:
            # Try to find existing event by name and date
            if event_date:
                existing_event = Event.objects.filter(
                    name__iexact=event_name,
                    date=event_date
                ).first()
                
                if existing_event:
                    return existing_event
            
            # Try to find by name only (for future events without confirmed dates)
            existing_event = Event.objects.filter(
                name__iexact=event_name
            ).first()
            
            if existing_event:
                return existing_event
            
            # Create new event would require organization - skip for now
            logger.info(f"Event '{event_name}' not found in database")
            return None
            
        except Exception as e:
            logger.warning(f"Error finding/creating event '{event_name}': {e}")
            return None
    
    def generate_scraping_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive report of scraping integration results.
        """
        return {
            'statistics': self.stats.copy(),
            'pending_review_count': PendingFighter.objects.filter(
                status='pending',
                confidence_level='low'
            ).count(),
            'high_confidence_new_fighters': PendingFighter.objects.filter(
                status='pending',
                confidence_level='high'
            ).count(),
            'auto_identified_duplicates': PendingFighter.objects.filter(
                status='duplicate'
            ).count(),
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on scraping results."""
        recommendations = []
        
        low_confidence_count = PendingFighter.objects.filter(
            status='pending',
            confidence_level='low'
        ).count()
        
        if low_confidence_count > 10:
            recommendations.append(
                f"Review {low_confidence_count} low-confidence pending fighters "
                "that may be duplicates of existing fighters"
            )
        
        high_confidence_count = PendingFighter.objects.filter(
            status='pending',
            confidence_level='high'
        ).count()
        
        if high_confidence_count > 5:
            recommendations.append(
                f"Consider bulk-approving {high_confidence_count} high-confidence "
                "new fighters for creation"
            )
        
        return recommendations


# Singleton instance
scraping_integration_service = ScrapingIntegrationService()