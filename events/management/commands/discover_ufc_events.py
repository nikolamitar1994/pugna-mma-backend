"""
Django management command for UFC Event Discovery (Phase 1)
Discovers all UFC events from Wikipedia and creates basic Event records
"""
import logging
from datetime import datetime
from typing import List, Tuple, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from events.models import Event
from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
from organizations.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Discover all UFC events from Wikipedia and create basic Event records (Phase 1 of two-phase scraping)'
    
    def add_arguments(self, parser):
        """Add command line arguments"""
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving to database'
        )
        
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing events with new Wikipedia URLs and dates'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of events to discover (for testing)'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Setup logging
        if options['verbose']:
            logging.getLogger('events.scrapers').setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS('Starting UFC Event Discovery (Phase 1)')
        )
        
        try:
            # Get UFC organization
            ufc_org = self._get_ufc_organization()
            
            # Initialize scraper
            scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)  # Faster for discovery
            
            # Test connectivity
            is_connected, message = scraper.test_connectivity()
            if not is_connected:
                raise CommandError(f"Wikipedia connectivity failed: {message}")
            
            self.stdout.write(f"✅ {message}")
            
            # Discover events from Wikipedia
            self.stdout.write('Discovering UFC events from Wikipedia...')
            event_data = self._discover_events(scraper, options.get('limit'))
            
            if not event_data:
                raise CommandError("No events discovered from Wikipedia")
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Discovered {len(event_data)} UFC events')
            )
            
            # Create/update Event records
            if not options['dry_run']:
                self.stdout.write('Creating Event records in database...')
            else:
                self.stdout.write('DRY RUN: Simulating Event record creation...')
            
            results = self._create_event_records(
                event_data, 
                ufc_org, 
                options['dry_run'],
                options['update_existing']
            )
            
            # Display results
            self._display_results(results, options)
            
        except Exception as e:
            logger.exception("Event discovery failed")
            raise CommandError(f"Event discovery failed: {str(e)}")
    
    def _get_ufc_organization(self) -> Organization:
        """Get or create UFC organization"""
        try:
            return Organization.objects.get(abbreviation='UFC')
        except Organization.DoesNotExist:
            raise CommandError(
                "UFC organization not found. Please create it first or run initial setup."
            )
    
    def _discover_events(self, scraper: WikipediaGeminiScraper, limit: Optional[int]) -> List[Tuple[str, str, Optional[str]]]:
        """
        Discover events from Wikipedia
        
        Returns:
            List of (event_name, wikipedia_url, date_str) tuples
        """
        try:
            # Get all UFC event URLs (no limit by default to get all 716 events)
            event_urls = scraper.get_ufc_event_urls(limit=limit)
            
            if not event_urls:
                return []
            
            # Convert to the format we need with date extraction
            event_data = []
            
            for event_name, wikipedia_url in event_urls:
                # Try to extract date from event name or URL if possible
                # For now, we'll set date to None and let Phase 2 extract it properly
                date_str = None
                
                event_data.append((event_name, wikipedia_url, date_str))
            
            return event_data
            
        except Exception as e:
            logger.error(f"Error discovering events: {e}")
            return []
    
    def _create_event_records(self, event_data: List[Tuple[str, str, Optional[str]]], 
                            ufc_org: Organization, dry_run: bool, update_existing: bool) -> dict:
        """
        Create Event records in database
        
        Returns:
            Dictionary with creation statistics
        """
        results = {
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'errors': []
        }
        
        for i, (event_name, wikipedia_url, date_str) in enumerate(event_data, 1):
            try:
                if not dry_run:
                    with transaction.atomic():
                        # Check if event already exists
                        existing_event = Event.objects.filter(
                            name__iexact=event_name,
                            organization=ufc_org
                        ).first()
                        
                        if existing_event:
                            if update_existing:
                                # Update existing event
                                existing_event.wikipedia_url = wikipedia_url
                                if date_str:
                                    parsed_date = parse_date(date_str)
                                    if parsed_date:
                                        existing_event.date = parsed_date
                                existing_event.save()
                                results['events_updated'] += 1
                                
                                if i <= 10:  # Show first 10
                                    self.stdout.write(f"  ✏️  Updated: {event_name}")
                            else:
                                results['events_skipped'] += 1
                                if i <= 5:  # Show first 5 skipped
                                    self.stdout.write(f"  ⏭️  Skipped existing: {event_name}")
                        else:
                            # Create new event
                            # Use a placeholder date if none provided
                            event_date = parse_date(date_str) if date_str else timezone.now().date()
                            
                            Event.objects.create(
                                organization=ufc_org,
                                name=event_name,
                                date=event_date,
                                location='TBD',  # Will be extracted in Phase 2
                                wikipedia_url=wikipedia_url,
                                processing_status='discovered',
                                processing_attempts=0
                            )
                            results['events_created'] += 1
                            
                            if i <= 10:  # Show first 10
                                self.stdout.write(f"  ✅ Created: {event_name}")
                else:
                    # Dry run - just count what would be created
                    existing_event = Event.objects.filter(
                        name__iexact=event_name,
                        organization=ufc_org
                    ).first()
                    
                    if existing_event:
                        if update_existing:
                            results['events_updated'] += 1
                        else:
                            results['events_skipped'] += 1
                    else:
                        results['events_created'] += 1
                    
                    if i <= 10:  # Show first 10
                        action = "UPDATE" if existing_event and update_existing else "SKIP" if existing_event else "CREATE"
                        self.stdout.write(f"  🔍 [{action}]: {event_name}")
                
            except Exception as e:
                error_msg = f"Error processing {event_name}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                if len(results['errors']) <= 5:  # Show first 5 errors
                    self.stdout.write(f"  ❌ Error: {event_name} - {str(e)}")
        
        return results
    
    def _display_results(self, results: dict, options: dict):
        """Display creation results"""
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('EVENT DISCOVERY RESULTS'))
        self.stdout.write('='*60)
        
        self.stdout.write(f"Events created: {results['events_created']}")
        self.stdout.write(f"Events updated: {results['events_updated']}")
        self.stdout.write(f"Events skipped: {results['events_skipped']}")
        
        total_events = results['events_created'] + results['events_updated'] + results['events_skipped']
        self.stdout.write(f"Total events processed: {total_events}")
        
        if results['errors']:
            self.stdout.write(f"\n❌ Errors encountered: {len(results['errors'])}")
            if len(results['errors']) > 5:
                self.stdout.write("   (showing first 5 errors)")
            for error in results['errors'][:5]:
                self.stdout.write(f"   • {error}")
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\n🔍 DRY RUN: No data was actually saved to the database')
            )
        else:
            self.stdout.write(f"\n✨ Phase 1 Complete! Events are ready for Phase 2 processing.")
            self.stdout.write(f"Next step: Run 'python manage.py scrape_ufc_wikipedia_gemini --from-database'")
        
        self.stdout.write('='*60)