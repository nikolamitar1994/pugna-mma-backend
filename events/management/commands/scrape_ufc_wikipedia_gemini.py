"""
Django management command for UFC Wikipedia scraping with Gemini AI
"""
import os
import json
import logging
from typing import List, Optional
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
from events.scrapers.gemini_processor import GeminiProcessor
from events.scrapers.data_importer import DataImporter
from events.scrapers.schemas import UFCEventSchema
from events.models import Event

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape UFC events from Wikipedia using Gemini AI for structured data extraction'
    
    def add_arguments(self, parser):
        """Add command line arguments"""
        
        # Basic options
        parser.add_argument(
            '--events',
            type=int,
            default=5,
            help='Number of events to scrape (default: 5, 0 = all available)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving to database'
        )
        
        parser.add_argument(
            '--gemini-api-key',
            type=str,
            help='Gemini API key (default: from environment or provided key)'
        )
        
        # Event selection
        parser.add_argument(
            '--event-urls',
            nargs='+',
            help='Specific Wikipedia URLs to scrape'
        )
        
        parser.add_argument(
            '--recent-events',
            action='store_true',
            help='Focus on most recent events first'
        )
        
        # Fighter handling options
        parser.add_argument(
            '--update-fighter-urls',
            action='store_true',
            help='Update fighter Wikipedia URLs for existing fighters'
        )
        
        parser.add_argument(
            '--skip-fighter-creation',
            action='store_true',
            help='Only match existing fighters, do not create new ones'
        )
        
        parser.add_argument(
            '--fighter-confidence-threshold',
            type=float,
            default=0.8,
            help='Minimum confidence for fighter matching (default: 0.8)'
        )
        
        # Processing options
        parser.add_argument(
            '--rate-limit',
            type=float,
            default=1.0,
            help='Delay between requests in seconds (default: 1.0)'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=3,
            help='Number of events to process in each batch (default: 3)'
        )
        
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing events in database'
        )
        
        # Output options
        parser.add_argument(
            '--output-json',
            type=str,
            help='Save extracted JSON data to file'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
        
        parser.add_argument(
            '--save-html',
            type=str,
            help='Directory to save raw HTML files for debugging'
        )
        
        parser.add_argument(
            '--max-retries',
            type=int,
            default=2,
            help='Maximum retries for failed events (default: 2)'
        )
        
        # Two-phase processing options
        parser.add_argument(
            '--from-database',
            action='store_true',
            help='Process events from database (Phase 2) instead of discovering from Wikipedia'
        )
        
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry processing failed events from database'
        )
        
        parser.add_argument(
            '--max-attempts',
            type=int,
            default=3,
            help='Maximum processing attempts per event (default: 3)'
        )
        
        parser.add_argument(
            '--processing-status',
            choices=['discovered', 'processing', 'failed'],
            default='discovered',
            help='Process events with specific status (default: discovered)'
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Setup logging
        if options['verbose']:
            logging.getLogger('events.scrapers').setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS('Starting UFC Wikipedia scraping with Gemini AI')
        )
        
        try:
            # Validate Gemini API key
            gemini_api_key = self._get_gemini_api_key(options)
            
            # Initialize services
            scraper = WikipediaGeminiScraper(rate_limit_delay=options['rate_limit'])
            processor = GeminiProcessor(gemini_api_key)
            importer = DataImporter(
                dry_run=options['dry_run'],
                update_existing=options['update_existing']
            )
            
            # Configure fighter service
            if options['skip_fighter_creation']:
                # Implementation would require updating FighterService
                self.stdout.write(
                    self.style.WARNING('Fighter creation skipping not yet implemented')
                )
            
            # Step 1: Get event URLs to scrape
            if options['from_database'] or options['retry_failed']:
                event_urls = self._get_events_from_database(options)
            else:
                event_urls = self._get_event_urls(scraper, options)
            
            if not event_urls:
                raise CommandError("No event URLs found to scrape")
            
            self.stdout.write(
                self.style.SUCCESS(f'Found {len(event_urls)} events to process')
            )
            
            # Step 2: Scrape Wikipedia pages
            self.stdout.write('Scraping Wikipedia pages...')
            scraped_results = scraper.batch_scrape_events(
                [url for _, url in event_urls],
                batch_size=options['batch_size'],
                max_retries=options['max_retries']
            )
            
            # Save HTML if requested
            if options['save_html']:
                self._save_html_files(scraped_results, options['save_html'])
            
            # Filter successful scrapes
            successful_scrapes = [r for r in scraped_results if r.extraction_success]
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully scraped {len(successful_scrapes)}/{len(scraped_results)} events'
                )
            )
            
            if not successful_scrapes:
                raise CommandError("No events were successfully scraped")
            
            # Step 3: Process with Gemini AI
            self.stdout.write('Processing with Gemini AI...')
            
            if options['from_database'] or options['retry_failed']:
                # Individual processing with status updates for Phase 2
                processed_events = self._process_events_with_status_updates(
                    successful_scrapes, processor, options
                )
            else:
                # Batch processing for Phase 1 (backward compatibility)
                processed_events = processor.batch_process_events(successful_scrapes)
            
            if not processed_events:
                if len(successful_scrapes) > 10:  # If we had many scraped events but none processed
                    self.stdout.write(
                        self.style.ERROR(
                            f"Warning: {len(successful_scrapes)} events scraped but none processed by Gemini. "
                            f"Check Gemini API key and rate limits."
                        )
                    )
                raise CommandError("No events were successfully processed by Gemini")
            
            elif len(processed_events) < len(successful_scrapes):
                # Some events processed, some failed - continue with what we have
                failed_count = len(successful_scrapes) - len(processed_events)
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: {failed_count} events failed Gemini processing. "
                        f"Continuing with {len(processed_events)} successful events."
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Gemini processed {len(processed_events)} events successfully'
                )
            )
            
            # Save JSON output if requested
            if options['output_json']:
                self._save_json_output(processed_events, options['output_json'])
            
            # Step 4: Import to database
            if not options['dry_run']:
                self.stdout.write('Importing to database...')
            else:
                self.stdout.write('DRY RUN: Simulating database import...')
            
            import_result = importer.batch_import_events(processed_events)
            
            # Display results
            self._display_results(import_result, options)
            
            # Final summary
            self._display_final_summary(
                len(event_urls), len(successful_scrapes), 
                len(processed_events), import_result
            )
            
        except Exception as e:
            logger.exception("Command execution failed")
            raise CommandError(f"Scraping failed: {str(e)}")
    
    def _get_gemini_api_key(self, options) -> str:
        """Get Gemini API key from options or environment"""
        api_key = options.get('gemini_api_key')
        
        if not api_key:
            # Try provided key first
            api_key = "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
        
        if not api_key:
            # Try environment variable
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            raise CommandError(
                "Gemini API key required. Provide via --gemini-api-key or GEMINI_API_KEY environment variable"
            )
        
        return api_key
    
    def _get_event_urls(self, scraper: WikipediaGeminiScraper, options) -> List[tuple]:
        """Get list of event URLs to scrape"""
        
        if options['event_urls']:
            # Use specific URLs provided
            event_urls = [(url.split('/')[-1], url) for url in options['event_urls']]
            self.stdout.write(f"Using {len(event_urls)} specific URLs provided")
            return event_urls
        
        # Get events from UFC events list page
        max_events = options['events'] if options['events'] > 0 else None
        
        self.stdout.write('Fetching UFC event URLs from Wikipedia...')
        event_urls = scraper.get_ufc_event_urls(limit=max_events)
        
        if options['recent_events']:
            # Sort by URL to get more recent events (UFC numbers are sequential)
            event_urls.sort(key=lambda x: x[1], reverse=True)
        
        return event_urls
    
    def _get_events_from_database(self, options) -> List[tuple]:
        """Get events from database for Phase 2 processing"""
        
        # Determine which events to process
        if options['retry_failed']:
            # Retry failed events
            status_filter = 'failed'
            max_attempts = options['max_attempts']
            events = Event.objects.filter(
                processing_status=status_filter,
                processing_attempts__lt=max_attempts
            ).order_by('-date', 'name')
            
            self.stdout.write(f"Found {events.count()} failed events to retry (attempts < {max_attempts})")
            
        else:
            # Process events with specified status
            status_filter = options['processing_status']
            events = Event.objects.filter(
                processing_status=status_filter
            ).order_by('-date', 'name')
            
            self.stdout.write(f"Found {events.count()} events with status '{status_filter}'")
        
        # Apply limit if specified
        if options['events'] > 0:
            events = events[:options['events']]
            self.stdout.write(f"Limited to {options['events']} events")
        
        # Convert to the expected format: (event_name, wikipedia_url)
        event_urls = []
        for event in events:
            if event.wikipedia_url:
                event_urls.append((event.name, event.wikipedia_url))
            else:
                self.stdout.write(
                    self.style.WARNING(f"Skipping {event.name} - no Wikipedia URL")
                )
        
        return event_urls
    
    def _process_events_with_status_updates(self, scraped_results, processor, options):
        """Process events individually with database status updates (Phase 2)"""
        from django.db import transaction
        from django.utils import timezone
        
        processed_events = []
        total_events = len(scraped_results)
        
        for i, scraped_data in enumerate(scraped_results, 1):
            # Find the corresponding Event record
            try:
                event = Event.objects.get(
                    name__iexact=scraped_data.event_title,
                    wikipedia_url=scraped_data.event_url
                )
            except Event.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Event not found in database: {scraped_data.event_title}")
                )
                continue
            except Event.MultipleObjectsReturned:
                event = Event.objects.filter(
                    name__iexact=scraped_data.event_title,
                    wikipedia_url=scraped_data.event_url
                ).first()
            
            # Update status to 'processing'
            with transaction.atomic():
                event.processing_status = 'processing'
                event.processing_attempts += 1
                event.last_processed_at = timezone.now()
                event.save()
            
            self.stdout.write(
                f"Processing event {i}/{total_events}: {event.name} (attempt {event.processing_attempts})"
            )
            
            try:
                # Process the event
                ufc_event = processor.process_scraped_event(scraped_data)
                
                if ufc_event:
                    processed_events.append(ufc_event)
                    
                    # Update status to 'completed'
                    with transaction.atomic():
                        event.processing_status = 'completed'
                        event.last_processing_error = ''
                        event.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Successfully processed: {event.name}")
                    )
                else:
                    # Processing failed
                    error_msg = "Gemini processing returned None"
                    
                    with transaction.atomic():
                        event.processing_status = 'failed'
                        event.last_processing_error = error_msg
                        event.save()
                    
                    self.stdout.write(
                        self.style.ERROR(f"❌ Processing failed: {event.name} - {error_msg}")
                    )
                    
            except Exception as e:
                # Processing failed with exception
                error_msg = str(e)
                
                with transaction.atomic():
                    event.processing_status = 'failed'
                    event.last_processing_error = error_msg
                    event.save()
                
                self.stdout.write(
                    self.style.ERROR(f"❌ Processing failed: {event.name} - {error_msg}")
                )
                logger.error(f"Error processing {event.name}: {e}")
            
            # Add small delay between events to be respectful
            if i < total_events:
                import time
                time.sleep(1.0)
        
        return processed_events
    
    def _save_html_files(self, scraped_results, html_dir: str):
        """Save raw HTML files for debugging"""
        try:
            os.makedirs(html_dir, exist_ok=True)
            
            for result in scraped_results:
                if result.extraction_success:
                    filename = f"{result.event_title.replace(' ', '_')}.html"
                    filepath = os.path.join(html_dir, filename)
                    
                    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{result.event_title}</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>{result.event_title}</h1>
    <p><strong>URL:</strong> {result.event_url}</p>
    <p><strong>Scraped:</strong> {result.scraping_timestamp}</p>
    
    <h2>First Paragraph</h2>
    {result.first_paragraph_html or 'Not found'}
    
    <h2>Infobox</h2>
    {result.infobox_html or 'Not found'}
    
    <h2>Results Table</h2>
    {result.results_table_html or 'Not found'}
    
    <h2>Bonus Awards</h2>
    {result.bonus_awards_html or 'Not found'}
</body>
</html>
                    """
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
            
            self.stdout.write(f"Saved HTML files to {html_dir}")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not save HTML files: {e}")
            )
    
    def _save_json_output(self, processed_events: List[UFCEventSchema], output_file: str):
        """Save processed JSON data to file"""
        try:
            json_data = [event.model_dump() for event in processed_events]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str)
            
            self.stdout.write(f"Saved JSON data to {output_file}")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not save JSON file: {e}")
            )
    
    def _display_results(self, import_result, options):
        """Display import results"""
        
        stats = import_result['overall_statistics']
        
        # Event statistics
        self.stdout.write('\nEVENT IMPORT RESULTS:')
        self.stdout.write(f"  Events created: {stats['events_created']}")
        self.stdout.write(f"  Events updated: {stats['events_updated']}")
        self.stdout.write(f"  Events skipped: {stats['events_skipped']}")
        self.stdout.write(f"  Fights created: {stats['fights_created']}")
        self.stdout.write(f"  Participants created: {stats['participants_created']}")
        
        # Fighter statistics
        if 'fighter_stats' in stats:
            fighter_stats = stats['fighter_stats']
            self.stdout.write('\nFIGHTER PROCESSING RESULTS:')
            self.stdout.write(f"  Fighters created: {fighter_stats['fighters_created']}")
            self.stdout.write(f"  Fighters matched: {fighter_stats['fighters_matched']}")
            self.stdout.write(f"  Fighters updated: {fighter_stats['fighters_updated']}")
            self.stdout.write(f"  Low confidence matches: {fighter_stats['low_confidence_matches']}")
            self.stdout.write(f"  Duplicate URLs found: {fighter_stats['duplicate_urls_found']}")
        
        # Errors
        if import_result['errors']:
            self.stdout.write('\nERRORS:')
            for error in import_result['errors'][:10]:  # Show first 10 errors
                self.stdout.write(f"  • {error}")
            
            if len(import_result['errors']) > 10:
                self.stdout.write(f"  ... and {len(import_result['errors']) - 10} more errors")
        
        # Dry run notice
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('\nDRY RUN: No data was actually saved to the database')
            )
    
    def _display_final_summary(self, total_urls, scraped_count, processed_count, import_result):
        """Display final summary"""
        
        success_rate = import_result['successful_imports'] / import_result['total_events'] * 100
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SCRAPING COMPLETED'))
        self.stdout.write('='*60)
        self.stdout.write(f"Total events found: {total_urls}")
        self.stdout.write(f"Successfully scraped: {scraped_count}")
        self.stdout.write(f"Processed by Gemini: {processed_count}")
        self.stdout.write(f"Imported to database: {import_result['successful_imports']}")
        self.stdout.write(f"Overall success rate: {success_rate:.1f}%")
        
        if import_result['failed_imports'] > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed imports: {import_result['failed_imports']}")
            )
        
        self.stdout.write('='*60)