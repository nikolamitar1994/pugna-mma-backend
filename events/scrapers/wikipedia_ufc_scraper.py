"""
Complete Wikipedia UFC Scraper
==============================

Main scraper class that orchestrates the complete UFC event scraping process.
Integrates all components to scrape Wikipedia data and populate the database.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from django.db import transaction
from django.core.management.base import CommandError

from .wikipedia_base import WikipediaUFCScraper
from .fighter_extractor import FighterExtractor
from .event_processor import EventProcessor
from events.models import Event

logger = logging.getLogger(__name__)


class WikipediaUFCScraperComplete:
    """
    Complete Wikipedia UFC scraper that handles the entire scraping workflow.
    
    Features:
    - Full UFC events list scraping
    - Individual event details extraction
    - Fighter information extraction and creation
    - Event and fight card database integration
    - Progress tracking and error handling
    - Selective scraping (by date range, event numbers, etc.)
    """
    
    def __init__(self):
        """Initialize scraper components"""
        
        # Initialize core components
        self.wiki_scraper = WikipediaUFCScraper()
        self.fighter_extractor = FighterExtractor(self.wiki_scraper)
        self.event_processor = EventProcessor(self.wiki_scraper, self.fighter_extractor)
        
        # Scraping statistics
        self.stats = {
            'events_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fighters_created': 0,
            'fights_created': 0,
            'errors': []
        }
    
    def scrape_all_ufc_events(self, 
                             update_existing: bool = False,
                             limit: Optional[int] = None,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Scrape all UFC events from Wikipedia
        
        Args:
            update_existing: Whether to update existing events
            limit: Maximum number of events to process
            start_date: Only process events after this date
            end_date: Only process events before this date
            
        Returns:
            Dictionary with scraping results and statistics
        """
        
        logger.info("Starting complete UFC events scraping from Wikipedia")
        
        try:
            # Get list of all UFC events
            logger.info("Fetching UFC events list...")
            events_list = self.wiki_scraper.get_ufc_events_list()
            
            if not events_list:
                raise CommandError("No events found in Wikipedia events list")
            
            logger.info(f"Found {len(events_list)} events in Wikipedia")
            
            # Filter events based on criteria
            filtered_events = self._filter_events_list(
                events_list, 
                start_date=start_date, 
                end_date=end_date
            )
            
            logger.info(f"Processing {len(filtered_events)} events after filtering")
            
            # Limit number of events if specified
            if limit:
                filtered_events = filtered_events[:limit]
                logger.info(f"Limited to {len(filtered_events)} events")
            
            # Process events
            processed_events = self._process_events_batch(
                filtered_events, 
                update_existing=update_existing
            )
            
            # Compile final statistics
            self.stats['events_processed'] = len(filtered_events)
            self.stats['processed_events'] = processed_events
            
            logger.info(f"Scraping completed. Statistics: {self._format_stats()}")
            
            return {
                'success': True,
                'events_processed': processed_events,
                'statistics': self.stats,
                'message': f"Successfully processed {len(processed_events)} UFC events"
            }
            
        except Exception as e:
            logger.error(f"Error in complete UFC scraping: {e}")
            self.stats['errors'].append(f"Complete scraping error: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats,
                'message': f"Scraping failed: {e}"
            }
    
    def scrape_specific_events(self, 
                              event_identifiers: List[str],
                              update_existing: bool = False) -> Dict[str, Any]:
        """
        Scrape specific UFC events by identifier
        
        Args:
            event_identifiers: List of event names, numbers, or Wikipedia page titles
            update_existing: Whether to update existing events
            
        Returns:
            Dictionary with scraping results
        """
        
        logger.info(f"Scraping {len(event_identifiers)} specific UFC events")
        
        processed_events = []
        
        for identifier in event_identifiers:
            try:
                logger.info(f"Processing event: {identifier}")
                
                # Determine if this is a page title or need to find it
                page_title = self._resolve_event_identifier(identifier)
                
                if not page_title:
                    logger.warning(f"Could not resolve event identifier: {identifier}")
                    self.stats['events_skipped'] += 1
                    continue
                
                # Get event details
                event_details = self.wiki_scraper.get_event_details(page_title)
                
                if not event_details:
                    logger.warning(f"Could not fetch event details for: {page_title}")
                    self.stats['events_skipped'] += 1
                    continue
                
                # Create basic event data structure
                event_data = self._convert_details_to_event_data(event_details, page_title)
                
                # Process event
                event = self.event_processor.process_event(event_data, update_existing)
                processed_events.append(event)
                
                if hasattr(event, '_state') and event._state.adding:
                    self.stats['events_created'] += 1
                else:
                    self.stats['events_updated'] += 1
                
                self.stats['events_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing event {identifier}: {e}")
                self.stats['errors'].append(f"Event {identifier}: {e}")
                continue
        
        return {
            'success': len(processed_events) > 0,
            'events_processed': processed_events,
            'statistics': self.stats,
            'message': f"Processed {len(processed_events)} specific events"
        }
    
    def scrape_recent_events(self, 
                           months_back: int = 6,
                           update_existing: bool = True) -> Dict[str, Any]:
        """
        Scrape recent UFC events (useful for regular updates)
        
        Args:
            months_back: How many months back to scrape
            update_existing: Whether to update existing events
            
        Returns:
            Dictionary with scraping results
        """
        
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        end_date = date.today()
        start_date = end_date - relativedelta(months=months_back)
        
        logger.info(f"Scraping UFC events from {start_date} to {end_date}")
        
        return self.scrape_all_ufc_events(
            update_existing=update_existing,
            start_date=start_date,
            end_date=end_date
        )
    
    def scrape_event_by_number(self, event_number: int, update_existing: bool = False) -> Dict[str, Any]:
        """
        Scrape specific UFC event by number
        
        Args:
            event_number: UFC event number (e.g., 300)
            update_existing: Whether to update if exists
            
        Returns:
            Dictionary with scraping results
        """
        
        return self.scrape_specific_events([f"UFC {event_number}"], update_existing)
    
    def _filter_events_list(self, 
                           events_list: List[Dict[str, Any]], 
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Filter events list based on date criteria"""
        
        filtered = events_list
        
        if start_date:
            filtered = [
                event for event in filtered 
                if event.get('date_obj') and event['date_obj'] >= start_date
            ]
        
        if end_date:
            filtered = [
                event for event in filtered 
                if event.get('date_obj') and event['date_obj'] <= end_date
            ]
        
        return filtered
    
    def _process_events_batch(self, 
                             events_list: List[Dict[str, Any]], 
                             update_existing: bool = False) -> List[Event]:
        """Process a batch of events with detailed tracking"""
        
        processed_events = []
        
        for i, event_data in enumerate(events_list, 1):
            try:
                logger.info(f"Processing event {i}/{len(events_list)}: {event_data.get('event_name', 'Unknown')}")
                
                # Check if we need to get detailed data
                if not event_data.get('fights') and event_data.get('wiki_page_title'):
                    logger.info(f"Fetching detailed data for: {event_data['wiki_page_title']}")
                    
                    detailed_data = self.wiki_scraper.get_event_details(event_data['wiki_page_title'])
                    
                    if detailed_data:
                        # Merge detailed data with basic event info
                        event_data.update(detailed_data)
                    else:
                        logger.warning(f"Could not get detailed data for: {event_data['wiki_page_title']}")
                
                # Process the event
                event = self.event_processor.process_event(event_data, update_existing)
                processed_events.append(event)
                
                # Track statistics
                if hasattr(event, '_state') and event._state.adding:
                    self.stats['events_created'] += 1
                else:
                    self.stats['events_updated'] += 1
                
                # Count fights and fighters
                fights_count = event.fights.count()
                self.stats['fights_created'] += fights_count
                
                logger.info(f"Event processed: {event.name} with {fights_count} fights")
                
            except Exception as e:
                logger.error(f"Error processing event {i}: {event_data.get('event_name', 'Unknown')}: {e}")
                self.stats['errors'].append(f"Event {event_data.get('event_name', 'Unknown')}: {e}")
                self.stats['events_skipped'] += 1
                continue
        
        return processed_events
    
    def _resolve_event_identifier(self, identifier: str) -> Optional[str]:
        """Resolve event identifier to Wikipedia page title"""
        
        # If it looks like a page title already, use it
        if '_' in identifier and not ' ' in identifier:
            return identifier
        
        # Try to find in events list
        try:
            events_list = self.wiki_scraper.get_ufc_events_list()
            
            for event in events_list:
                # Match by name
                if identifier.lower() in event.get('event_name', '').lower():
                    return event.get('wiki_page_title')
                
                # Match by event number if it's a number
                try:
                    event_num = int(identifier)
                    if event.get('event_number') == event_num:
                        return event.get('wiki_page_title')
                except ValueError:
                    pass
        
        except Exception as e:
            logger.warning(f"Error resolving event identifier {identifier}: {e}")
        
        # Try direct page title variations
        variations = [
            identifier.replace(' ', '_'),
            f"UFC_{identifier}",
            f"UFC_{identifier.replace('UFC ', '')}",
        ]
        
        for variation in variations:
            try:
                page_data = self.wiki_scraper.get_page_content(variation, use_cache=False)
                if page_data:
                    return variation
            except Exception:
                continue
        
        return None
    
    def _convert_details_to_event_data(self, event_details: Dict[str, Any], page_title: str) -> Dict[str, Any]:
        """Convert event details from scraper to event data format"""
        
        # Extract event name from page title
        event_name = page_title.replace('_', ' ')
        
        # Try to get event number
        import re
        event_number = None
        match = re.search(r'UFC\s+(\d+)', event_name, re.IGNORECASE)
        if match:
            event_number = int(match.group(1))
        
        event_data = {
            'event_name': event_name,
            'event_number': event_number,
            'wiki_page_title': page_title,
            'wikipedia_url': f"{self.wiki_scraper.base_wiki_url}/wiki/{page_title}",
            'fights': event_details.get('fights', []),
            'bonuses': event_details.get('bonuses', []),
            'records': event_details.get('records', [])
        }
        
        # Extract additional data from event details
        if 'event_date' in event_details:
            event_data['date'] = event_details['event_date']
        
        if 'venue' in event_details:
            event_data['venue'] = event_details['venue']
        
        if 'location' in event_details:
            event_data['location'] = event_details['location']
        
        return event_data
    
    def _format_stats(self) -> str:
        """Format statistics for logging"""
        
        return (
            f"Events: {self.stats['events_processed']} processed, "
            f"{self.stats['events_created']} created, "
            f"{self.stats['events_updated']} updated, "
            f"{self.stats['events_skipped']} skipped, "
            f"{self.stats['fights_created']} fights created, "
            f"{len(self.stats['errors'])} errors"
        )
    
    def get_scraping_statistics(self) -> Dict[str, Any]:
        """Get current scraping statistics"""
        
        return {
            'statistics': self.stats.copy(),
            'summary': self._format_stats()
        }
    
    def reset_statistics(self):
        """Reset scraping statistics"""
        
        self.stats = {
            'events_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fighters_created': 0,
            'fights_created': 0,
            'errors': []
        }
    
    @transaction.atomic
    def scrape_and_verify_event(self, event_identifier: str, update_existing: bool = False) -> Dict[str, Any]:
        """
        Scrape single event with detailed verification
        
        Args:
            event_identifier: Event identifier
            update_existing: Whether to update existing
            
        Returns:
            Detailed results with verification info
        """
        
        logger.info(f"Scraping and verifying event: {event_identifier}")
        
        try:
            # Reset stats for this operation
            self.reset_statistics()
            
            # Scrape the event
            result = self.scrape_specific_events([event_identifier], update_existing)
            
            if not result['success'] or not result['events_processed']:
                return {
                    'success': False,
                    'error': 'Event could not be processed',
                    'details': result
                }
            
            event = result['events_processed'][0]
            
            # Verify the event data
            verification = self._verify_event_data(event)
            
            return {
                'success': True,
                'event': event,
                'verification': verification,
                'statistics': self.stats,
                'message': f"Successfully processed and verified event: {event.name}"
            }
            
        except Exception as e:
            logger.error(f"Error in scrape and verify: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats
            }
    
    def _verify_event_data(self, event: Event) -> Dict[str, Any]:
        """Verify scraped event data for completeness and accuracy"""
        
        verification = {
            'completeness_score': 0.0,
            'issues': [],
            'warnings': [],
            'stats': {}
        }
        
        # Check basic event data
        required_fields = ['name', 'date', 'organization']
        optional_fields = ['venue', 'location', 'attendance', 'wikipedia_url']
        
        required_score = 0
        for field in required_fields:
            if getattr(event, field, None):
                required_score += 1
            else:
                verification['issues'].append(f"Missing required field: {field}")
        
        optional_score = 0
        for field in optional_fields:
            if getattr(event, field, None):
                optional_score += 1
        
        # Check fights data
        fights = event.fights.all()
        fights_count = fights.count()
        
        verification['stats'] = {
            'fights_count': fights_count,
            'fighters_count': 0,
            'title_fights': 0,
            'main_events': 0
        }
        
        if fights_count == 0:
            verification['issues'].append("No fights found for event")
        else:
            # Check fight data quality
            fighters_set = set()
            
            for fight in fights:
                participants = fight.participants.all()
                verification['stats']['fighters_count'] += participants.count()
                
                for participant in participants:
                    fighters_set.add(participant.fighter.id)
                
                if fight.is_title_fight:
                    verification['stats']['title_fights'] += 1
                
                if fight.is_main_event:
                    verification['stats']['main_events'] += 1
                
                # Check for missing fight data
                if not fight.method:
                    verification['warnings'].append(f"Fight {fight.fight_order} missing method")
                
                if participants.count() != 2:
                    verification['issues'].append(f"Fight {fight.fight_order} has {participants.count()} participants (expected 2)")
            
            verification['stats']['unique_fighters'] = len(fighters_set)
        
        # Calculate completeness score
        total_possible = len(required_fields) + len(optional_fields) + (1 if fights_count > 0 else 0)
        total_actual = required_score + optional_score + (1 if fights_count > 0 else 0)
        
        verification['completeness_score'] = round(total_actual / total_possible, 2) if total_possible > 0 else 0.0
        
        return verification