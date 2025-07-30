"""
Fighter Scraping Integration Service
===================================

Enhanced service for integrating scraped fighter data with the existing Fighter model system.
Handles fighter matching, creation, Wikipedia URL extraction, and pending fighter workflow.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from ..models import PendingFighter, Fighter, FighterNameVariation
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


class EnhancedFighterScrapingIntegration:
    """
    Enhanced service for integrating Wikipedia scraped fighter data.
    Designed to work with the enhanced Wikipedia UFC scraper.
    """
    
    def __init__(self, create_fighters: bool = True, use_pending_workflow: bool = False):
        """
        Initialize integration service
        
        Args:
            create_fighters: Whether to automatically create Fighter records
            use_pending_workflow: Whether to use PendingFighter workflow for review
        """
        self.create_fighters = create_fighters
        self.use_pending_workflow = use_pending_workflow
        
        # Statistics tracking
        self.stats = {
            'fighters_found': 0,
            'fighters_created': 0,
            'pending_fighters_created': 0,
            'fighters_updated': 0,
            'wikipedia_urls_added': 0,
            'name_variations_added': 0,
            'matching_errors': []
        }
    
    def process_scraped_fighter(self, 
                              fighter_name: str, 
                              wikipedia_url: Optional[str] = None,
                              context_data: Optional[Dict[str, Any]] = None) -> Optional[Fighter]:
        """
        Process a fighter discovered during Wikipedia scraping
        
        Args:
            fighter_name: Fighter's name as found in Wikipedia
            wikipedia_url: Fighter's Wikipedia URL if available  
            context_data: Additional context (event, weight class, etc.)
            
        Returns:
            Fighter instance or None if using pending workflow
        """
        
        if not fighter_name or not fighter_name.strip():
            logger.warning("Empty fighter name provided")
            return None
        
        fighter_name = fighter_name.strip()
        context_data = context_data or {}
        
        logger.debug(f"Processing scraped fighter: {fighter_name}")
        
        try:
            # Parse fighter name into components using enhanced parsing
            name_components = self._parse_fighter_name_enhanced(fighter_name)
            
            # Try to find existing fighter using multiple strategies
            existing_fighter = self._find_existing_fighter_enhanced(name_components, context_data)
            
            if existing_fighter:
                logger.debug(f"Found existing fighter: {existing_fighter.get_full_name()}")
                self.stats['fighters_found'] += 1
                
                # Update with new information if available
                updated = self._update_existing_fighter(existing_fighter, wikipedia_url, fighter_name)
                if updated:
                    self.stats['fighters_updated'] += 1
                
                return existing_fighter
            
            # No existing fighter found
            if self.use_pending_workflow:
                self._create_pending_fighter_enhanced(fighter_name, name_components, wikipedia_url, context_data)
                return None
            elif self.create_fighters:
                return self._create_new_fighter_enhanced(fighter_name, name_components, wikipedia_url, context_data)
            else:
                logger.warning(f"Fighter not found and creation disabled: {fighter_name}")
                return None
                
        except Exception as e:
            logger.exception(f"Error processing fighter {fighter_name}")
            self.stats['matching_errors'].append(f"{fighter_name}: {str(e)}")
            return None
    
    def _parse_fighter_name_enhanced(self, full_name: str) -> Dict[str, str]:
        """
        Enhanced fighter name parsing with better nickname handling
        
        Args:
            full_name: Complete fighter name
            
        Returns:
            Dictionary with name components
        """
        
        # Clean the name
        full_name = re.sub(r'\s+', ' ', full_name.strip())
        
        # Remove common prefixes/suffixes
        full_name = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.)\s+', '', full_name, flags=re.IGNORECASE)
        full_name = re.sub(r'\s+(Jr\.?|Sr\.?|III?|IV)$', '', full_name, flags=re.IGNORECASE)
        
        # Handle nicknames in various formats
        nickname = ''
        
        # Pattern 1: "John 'The Rock' Doe" or "John \"The Rock\" Doe"
        nickname_match = re.search(r'["\']([^"\']+)["\']', full_name)
        if nickname_match:
            nickname = nickname_match.group(1).strip()
            full_name = re.sub(r'\s*["\'][^"\']+["\']', '', full_name).strip()
        
        # Pattern 2: "John (The Rock) Doe"
        elif '(' in full_name and ')' in full_name:
            paren_match = re.search(r'\(([^)]+)\)', full_name)
            if paren_match:
                potential_nickname = paren_match.group(1).strip()
                # Only treat as nickname if it's not obviously other info (like birth year)
                if not re.match(r'^\d{4}$', potential_nickname):  # Not just a year
                    nickname = potential_nickname
                    full_name = re.sub(r'\s*\([^)]+\)', '', full_name).strip()
        
        # Split into parts
        name_parts = [part for part in full_name.split() if part]
        
        if not name_parts:
            return {'first_name': '', 'last_name': '', 'full_name': full_name, 'nickname': nickname}
        
        if len(name_parts) == 1:
            # Single name (like Brazilian fighters: "Ronaldo", "Shogun")
            return {
                'first_name': name_parts[0],
                'last_name': '',
                'full_name': name_parts[0],
                'nickname': nickname
            }
        elif len(name_parts) == 2:
            # Standard "First Last" format
            return {
                'first_name': name_parts[0],
                'last_name': name_parts[1],
                'full_name': ' '.join(name_parts),
                'nickname': nickname
            }
        else:
            # Multiple names - first name is first part, last name is remaining parts
            return {
                'first_name': name_parts[0],
                'last_name': ' '.join(name_parts[1:]),
                'full_name': ' '.join(name_parts),
                'nickname': nickname
            }
    
    def _find_existing_fighter_enhanced(self, 
                                      name_components: Dict[str, str], 
                                      context_data: Dict[str, Any]) -> Optional[Fighter]:
        """
        Enhanced fighter matching using multiple strategies
        
        Args:
            name_components: Parsed name components
            context_data: Additional context for matching
            
        Returns:
            Existing Fighter instance or None
        """
        
        first_name = name_components['first_name']
        last_name = name_components['last_name']
        full_name = name_components['full_name']
        nickname = name_components.get('nickname', '')
        
        # Strategy 1: Exact name match (case insensitive)
        exact_match = Fighter.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name
        ).first()
        
        if exact_match:
            logger.debug(f"Exact name match found: {exact_match.get_full_name()}")
            return exact_match
        
        # Strategy 2: Display name exact match
        display_name_match = Fighter.objects.filter(
            display_name__iexact=full_name
        ).first()
        
        if display_name_match:
            logger.debug(f"Display name match found: {display_name_match.get_full_name()}")
            return display_name_match
        
        # Strategy 3: Nickname match (if fighter has a unique nickname)
        if nickname:
            nickname_match = Fighter.objects.filter(
                nickname__iexact=nickname
            ).first()
            
            if nickname_match:
                logger.debug(f"Nickname match found: {nickname_match.get_full_name()}")
                return nickname_match
        
        # Strategy 4: Name variations search
        name_variation_match = FighterNameVariation.objects.filter(
            full_name_variation__iexact=full_name
        ).select_related('fighter').first()
        
        if name_variation_match:
            logger.debug(f"Name variation match found: {name_variation_match.fighter.get_full_name()}")
            return name_variation_match.fighter
        
        # Strategy 5: Use existing FighterMatcher service with context
        try:
            matched_fighter, confidence = FighterMatcher.find_fighter_by_name(
                first_name, 
                last_name, 
                context_data=context_data
            )
            
            if matched_fighter and confidence > 0.85:  # High confidence threshold
                logger.debug(f"FighterMatcher found fighter with confidence {confidence}: {matched_fighter.get_full_name()}")
                return matched_fighter
        
        except Exception as e:
            logger.warning(f"FighterMatcher error: {e}")
        
        # Strategy 6: Fuzzy matching with similarity scoring
        if len(first_name) > 2 and len(last_name) > 2:
            fuzzy_candidates = Fighter.objects.filter(
                Q(first_name__istartswith=first_name[:2]) &
                Q(last_name__istartswith=last_name[:2])
            )[:10]  # Limit candidates
            
            for candidate in fuzzy_candidates:
                similarity = self._calculate_name_similarity(full_name, candidate.get_full_name())
                if similarity > 0.9:  # Very high similarity
                    logger.debug(f"Fuzzy match found with similarity {similarity}: {candidate.get_full_name()}")
                    return candidate
        
        return None
    
    def _create_new_fighter_enhanced(self, 
                                   full_name: str,
                                   name_components: Dict[str, str],
                                   wikipedia_url: Optional[str],
                                   context_data: Dict[str, Any]) -> Fighter:
        """
        Create new Fighter record with enhanced data handling
        """
        
        logger.info(f"Creating new fighter: {full_name}")
        
        fighter_data = {
            'first_name': name_components['first_name'],
            'last_name': name_components['last_name'],
            'display_name': full_name,
            'data_source': 'wikipedia',
            'wikipedia_url': wikipedia_url or '',
            'nickname': name_components.get('nickname', '') or ''
        }
        
        # Add context data if available
        if 'nationality' in context_data:
            fighter_data['nationality'] = context_data['nationality']
        if 'weight_class' in context_data:
            # Could store weight class info or related data
            pass
        
        with transaction.atomic():
            fighter = Fighter.objects.create(**fighter_data)
            
            # Create name variation if full name differs from computed name
            computed_name = fighter.get_full_name()
            if full_name != computed_name:
                self._create_name_variation(fighter, full_name, 'scraped_variation')
            
            logger.info(f"Created fighter: {fighter.get_full_name()} (ID: {fighter.id})")
            self.stats['fighters_created'] += 1
            
            if wikipedia_url:
                self.stats['wikipedia_urls_added'] += 1
        
        return fighter
    
    def _create_pending_fighter_enhanced(self,
                                      full_name: str,
                                      name_components: Dict[str, str],
                                      wikipedia_url: Optional[str],
                                      context_data: Dict[str, Any]) -> None:
        """
        Create enhanced PendingFighter record with better data structure
        """
        
        logger.info(f"Creating pending fighter: {full_name}")
        
        # Check if pending fighter already exists
        existing_pending = PendingFighter.objects.filter(
            full_name_raw=full_name,
            status__in=['pending', 'approved']
        ).first()
        
        if existing_pending:
            logger.debug(f"Pending fighter already exists: {full_name}")
            return None
        
        source_data = {
            'parsed_name': name_components,
            'wikipedia_url': wikipedia_url,
            'context': context_data,
            'scraper_version': 'enhanced_wikipedia_scraper_v1.0'
        }
        
        pending_fighter = PendingFighter.objects.create(
            first_name=name_components['first_name'],
            last_name=name_components['last_name'],
            full_name_raw=full_name,
            nickname=name_components.get('nickname', '') or '',
            source='scraper',
            source_data=source_data,
            confidence_level='medium'
        )
        
        # Run fuzzy matching to find potential duplicates
        pending_fighter.run_fuzzy_matching()
        
        logger.info(f"Created pending fighter: {full_name} (ID: {pending_fighter.id})")
        self.stats['pending_fighters_created'] += 1
        
        return None
    
    def _update_existing_fighter(self,
                               fighter: Fighter,
                               wikipedia_url: Optional[str],
                               scraped_name: str) -> bool:
        """
        Update existing fighter with new information from Wikipedia scraping
        """
        
        updated = False
        
        # Add Wikipedia URL if not present
        if wikipedia_url and not fighter.wikipedia_url:
            fighter.wikipedia_url = wikipedia_url
            updated = True
            self.stats['wikipedia_urls_added'] += 1
            logger.debug(f"Added Wikipedia URL to {fighter.get_full_name()}")
        
        # Create name variation if scraped name is different
        computed_name = fighter.get_full_name()
        if scraped_name != computed_name and scraped_name != fighter.display_name:
            # Check if variation already exists
            existing_variation = FighterNameVariation.objects.filter(
                fighter=fighter,
                full_name_variation=scraped_name
            ).exists()
            
            if not existing_variation:
                self._create_name_variation(fighter, scraped_name, 'scraped_variation')
                self.stats['name_variations_added'] += 1
                logger.debug(f"Added name variation '{scraped_name}' to {fighter.get_full_name()}")
        
        # Update data source if it was manual and now we have Wikipedia data
        if fighter.data_source == 'manual' and wikipedia_url:
            fighter.data_source = 'wikipedia'
            updated = True
        
        if updated:
            fighter.save()
        
        return updated
    
    def _create_name_variation(self, fighter: Fighter, variation_name: str, variation_type: str):
        """Create a name variation record"""
        
        # Parse variation name
        variation_components = self._parse_fighter_name_enhanced(variation_name)
        
        try:
            FighterNameVariation.objects.create(
                fighter=fighter,
                first_name_variation=variation_components['first_name'],
                last_name_variation=variation_components['last_name'],
                full_name_variation=variation_name,
                variation_type=variation_type,
                source='wikipedia_scraping'
            )
        except Exception as e:
            logger.warning(f"Failed to create name variation: {e}")
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names using character overlap
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        if name1 == name2:
            return 1.0
        
        # Character-based similarity
        set1 = set(name1.replace(' ', ''))
        set2 = set(name2.replace(' ', ''))
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        char_similarity = intersection / union if union > 0 else 0.0
        
        # Word-based similarity for better matching
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        word_intersection = len(words1.intersection(words2))
        word_union = len(words1.union(words2))
        
        word_similarity = word_intersection / word_union if word_union > 0 else 0.0
        
        # Combine both similarities with weight on word similarity
        return (char_similarity * 0.3) + (word_similarity * 0.7)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset integration statistics"""
        for key in self.stats:
            if isinstance(self.stats[key], list):
                self.stats[key] = []
            else:
                self.stats[key] = 0


# Singleton instances
scraping_integration_service = ScrapingIntegrationService()
enhanced_fighter_integration = EnhancedFighterScrapingIntegration()