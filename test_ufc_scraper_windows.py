#!/usr/bin/env python3
"""
Test script for UFC Wikipedia scraper with Gemini AI (Windows compatible)
Run this to validate the implementation before full deployment
"""
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
django.setup()

import logging
from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
from events.scrapers.gemini_processor import GeminiProcessor
from events.scrapers.data_importer import DataImporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_wikipedia_scraper():
    """Test Wikipedia scraping functionality"""
    print("Testing Wikipedia scraper...")
    
    scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
    
    # Test getting event URLs
    print("Getting sample UFC event URLs...")
    event_urls = scraper.get_ufc_event_urls(limit=2)
    
    if not event_urls:
        print("ERROR: No event URLs found")
        return False
    
    print(f"SUCCESS: Found {len(event_urls)} event URLs:")
    for name, url in event_urls:
        print(f"  - {name}: {url}")
    
    # Test scraping one event
    print("\nTesting event page scraping...")
    _, test_url = event_urls[0]
    
    scraped_result = scraper.scrape_event_page(test_url)
    
    if scraped_result.extraction_success:
        print(f"SUCCESS: Successfully scraped: {scraped_result.event_title}")
        print(f"  - First paragraph: {'YES' if scraped_result.first_paragraph_html else 'NO'}")
        print(f"  - Infobox: {'YES' if scraped_result.infobox_html else 'NO'}")
        print(f"  - Results table: {'YES' if scraped_result.results_table_html else 'NO'}")
        print(f"  - Bonus awards: {'YES' if scraped_result.bonus_awards_html else 'NO'}")
        
        # Count fighter links
        if scraped_result.results_table_html:
            import re
            links = re.findall(r'href=\"([^\"]*)\"', scraped_result.results_table_html)
            wiki_links = [link for link in links if 'wikipedia.org/wiki/' in link]
            print(f"  - Fighter Wikipedia links: {len(wiki_links)}")
        
        return scraped_result
    else:
        print(f"ERROR: Scraping failed: {scraped_result.error_messages}")
        return False


def test_gemini_processor(scraped_result):
    """Test Gemini AI processing"""
    print("\nTesting Gemini AI processor...")
    
    # Use the provided API key
    api_key = "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
    
    try:
        processor = GeminiProcessor(api_key)
        print("SUCCESS: Gemini processor initialized")
        
        # Process the scraped event
        print(f"Processing {scraped_result.event_title} with Gemini...")
        ufc_event = processor.process_scraped_event(scraped_result)
        
        if ufc_event:
            print(f"SUCCESS: Successfully processed event: {ufc_event.event.name}")
            print(f"  - Date: {ufc_event.event.date}")
            print(f"  - Location: {ufc_event.event.location}")
            print(f"  - Fights extracted: {len(ufc_event.fights)}")
            
            # Show sample fight data
            if ufc_event.fights:
                fight = ufc_event.fights[0]
                print(f"  - Sample fight: {fight.fighter1.first_name} {fight.fighter1.last_name} vs {fight.fighter2.first_name} {fight.fighter2.last_name}")
                print(f"    * Fighter 1 Wikipedia: {fight.fighter1.wikipedia_url or 'Not found'}")
                print(f"    * Fighter 2 Wikipedia: {fight.fighter2.wikipedia_url or 'Not found'}")
            
            return ufc_event
        else:
            print("ERROR: Gemini processing failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Gemini processing error: {e}")
        return False


def test_data_importer(ufc_event):
    """Test data import functionality (dry run)"""
    print("\nTesting data importer (dry run)...")
    
    try:
        importer = DataImporter(dry_run=True, update_existing=True)
        print("SUCCESS: Data importer initialized")
        
        # Import the processed event
        print(f"Importing {ufc_event.event.name} (dry run)...")
        import_result = importer.import_ufc_event(ufc_event)
        
        if import_result['success']:
            print("SUCCESS: Dry run import successful!")
            print(f"  - Event: {import_result['event'].name}")
            print(f"  - Fights: {len(import_result['fights'])}")
            print(f"  - Errors: {len(import_result['errors'])}")
            
            # Show statistics
            stats = importer.get_import_statistics()
            print(f"  - Fighter stats: {stats['fighter_stats']['fighters_created']} created, {stats['fighter_stats']['fighters_matched']} matched")
            
            return True
        else:
            print(f"ERROR: Import failed: {import_result['errors']}")
            return False
            
    except Exception as e:
        print(f"ERROR: Import error: {e}")
        return False


def main():
    """Run complete test suite"""
    print("Starting UFC Wikipedia Scraper Test Suite")
    print("=" * 60)
    
    # Test 1: Wikipedia scraping
    scraped_result = test_wikipedia_scraper()
    if not scraped_result:
        print("\nERROR: Wikipedia scraping test failed. Stopping.")
        return False
    
    # Test 2: Gemini processing
    ufc_event = test_gemini_processor(scraped_result)
    if not ufc_event:
        print("\nERROR: Gemini processing test failed. Stopping.")
        return False
    
    # Test 3: Data import (dry run)
    import_success = test_data_importer(ufc_event)
    if not import_success:
        print("\nERROR: Data import test failed. Stopping.")
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("SUCCESS: ALL TESTS PASSED!")
    print("The UFC Wikipedia scraper is ready for production use.")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run migrations: python manage.py migrate")
    print("3. Test with real data: python manage.py scrape_ufc_wikipedia_gemini --events 2 --dry-run")
    print("4. Full import: python manage.py scrape_ufc_wikipedia_gemini --events 10")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)