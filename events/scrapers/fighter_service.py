"""
Fighter Service for UFC Wikipedia Scraper
Handles fighter matching, creation, and duplicate prevention
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.utils import timezone

from fighters.models import Fighter, FighterNameVariation
from fighters.services.matching import FighterMatcher
from .schemas import FighterInfoSchema

logger = logging.getLogger(__name__)


class FighterService:
    """Service for managing fighters from Wikipedia scraping"""
    
    def __init__(self, confidence_threshold: float = 0.8):
        """
        Initialize fighter service
        
        Args:
            confidence_threshold: Minimum confidence for fighter matching
        """
        self.confidence_threshold = confidence_threshold
        self.matcher = FighterMatcher()
        
        # Statistics tracking
        self.stats = {
            'fighters_matched': 0,
            'fighters_created': 0,
            'fighters_updated': 0,
            'low_confidence_matches': 0,
            'duplicate_urls_found': 0
        }
    
    def get_or_create_fighter(self, fighter_data: FighterInfoSchema, 
                             event_date=None, context_data: Dict = None) -> Tuple[Fighter, bool, float]:
        """
        Get existing fighter or create new one with duplicate prevention
        
        Args:
            fighter_data: Pydantic schema with fighter information
            event_date: Date of the event for context
            context_data: Additional context for matching
            
        Returns:
            Tuple of (Fighter, created, confidence)
        """
        fighter_dict = fighter_data.model_dump()
        
        # Step 1: Try to find existing fighter
        existing_fighter, confidence = self._find_existing_fighter(
            fighter_dict, event_date, context_data
        )
        
        if existing_fighter and confidence >= self.confidence_threshold:
            # Update existing fighter with new data if needed
            updated = self._update_fighter_data(existing_fighter, fighter_dict)
            
            if updated:
                self.stats['fighters_updated'] += 1
            
            self.stats['fighters_matched'] += 1
            
            # Create name variation for this scraping
            self._create_name_variation(existing_fighter, fighter_dict)
            
            return existing_fighter, False, confidence
        
        elif existing_fighter:
            # Low confidence match - log for review
            self.stats['low_confidence_matches'] += 1
            logger.warning(
                f"Low confidence match ({confidence:.2f}) for {fighter_data.first_name} {fighter_data.last_name} "
                f"-> {existing_fighter.get_full_name()}"
            )
        
        # Step 2: Check for duplicate Wikipedia URLs
        if fighter_dict.get('wikipedia_url'):
            url_duplicate = self._check_wikipedia_url_duplicate(fighter_dict['wikipedia_url'])
            if url_duplicate:
                self.stats['duplicate_urls_found'] += 1
                logger.info(
                    f"Found existing fighter with same Wikipedia URL: {url_duplicate.get_full_name()}"
                )
                # Update the existing fighter and return it
                updated = self._update_fighter_data(url_duplicate, fighter_dict)
                if updated:
                    self.stats['fighters_updated'] += 1
                
                self._create_name_variation(url_duplicate, fighter_dict)
                return url_duplicate, False, 1.0  # High confidence for URL match
        
        # Step 3: Create new fighter
        new_fighter = self._create_new_fighter(fighter_dict)
        self.stats['fighters_created'] += 1
        
        # Create name variation
        self._create_name_variation(new_fighter, fighter_dict)
        
        logger.info(f"Created new fighter: {new_fighter.get_full_name()}")
        return new_fighter, True, 1.0
    
    def _find_existing_fighter(self, fighter_data: Dict, event_date=None, 
                             context_data: Dict = None) -> Tuple[Optional[Fighter], float]:
        """Find existing fighter using multiple matching strategies"""
        
        # Prepare context data
        full_context = context_data or {}
        full_context.update({
            'nationality': fighter_data.get('nationality'),
            'event_date': event_date
        })
        
        # Use the existing FighterMatcher service
        fighter, confidence = self.matcher.find_fighter_by_name(
            first_name=fighter_data['first_name'],
            last_name=fighter_data.get('last_name', ''),
            event_date=event_date,
            context_data=full_context
        )
        
        return fighter, confidence
    
    def _check_wikipedia_url_duplicate(self, wikipedia_url: str) -> Optional[Fighter]:
        """Check if any fighter already has this Wikipedia URL"""
        try:
            return Fighter.objects.filter(wikipedia_url=wikipedia_url).first()
        except Exception as e:
            logger.debug(f"Error checking Wikipedia URL duplicate: {e}")
            return None
    
    def _update_fighter_data(self, fighter: Fighter, new_data: Dict) -> bool:
        """Update existing fighter with new data from scraping"""
        updated = False
        
        try:
            # Update Wikipedia URL if not set
            if new_data.get('wikipedia_url') and not fighter.wikipedia_url:
                fighter.wikipedia_url = new_data['wikipedia_url']
                updated = True
            
            # Update nationality if not set
            if new_data.get('nationality') and not fighter.nationality:
                fighter.nationality = new_data['nationality']
                updated = True
            
            # Update nickname if not set
            if new_data.get('nickname') and not fighter.nickname:
                fighter.nickname = new_data['nickname']
                updated = True
            
            # Update data source to include Wikipedia
            if fighter.data_source != 'wikipedia' and new_data.get('wikipedia_url'):
                if fighter.data_source == 'manual':
                    fighter.data_source = 'wikipedia'
                else:
                    fighter.data_source = f"{fighter.data_source},wikipedia"
                updated = True
            
            # Update last data update timestamp
            if updated:
                fighter.last_data_update = timezone.now()
                fighter.save()
                
                logger.debug(f"Updated fighter data for {fighter.get_full_name()}")
        
        except Exception as e:
            logger.error(f"Error updating fighter {fighter.id}: {e}")
        
        return updated
    
    def _create_new_fighter(self, fighter_data: Dict) -> Fighter:
        """Create a new fighter from scraped data"""
        
        # Prepare fighter data
        create_data = {
            'first_name': fighter_data['first_name'],
            'last_name': fighter_data.get('last_name', ''),
            'nickname': fighter_data.get('nickname', ''),
            'nationality': fighter_data.get('nationality', ''),
            'wikipedia_url': fighter_data.get('wikipedia_url', ''),
            'data_source': 'wikipedia',
            'last_data_update': timezone.now(),
            'is_active': True
        }
        
        # Generate display name if not provided
        if not create_data.get('display_name'):
            name_parts = [create_data['first_name']]
            if create_data['last_name']:
                name_parts.append(create_data['last_name'])
            create_data['display_name'] = ' '.join(name_parts)
        
        try:
            with transaction.atomic():
                fighter = Fighter.objects.create(**create_data)
                return fighter
                
        except Exception as e:
            logger.error(f"Error creating fighter: {e}")
            raise
    
    def _create_name_variation(self, fighter: Fighter, scraped_data: Dict):
        """Create a name variation entry for the scraped name"""
        try:
            # Build full name from scraped data
            name_parts = [scraped_data['first_name']]
            if scraped_data.get('last_name'):
                name_parts.append(scraped_data['last_name'])
            full_name = ' '.join(name_parts)
            
            # Don't create variation if it's identical to the main name
            if full_name.lower() == fighter.get_full_name().lower():
                return
            
            # Check if variation already exists
            existing_variation = FighterNameVariation.objects.filter(
                fighter=fighter,
                full_name_variation__iexact=full_name
            ).first()
            
            if not existing_variation:
                FighterNameVariation.objects.create(
                    fighter=fighter,
                    first_name_variation=scraped_data['first_name'],
                    last_name_variation=scraped_data.get('last_name', ''),
                    full_name_variation=full_name,
                    variation_type='wikipedia',
                    source='wikipedia_scraper'
                )
                
                logger.debug(f"Created name variation '{full_name}' for {fighter.get_full_name()}")
        
        except Exception as e:
            logger.debug(f"Error creating name variation: {e}")
    
    def bulk_process_fighters(self, fighters_data: List[FighterInfoSchema], 
                            event_date=None) -> Dict[str, Any]:
        """
        Process multiple fighters in bulk with statistics
        
        Args:
            fighters_data: List of fighter data from Gemini extraction
            event_date: Event date for context
            
        Returns:
            Processing results and statistics
        """
        results = {
            'processed_fighters': [],
            'statistics': self.stats.copy(),
            'errors': []
        }
        
        logger.info(f"Bulk processing {len(fighters_data)} fighters")
        
        for i, fighter_data in enumerate(fighters_data):
            try:
                fighter, created, confidence = self.get_or_create_fighter(
                    fighter_data,
                    event_date=event_date
                )
                
                results['processed_fighters'].append({
                    'fighter': fighter,
                    'fighter_data': fighter_data,
                    'created': created,
                    'confidence': confidence
                })
                
            except Exception as e:
                error_msg = f"Error processing fighter {i+1} ({fighter_data.first_name}): {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        # Update final statistics
        results['statistics'] = self.stats.copy()
        
        logger.info(
            f"Bulk processing completed: "
            f"{self.stats['fighters_created']} created, "
            f"{self.stats['fighters_matched']} matched, "
            f"{self.stats['fighters_updated']} updated"
        )
        
        return results
    
    def get_statistics(self) -> Dict[str, int]:
        """Get current processing statistics"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.stats = {
            'fighters_matched': 0,
            'fighters_created': 0,
            'fighters_updated': 0,
            'low_confidence_matches': 0,
            'duplicate_urls_found': 0
        }
    
    def validate_fighter_data(self, fighter_data: FighterInfoSchema) -> List[str]:
        """
        Validate fighter data quality
        
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check required fields
        if not fighter_data.first_name.strip():
            warnings.append("First name is empty")
        
        # Check name format
        if len(fighter_data.first_name.split()) > 3:
            warnings.append("First name appears to contain multiple names")
        
        # Check Wikipedia URL format
        if fighter_data.wikipedia_url:
            if not fighter_data.wikipedia_url.startswith('https://en.wikipedia.org/wiki/'):
                warnings.append("Wikipedia URL format is incorrect")
        
        # Check nationality format
        if fighter_data.nationality:
            if len(fighter_data.nationality) < 2:
                warnings.append("Nationality appears too short")
        
        return warnings