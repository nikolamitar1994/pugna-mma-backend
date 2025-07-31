"""
Django management command to test the Wikipedia scraper with specific events
"""
from django.core.management.base import BaseCommand
from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test Wikipedia scraper with specific UFC events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Specific Wikipedia URL to test (e.g., https://en.wikipedia.org/wiki/UFC_300)'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Request timeout in seconds (default: 30)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Rate limit delay in seconds (default: 1.0)'
        )
        parser.add_argument(
            '--test-connectivity',
            action='store_true',
            help='Test Wikipedia connectivity first'
        )
        parser.add_argument(
            '--show-html',
            action='store_true',
            help='Show extracted HTML sections (truncated)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 UFC Wikipedia Scraper Test')
        )
        
        # Create scraper with options
        scraper = WikipediaGeminiScraper(
            rate_limit_delay=options['delay'],
            request_timeout=options['timeout']
        )
        
        # Test connectivity if requested
        if options['test_connectivity']:
            self.stdout.write('\n📡 Testing Wikipedia connectivity...')
            success, message = scraper.test_connectivity()
            if success:
                self.stdout.write(self.style.SUCCESS(message))
            else:
                self.stdout.write(self.style.ERROR(message))
                return
        
        # Show circuit breaker status
        cb_status = scraper.get_circuit_breaker_status()
        self.stdout.write(f'\n🔌 Circuit breaker: {cb_status}')
        
        # Determine URL to test
        if options['url']:
            test_url = options['url']
        else:
            # Default to UFC 300
            test_url = "https://en.wikipedia.org/wiki/UFC_300"
            self.stdout.write(f'\n⚠️  No URL provided, testing with: {test_url}')
        
        # Scrape the event
        self.stdout.write(f'\n📄 Scraping: {test_url}')
        self.stdout.write(f'⏱️  Timeout: {options["timeout"]}s, Rate limit: {options["delay"]}s')
        
        try:
            result = scraper.scrape_event_page(test_url)
            
            # Display results
            if result.extraction_success:
                self.stdout.write(self.style.SUCCESS('\n✅ Scraping SUCCESSFUL'))
            else:
                self.stdout.write(self.style.WARNING('\n⚠️  Scraping PARTIAL/FAILED'))
            
            self.stdout.write(f'📋 Event Title: {result.event_title}')
            self.stdout.write(f'⏰ Timestamp: {result.scraping_timestamp}')
            
            # Show extracted sections
            sections = []
            if result.first_paragraph_html:
                sections.append('first_paragraph')
            if result.infobox_html:
                sections.append('infobox')
            if result.results_table_html:
                sections.append('results_table')
            if result.bonus_awards_html:
                sections.append('bonus_awards')
            
            self.stdout.write(f'📦 Sections extracted: {", ".join(sections) if sections else "None"}')
            
            # Show errors if any
            if result.error_messages:
                self.stdout.write(self.style.ERROR('\n❌ Errors:'))
                for error in result.error_messages:
                    self.stdout.write(self.style.ERROR(f'   • {error}'))
            
            # Show HTML content if requested (truncated)
            if options['show_html']:
                self.stdout.write('\n📝 Extracted HTML (first 500 chars of each section):')
                
                sections_html = [
                    ('First Paragraph', result.first_paragraph_html),
                    ('Infobox', result.infobox_html),
                    ('Results Table', result.results_table_html),
                    ('Bonus Awards', result.bonus_awards_html)
                ]
                
                for section_name, html_content in sections_html:
                    if html_content:
                        truncated = html_content[:500] + '...' if len(html_content) > 500 else html_content
                        self.stdout.write(f'\n--- {section_name} ---')
                        self.stdout.write(truncated)
            
            # Final circuit breaker status
            cb_status_final = scraper.get_circuit_breaker_status()
            self.stdout.write(f'\n🔌 Final circuit breaker: {cb_status_final}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n💥 Scraping failed with exception: {str(e)}')
            )
        
        self.stdout.write(self.style.SUCCESS('\n🏁 Test completed!'))