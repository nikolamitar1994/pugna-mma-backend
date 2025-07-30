"""
Enhanced Django Management Command for UFC Wikipedia Scraping
============================================================

Production-ready Wikipedia UFC scraper with comprehensive error handling,
rate limiting, and integration with existing Django models.
"""

import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.conf import settings
from django.utils import timezone

from events.models import Event, Fight, FightParticipant
from fighters.models import Fighter, PendingFighter
from organizations.models import Organization, WeightClass
from events.scrapers.wikipedia_enhanced_scraper import WikipediaUFCEnhancedScraper
from fighters.services.scraping_integration import enhanced_fighter_integration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Enhanced Wikipedia UFC scraper command with production features:
    - Comprehensive error handling and logging
    - Rate limiting for Wikipedia API (1 req/sec)
    - Django transaction management
    - Fighter creation and pending fighter workflow
    - Complete event/fight/participant creation
    - Progress tracking and statistics
    """
    
    help = 'Enhanced UFC Wikipedia scraper with fighter creation and full integration'
    
    def add_arguments(self, parser):
        """Add command-line arguments for flexible scraping options"""
        
        # Scraping scope
        parser.add_argument('--event', type=str, help='Scrape specific event by name or Wikipedia URL')
        parser.add_argument('--event-number', type=int, help='Scrape specific UFC event by number (e.g., 300)')
        parser.add_argument('--recent', type=int, help='Scrape events from last N days')
        parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'), 
                          help='Scrape events in date range (YYYY-MM-DD format)')
        parser.add_argument('--all-events', action='store_true', 
                          help='Scrape all UFC events (use with caution)')
        
        # Processing options
        parser.add_argument('--create-fighters', action='store_true', default=True,
                          help='Automatically create Fighter records (default: True)')
        parser.add_argument('--pending-only', action='store_true',
                          help='Create PendingFighter records instead of Fighter records')
        parser.add_argument('--update-existing', action='store_true',
                          help='Update existing events and fighters')
        parser.add_argument('--verify-data', action='store_true',
                          help='Verify scraped data completeness after processing')
        
        # Rate limiting and performance
        parser.add_argument('--rate-limit', type=float, default=1.0,
                          help='Seconds between Wikipedia requests (default: 1.0)')
        parser.add_argument('--batch-size', type=int, default=5,
                          help='Number of events to process in each transaction (default: 5)')
        parser.add_argument('--max-retries', type=int, default=3,
                          help='Maximum retries for failed requests (default: 3)')
        
        # Output and debugging
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be scraped without making changes')
        parser.add_argument('--verbose', action='store_true',
                          help='Enable verbose logging')
        parser.add_argument('--quiet', action='store_true',
                          help='Suppress output except errors')
        parser.add_argument('--progress', action='store_true', default=True,
                          help='Show progress indicators (default: True)')
    
    def handle(self, *args, **options):
        """Main command handler with comprehensive error handling"""
        
        # Configure logging
        self._setup_logging(options)
        
        # Initialize scraper with rate limiting
        self.scraper = WikipediaUFCEnhancedScraper(
            rate_limit=options['rate_limit'],
            max_retries=options['max_retries']
        )
        
        # Configure fighter integration service
        enhanced_fighter_integration.create_fighters = options['create_fighters']
        enhanced_fighter_integration.use_pending_workflow = options['pending_only']
        enhanced_fighter_integration.reset_statistics()
        
        # Initialize statistics
        self.stats = {
            'events_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fights_created': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Ensure UFC organization exists
            self._ensure_ufc_organization()
            
            # Execute scraping based on options
            if options['event']:
                result = self._scrape_single_event(options)
            elif options['event_number']:
                result = self._scrape_event_by_number(options)
            elif options['recent']:
                result = self._scrape_recent_events(options)
            elif options['date_range']:
                result = self._scrape_date_range(options)
            elif options['all_events']:
                result = self._scrape_all_events(options)
            else:
                raise CommandError("No scraping target specified. Use --help for options.")
            
            # Display results
            self._display_results(result, options)
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nScraping interrupted by user"))
            self._display_stats(options)
        except Exception as e:
            logger.exception("Scraping failed with exception")
            self.stdout.write(self.style.ERROR(f"Scraping failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            self._display_stats(options)
    
    def _setup_logging(self, options):
        """Configure logging based on verbosity options"""
        
        if options['quiet']:
            log_level = logging.ERROR
        elif options['verbose']:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        
        logger.setLevel(log_level)
        
        # Add console handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    def _ensure_ufc_organization(self):
        """Ensure UFC organization exists in database"""
        
        try:
            self.ufc_org = Organization.objects.get(abbreviation='UFC')
            logger.info("Found existing UFC organization")
        except Organization.DoesNotExist:
            logger.info("Creating UFC organization")
            self.ufc_org = Organization.objects.create(
                name='Ultimate Fighting Championship',
                abbreviation='UFC',
                website='https://www.ufc.com',
                is_active=True
            )
    
    def _scrape_single_event(self, options) -> Dict[str, Any]:
        """Scrape a single event by name or URL"""
        
        event_identifier = options['event']
        
        if not options['quiet']:
            self.stdout.write(f"Scraping event: {event_identifier}")
        
        if options['dry_run']:
            return self._dry_run_single_event(event_identifier)
        
        try:
            with transaction.atomic():
                event_data = self.scraper.scrape_event(event_identifier)
                
                if not event_data:
                    raise CommandError(f"Could not scrape event: {event_identifier}")
                
                result = self._process_event_data(event_data, options)
                self.stats['events_processed'] += 1
                
                return {
                    'success': True,
                    'message': f"Successfully scraped {event_identifier}",
                    'event_data': result,
                    'statistics': self.stats
                }
                
        except Exception as e:
            logger.exception(f"Failed to scrape event {event_identifier}")
            self.stats['errors'].append(f"Event {event_identifier}: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to scrape {event_identifier}: {e}",
                'statistics': self.stats
            }
    
    def _scrape_event_by_number(self, options) -> Dict[str, Any]:
        """Scrape UFC event by number (e.g., UFC 300)"""
        
        event_number = options['event_number']
        event_name = f"UFC {event_number}"
        
        if not options['quiet']:
            self.stdout.write(f"Scraping {event_name}")
        
        # Convert to single event scraping
        options['event'] = event_name
        return self._scrape_single_event(options)
    
    def _process_event_data(self, event_data: Dict[str, Any], options) -> Dict[str, Any]:
        """
        Process scraped event data and create database records
        
        Args:
            event_data: Dictionary containing event information
            options: Command options
            
        Returns:
            Dictionary with processing results
        """
        
        # Create or update Event record
        event = self._create_or_update_event(event_data, options)
        
        # Process fight card
        fights_data = event_data.get('fights', [])
        created_fights = []
        
        for fight_data in fights_data:
            try:
                fight = self._process_fight_data(fight_data, event, options)
                if fight:
                    created_fights.append(fight)
                    self.stats['fights_created'] += 1
            except Exception as e:
                logger.warning(f"Failed to process fight: {e}")
                self.stats['warnings'].append(f"Fight processing: {str(e)}")
        
        return {
            'event': event,
            'fights_created': len(created_fights),
            'fights': created_fights
        }
    
    def _create_or_update_event(self, event_data: Dict[str, Any], options) -> Event:
        """Create or update Event record from scraped data"""
        
        event_name = event_data['name']
        event_date = event_data.get('date')
        
        if not event_date:
            raise ValueError(f"No date found for event: {event_name}")
        
        # Check if event exists
        existing_event = Event.objects.filter(
            name=event_name,
            date=event_date,
            organization=self.ufc_org
        ).first()
        
        if existing_event and not options['update_existing']:
            logger.info(f"Event already exists, skipping: {event_name}")
            self.stats['events_skipped'] += 1
            return existing_event
        
        # Prepare event data
        event_fields = {
            'organization': self.ufc_org,
            'name': event_name,
            'date': event_date,
            'location': event_data.get('location', ''),
            'venue': event_data.get('venue', ''),
            'city': event_data.get('city', ''),
            'state': event_data.get('state', ''),
            'country': event_data.get('country', ''),
            'attendance': event_data.get('attendance'),
            'gate_revenue': event_data.get('gate_revenue'),
            'ppv_buys': event_data.get('ppv_buys'),
            'wikipedia_url': event_data.get('wikipedia_url', ''),
            'status': 'completed'  # Assume completed for historical events
        }
        
        # Extract event number if available
        if 'event_number' in event_data:
            event_fields['event_number'] = event_data['event_number']
        
        if existing_event:
            # Update existing event
            for field, value in event_fields.items():
                if value is not None:  # Only update non-null values
                    setattr(existing_event, field, value)
            existing_event.save()
            
            logger.info(f"Updated event: {event_name}")
            self.stats['events_updated'] += 1
            return existing_event
        else:
            # Create new event
            event = Event.objects.create(**event_fields)
            
            logger.info(f"Created event: {event_name}")
            self.stats['events_created'] += 1
            return event
    
    def _process_fight_data(self, fight_data: Dict[str, Any], event: Event, options) -> Optional[Fight]:
        """Process individual fight data and create Fight + FightParticipant records"""
        
        fighters = fight_data.get('fighters', [])
        if len(fighters) != 2:
            logger.warning(f"Fight must have exactly 2 fighters, found {len(fighters)}")
            return None
        
        # Get or create fighters with Wikipedia URLs if available
        fighter_objects = []
        fighter_urls = fight_data.get('fighter_urls', {})
        
        for fighter_name in fighters:
            wikipedia_url = fighter_urls.get(fighter_name)
            context_data = {
                'event_name': event.name,
                'event_date': event.date,
                'weight_class': fight_data.get('weight_class')
            }
            
            fighter = self._get_or_create_fighter(
                fighter_name=fighter_name,
                wikipedia_url=wikipedia_url,
                context_data=context_data
            )
            if fighter:
                fighter_objects.append(fighter)
        
        if len(fighter_objects) != 2:
            logger.warning(f"Could not resolve both fighters: {fighters}")
            return None
        
        # Check if fight already exists
        existing_fight = Fight.objects.filter(
            event=event,
            participants__fighter__in=fighter_objects
        ).distinct().first()
        
        if existing_fight and not options['update_existing']:
            logger.debug(f"Fight already exists: {fighters[0]} vs {fighters[1]}")
            return existing_fight
        
        # Create Fight record
        fight_fields = {
            'event': event,
            'fight_order': fight_data.get('fight_order', 1),
            'is_main_event': fight_data.get('is_main_event', False),
            'is_title_fight': fight_data.get('is_title_fight', False),
            'scheduled_rounds': fight_data.get('scheduled_rounds', 3),
            'status': 'completed',
            'method': fight_data.get('method', ''),
            'method_details': fight_data.get('method_details', ''),
            'ending_round': fight_data.get('ending_round'),
            'ending_time': fight_data.get('ending_time', ''),
            'referee': fight_data.get('referee', '')
        }
        
        # Get weight class if available
        weight_class_name = fight_data.get('weight_class')
        if weight_class_name:
            weight_class = WeightClass.objects.filter(
                organization=self.ufc_org,
                name__icontains=weight_class_name
            ).first()
            if weight_class:
                fight_fields['weight_class'] = weight_class
        
        # Set winner if available
        winner_name = fight_data.get('winner')
        if winner_name:
            for fighter in fighter_objects:
                if winner_name.lower() in fighter.get_full_name().lower():
                    fight_fields['winner'] = fighter
                    break
        
        if existing_fight:
            # Update existing fight
            for field, value in fight_fields.items():
                if value is not None:
                    setattr(existing_fight, field, value)
            existing_fight.save()
            fight = existing_fight
        else:
            # Create new fight
            fight = Fight.objects.create(**fight_fields)
        
        # Create or update FightParticipant records
        self._create_fight_participants(fight, fighter_objects, fight_data)
        
        # Create interconnected fight history perspectives
        try:
            fight.create_history_perspectives()
            logger.debug(f"Created fight history perspectives for {fight}")
        except Exception as e:
            logger.warning(f"Failed to create fight history perspectives: {e}")
        
        return fight
    
    def _get_or_create_fighter(self, fighter_name: str, wikipedia_url: Optional[str] = None, context_data: Optional[Dict[str, Any]] = None) -> Optional[Fighter]:
        """Get existing fighter or create new Fighter/PendingFighter using enhanced integration"""
        
        return enhanced_fighter_integration.process_scraped_fighter(
            fighter_name=fighter_name,
            wikipedia_url=wikipedia_url,
            context_data=context_data or {}
        )
    
    
    def _create_fight_participants(self, fight: Fight, fighters: List[Fighter], fight_data: Dict[str, Any]):
        """Create FightParticipant records for the fight"""
        
        # Remove existing participants if updating
        fight.participants.all().delete()
        
        winner_name = fight_data.get('winner', '')
        
        for i, fighter in enumerate(fighters):
            corner = 'red' if i == 0 else 'blue'
            
            # Determine result
            result = ''
            if winner_name:
                if winner_name.lower() in fighter.get_full_name().lower():
                    result = 'win'
                else:
                    result = 'loss'
            
            FightParticipant.objects.create(
                fight=fight,
                fighter=fighter,
                corner=corner,
                result=result
            )
    
    def _display_results(self, result: Dict[str, Any], options):
        """Display scraping results to user"""
        
        if options['quiet']:
            return
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(result['message']))
        else:
            self.stdout.write(self.style.ERROR(result['message']))
        
        self._display_stats(options)
    
    def _display_stats(self, options):
        """Display scraping statistics"""
        
        if options['quiet']:
            return
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SCRAPING STATISTICS")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Events processed: {self.stats['events_processed']}")
        self.stdout.write(f"Events created: {self.stats['events_created']}")
        self.stdout.write(f"Events updated: {self.stats['events_updated']}")
        self.stdout.write(f"Events skipped: {self.stats['events_skipped']}")
        self.stdout.write(f"Fights created: {self.stats['fights_created']}")
        
        # Get fighter integration statistics
        fighter_stats = enhanced_fighter_integration.get_statistics()
        self.stdout.write(f"Fighters found: {fighter_stats['fighters_found']}")
        self.stdout.write(f"Fighters created: {fighter_stats['fighters_created']}")
        self.stdout.write(f"Pending fighters created: {fighter_stats['pending_fighters_created']}")
        self.stdout.write(f"Fighters updated: {fighter_stats['fighters_updated']}")
        self.stdout.write(f"Wikipedia URLs added: {fighter_stats['wikipedia_urls_added']}")
        self.stdout.write(f"Name variations added: {fighter_stats['name_variations_added']}")
        
        if self.stats['errors']:
            self.stdout.write(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(self.stats['errors']) > 5:
                self.stdout.write(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        if self.stats['warnings'] and options['verbose']:
            self.stdout.write(f"\nWarnings ({len(self.stats['warnings'])}):")
            for warning in self.stats['warnings'][:5]:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
            if len(self.stats['warnings']) > 5:
                self.stdout.write(f"  ... and {len(self.stats['warnings']) - 5} more warnings")
    
    def _dry_run_single_event(self, event_identifier: str) -> Dict[str, Any]:
        """Perform dry run for single event"""
        
        try:
            event_data = self.scraper.get_event_info(event_identifier)
            
            if not event_data:
                return {
                    'success': False,
                    'message': f"Could not find event: {event_identifier}",
                    'dry_run': True
                }
            
            fights_count = len(event_data.get('fights', []))
            fighters_list = []
            
            for fight in event_data.get('fights', []):
                fighters_list.extend(fight.get('fighters', []))
            
            unique_fighters = len(set(fighters_list))
            
            return {
                'success': True,
                'message': f"Would process event: {event_data['name']}",
                'dry_run': True,
                'event_info': {
                    'name': event_data['name'],
                    'date': event_data.get('date'),
                    'location': event_data.get('location'),
                    'fights_count': fights_count,
                    'unique_fighters': unique_fighters,
                    'fighters': list(set(fighters_list))
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Dry run failed: {e}",
                'dry_run': True
            }