"""
Django Management Command for UFC Wikipedia Scraping
===================================================

Provides command-line interface for running the Wikipedia UFC scraper.
Supports various options for different scraping scenarios.
"""

import logging
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from events.scrapers.wikipedia_base import WikipediaUFCScraperBase
from events.scrapers.fighter_extractor import FighterExtractor
from events.scrapers.event_processor import EventProcessor


class Command(BaseCommand):
    help = 'Scrape UFC events from Wikipedia and populate the database'
    
    def add_arguments(self, parser):
        """Add command-line arguments"""
        
        # Scraping scope options
        parser.add_argument(
            '--all',
            action='store_true',
            help='Scrape all UFC events from Wikipedia'
        )
        
        parser.add_argument(
            '--recent',
            type=int,
            metavar='MONTHS',
            help='Scrape events from the last N months (e.g., --recent 6)'
        )
        
        parser.add_argument(
            '--event',
            type=str,
            action='append',
            metavar='EVENT',
            help='Scrape specific event(s) by name or number (can be used multiple times)'
        )
        
        parser.add_argument(
            '--number',
            type=int,
            metavar='N',
            help='Scrape specific UFC event by number (e.g., --number 300)'
        )
        
        # Date range options
        parser.add_argument(
            '--start-date',
            type=str,
            metavar='YYYY-MM-DD',
            help='Only scrape events after this date'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            metavar='YYYY-MM-DD',
            help='Only scrape events before this date'
        )
        
        # Processing options
        parser.add_argument(
            '--limit',
            type=int,
            metavar='N',
            help='Limit the number of events to process'
        )
        
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing events instead of skipping them'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scraped without actually scraping'
        )
        
        # Output options
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress non-error output'
        )
        
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify scraped data completeness and quality'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Configure logging
        self._configure_logging(options)
        
        # Validate arguments
        try:
            self._validate_arguments(options)
        except CommandError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return
        
        # Initialize scraper components
        self.wiki_scraper = WikipediaUFCScraperBase()
        self.fighter_extractor = FighterExtractor()
        self.event_processor = EventProcessor()
        
        # Determine scraping mode and execute
        try:
            if options['all']:
                result = self._scrape_all_events(options)
            elif options['recent']:
                result = self._scrape_recent_events(options)
            elif options['event']:
                result = self._scrape_specific_events(options)
            elif options['number']:
                result = self._scrape_event_by_number(options)
            else:
                raise CommandError("No scraping mode specified. Use --help for options.")
            
            # Display results
            self._display_results(result, options)
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nScraping interrupted by user"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scraping failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
    
    def _configure_logging(self, options):
        """Configure logging based on options"""
        
        if options['quiet']:
            log_level = logging.ERROR
        elif options['verbose']:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        
        # Configure logger
        logger = logging.getLogger('events.scrapers')
        logger.setLevel(log_level)
        
        # Create console handler if not exists
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    def _validate_arguments(self, options):
        """Validate command arguments"""
        
        # Check that at least one scraping mode is specified
        modes = [options['all'], options['recent'], options['event'], options['number']]
        if not any(modes):
            raise CommandError(
                "You must specify a scraping mode: --all, --recent, --event, or --number"
            )
        
        # Check that only one mode is specified
        if sum(bool(mode) for mode in modes) > 1:
            raise CommandError(
                "You can only specify one scraping mode at a time"
            )
        
        # Validate date formats
        for date_option in ['start_date', 'end_date']:
            if options[date_option]:
                try:
                    datetime.strptime(options[date_option], '%Y-%m-%d')
                except ValueError:
                    raise CommandError(
                        f"Invalid date format for --{date_option.replace('_', '-')}. "
                        f"Use YYYY-MM-DD format."
                    )
        
        # Validate numeric options
        if options['recent'] and options['recent'] <= 0:
            raise CommandError("--recent must be a positive number")
        
        if options['limit'] and options['limit'] <= 0:
            raise CommandError("--limit must be a positive number")
        
        if options['number'] and options['number'] <= 0:
            raise CommandError("--number must be a positive number")
    
    def _scrape_all_events(self, options):
        """Scrape all UFC events"""
        
        if not options['quiet']:
            self.stdout.write("Scraping all UFC events from Wikipedia...")
        
        # Parse date options
        start_date = self._parse_date(options['start_date']) if options['start_date'] else None
        end_date = self._parse_date(options['end_date']) if options['end_date'] else None
        
        if options['dry_run']:
            return self._dry_run_all_events(start_date, end_date, options['limit'])
        
        return self._scrape_events_batch(
            event_list=self._get_filtered_events(start_date, end_date, options['limit']),
            update_existing=options['update_existing'],
            options=options
        )
    
    def _scrape_recent_events(self, options):
        """Scrape recent UFC events"""
        
        months_back = options['recent']
        
        if not options['quiet']:
            self.stdout.write(f"Scraping UFC events from the last {months_back} months...")
        
        if options['dry_run']:
            return self._dry_run_recent_events(months_back)
        
        from dateutil.relativedelta import relativedelta
        
        end_date = date.today()
        start_date = end_date - relativedelta(months=months_back)
        
        return self._scrape_events_batch(
            event_list=self._get_filtered_events(start_date, end_date, None),
            update_existing=options['update_existing'],
            options=options
        )
    
    def _scrape_specific_events(self, options):
        """Scrape specific events"""
        
        events = options['event']
        
        if not options['quiet']:
            self.stdout.write(f"Scraping specific events: {', '.join(events)}")
        
        if options['dry_run']:
            return self._dry_run_specific_events(events)
        
        # Convert event names to event data format
        event_list = []
        for event_name in events:
            # Try to resolve the event identifier
            page_title = self._resolve_event_identifier(event_name)
            if page_title:
                event_list.append({
                    'event_name': event_name,
                    'wiki_link': page_title,
                    'date': '',
                    'venue': '',
                    'location': ''
                })
        
        return self._scrape_events_batch(
            event_list=event_list,
            update_existing=options['update_existing'],
            options=options
        )
    
    def _scrape_event_by_number(self, options):
        """Scrape event by number"""
        
        event_number = options['number']
        
        if not options['quiet']:
            self.stdout.write(f"Scraping UFC {event_number}...")
        
        if options['dry_run']:
            return self._dry_run_event_by_number(event_number)
        
        event_name = f"UFC {event_number}"
        page_title = self._resolve_event_identifier(event_name)
        
        if not page_title:
            return {
                'success': False,
                'message': f"Could not find UFC {event_number} on Wikipedia",
                'error': f"Event page not found"
            }
        
        event_list = [{
            'event_name': event_name,
            'wiki_link': page_title,
            'date': '',
            'venue': '',
            'location': ''
        }]
        
        return self._scrape_events_batch(
            event_list=event_list,
            update_existing=options['update_existing'],
            options=options
        )
    
    def _dry_run_all_events(self, start_date, end_date, limit):
        """Dry run for all events"""
        
        try:
            events_list = self.wiki_scraper.get_ufc_events_list()
            
            # Apply filters
            if start_date:
                events_list = [e for e in events_list if e.get('date_obj') and e['date_obj'] >= start_date]
            
            if end_date:
                events_list = [e for e in events_list if e.get('date_obj') and e['date_obj'] <= end_date]
            
            if limit:
                events_list = events_list[:limit]
            
            return {
                'success': True,
                'dry_run': True,
                'events_count': len(events_list),
                'events_list': events_list,
                'message': f"Would process {len(events_list)} events"
            }
            
        except Exception as e:
            return {
                'success': False,
                'dry_run': True,
                'error': str(e),
                'message': f"Dry run failed: {e}"
            }
    
    def _dry_run_recent_events(self, months_back):
        """Dry run for recent events"""
        
        from dateutil.relativedelta import relativedelta
        
        end_date = date.today()
        start_date = end_date - relativedelta(months=months_back)
        
        return self._dry_run_all_events(start_date, end_date, None)
    
    def _dry_run_specific_events(self, events):
        """Dry run for specific events"""
        
        resolved_events = []
        
        for event in events:
            page_title = self._resolve_event_identifier(event)
            if page_title:
                resolved_events.append({
                    'identifier': event,
                    'page_title': page_title,
                    'url': f"https://en.wikipedia.org/wiki/{page_title}"
                })
        
        return {
            'success': True,
            'dry_run': True,
            'events_count': len(resolved_events),
            'events_list': resolved_events,
            'message': f"Would process {len(resolved_events)} specific events"
        }
    
    def _dry_run_event_by_number(self, event_number):
        """Dry run for event by number"""
        
        return self._dry_run_specific_events([f"UFC {event_number}"])
    
    def _display_results(self, result, options):
        """Display scraping results"""
        
        if options['quiet'] and result['success']:
            return
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(result['message']))
            
            # Display statistics
            if 'statistics' in result:
                self._display_statistics(result['statistics'], options)
            
            # Display verification results
            if 'verification' in result:
                self._display_verification(result['verification'], options)
            
            # Display dry run results
            if result.get('dry_run'):
                self._display_dry_run_results(result, options)
        
        else:
            self.stdout.write(self.style.ERROR(result['message']))
            
            if 'error' in result:
                self.stdout.write(self.style.ERROR(f"Error: {result['error']}"))
            
            # Still show statistics if available
            if 'statistics' in result and options['verbose']:
                self._display_statistics(result['statistics'], options)
    
    def _display_statistics(self, stats, options):
        """Display scraping statistics"""
        
        if options['quiet']:
            return
        
        self.stdout.write("\nScraping Statistics:")
        self.stdout.write(f"  Events processed: {stats.get('events_processed', 0)}")
        self.stdout.write(f"  Events created: {stats.get('events_created', 0)}")
        self.stdout.write(f"  Events updated: {stats.get('events_updated', 0)}")
        self.stdout.write(f"  Events skipped: {stats.get('events_skipped', 0)}")
        self.stdout.write(f"  Fights created: {stats.get('fights_created', 0)}")
        
        if stats.get('errors') and options['verbose']:
            self.stdout.write(f"\nErrors ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Show first 10 errors
                self.stdout.write(f"  - {error}")
            
            if len(stats['errors']) > 10:
                self.stdout.write(f"  ... and {len(stats['errors']) - 10} more errors")
    
    def _display_verification(self, verification, options):
        """Display verification results"""
        
        if options['quiet']:
            return
        
        self.stdout.write("\nData Verification:")
        self.stdout.write(f"  Completeness Score: {verification['completeness_score']:.2f}")
        
        if verification['stats']:
            stats = verification['stats']
            self.stdout.write(f"  Fights: {stats.get('fights_count', 0)}")
            self.stdout.write(f"  Unique Fighters: {stats.get('unique_fighters', 0)}")
            self.stdout.write(f"  Title Fights: {stats.get('title_fights', 0)}")
            self.stdout.write(f"  Main Events: {stats.get('main_events', 0)}")
        
        if verification['issues']:
            self.stdout.write(self.style.ERROR(f"\nIssues ({len(verification['issues'])}):"))
            for issue in verification['issues']:
                self.stdout.write(self.style.ERROR(f"  - {issue}"))
        
        if verification['warnings'] and options['verbose']:
            self.stdout.write(self.style.WARNING(f"\nWarnings ({len(verification['warnings'])}):"))
            for warning in verification['warnings']:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
    
    def _display_dry_run_results(self, result, options):
        """Display dry run results"""
        
        if options['quiet']:
            return
        
        self.stdout.write("\nDry Run Results:")
        self.stdout.write(f"  Events found: {result.get('events_count', 0)}")
        
        if options['verbose'] and 'events_list' in result:
            events_list = result['events_list']
            
            self.stdout.write("\nEvents that would be processed:")
            for i, event in enumerate(events_list[:20], 1):  # Show first 20
                if isinstance(event, dict):
                    if 'event_name' in event:
                        # From events list
                        name = event['event_name']
                        date_str = event.get('date', 'Unknown date')
                        self.stdout.write(f"  {i:3d}. {name} ({date_str})")
                    else:
                        # From specific events
                        identifier = event.get('identifier', 'Unknown')
                        page_title = event.get('page_title', 'Unknown')
                        self.stdout.write(f"  {i:3d}. {identifier} -> {page_title}")
            
            if len(events_list) > 20:
                self.stdout.write(f"  ... and {len(events_list) - 20} more events")
    
    def _parse_date(self, date_str):
        """Parse date string to date object"""
        
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f"Invalid date format: {date_str}")
    
    def _get_filtered_events(self, start_date=None, end_date=None, limit=None):
        """Get filtered list of UFC events"""
        
        events_list = self.wiki_scraper.get_ufc_events_list()
        
        # Parse dates for events that don't have date_obj
        for event in events_list:
            if 'date_obj' not in event and event.get('date'):
                try:
                    from dateutil.parser import parse
                    event['date_obj'] = parse(event['date']).date()
                except:
                    event['date_obj'] = None
        
        # Apply filters
        if start_date:
            events_list = [e for e in events_list if e.get('date_obj') and e['date_obj'] >= start_date]
        
        if end_date:
            events_list = [e for e in events_list if e.get('date_obj') and e['date_obj'] <= end_date]
        
        if limit:
            events_list = events_list[:limit]
        
        return events_list
    
    def _resolve_event_identifier(self, event_identifier):
        """Resolve event identifier to Wikipedia page title"""
        
        # Clean the identifier
        identifier = event_identifier.strip()
        
        # If it's already a Wikipedia URL, extract the page title
        if 'wikipedia.org/wiki/' in identifier:
            return identifier.split('/wiki/')[-1]
        
        # Try direct page lookup
        if self.wiki_scraper.get_page_content(identifier):
            return identifier
        
        # Try with 'UFC_' prefix
        if not identifier.upper().startswith('UFC'):
            ufc_identifier = f"UFC_{identifier}"
            if self.wiki_scraper.get_page_content(ufc_identifier):
                return ufc_identifier
        
        # Try replacing spaces with underscores
        underscore_identifier = identifier.replace(' ', '_')
        if self.wiki_scraper.get_page_content(underscore_identifier):
            return underscore_identifier
        
        # Search for the page
        search_results = self.wiki_scraper.search_pages(identifier, limit=5)
        for result in search_results:
            if 'UFC' in result and identifier.replace('UFC ', '').replace('UFC_', '') in result:
                return result
        
        return None
    
    def _scrape_events_batch(self, event_list, update_existing=False, options=None):
        """Scrape a batch of events using the modular scraper system"""
        
        statistics = {
            'events_processed': 0,
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fights_created': 0,
            'errors': []
        }
        
        if not options:
            options = {}
        
        for event_data in event_list:
            try:
                if not options.get('quiet'):
                    self.stdout.write(f"Processing: {event_data.get('event_name', 'Unknown')}")
                
                # Get event page content
                page_title = event_data.get('wiki_link')
                if not page_title:
                    statistics['events_skipped'] += 1
                    continue
                
                content = self.wiki_scraper.get_page_content(page_title)
                if not content:
                    statistics['events_skipped'] += 1
                    statistics['errors'].append(f"Could not fetch content for {page_title}")
                    continue
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract fighters
                fighters_data = self.fighter_extractor.extract_fighters_from_event(
                    soup, event_data.get('event_name', '')
                )
                
                # Create fighters in database
                fighters = self.fighter_extractor.create_or_update_fighters(fighters_data)
                
                # Process event and fights
                event = self.event_processor.process_event(event_data, soup, fighters)
                
                if event:
                    statistics['events_created'] += 1
                    statistics['fights_created'] += event.fights.count()
                else:
                    statistics['events_skipped'] += 1
                
                statistics['events_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error processing {event_data.get('event_name', 'Unknown')}: {str(e)}"
                statistics['errors'].append(error_msg)
                if options.get('verbose'):
                    self.stdout.write(self.style.ERROR(error_msg))
        
        # Compile final statistics
        fighter_stats = self.fighter_extractor.get_stats()
        event_stats = self.event_processor.get_stats()
        
        statistics.update({
            'fighters_created': fighter_stats.get('created_fighters', 0),
            'fighters_updated': fighter_stats.get('updated_fighters', 0),
            'fighters_matched': fighter_stats.get('matched_fighters', 0),
            'wikipedia_urls_added': fighter_stats.get('fighter_urls_added', 0)
        })
        
        success = len(statistics['errors']) == 0 or statistics['events_created'] > 0
        
        return {
            'success': success,
            'message': f"Processed {statistics['events_processed']} events, created {statistics['events_created']} events and {statistics['fights_created']} fights",
            'statistics': statistics
        }