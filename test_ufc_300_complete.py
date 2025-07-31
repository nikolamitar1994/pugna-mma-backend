#!/usr/bin/env python3
"""
Test script for UFC Wikipedia scraper with UFC 300 specifically (Windows compatible)
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


def test_ufc_300_complete():
    """Test complete pipeline with UFC 300"""
    print("Testing UFC 300 Complete Pipeline")
    print("=" * 50)
    
    # Step 1: Test Wikipedia scraping with UFC 300
    print("STEP 1: Testing Wikipedia scraping with UFC 300...")
    scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
    
    ufc_300_url = "https://en.wikipedia.org/wiki/UFC_300"
    scraped_result = scraper.scrape_event_page(ufc_300_url)
    
    if not scraped_result.extraction_success:
        print(f"ERROR: Failed to scrape UFC 300: {scraped_result.error_messages}")
        return False
    
    print(f"SUCCESS: Scraped {scraped_result.event_title}")
    print(f"  - First paragraph: {'YES' if scraped_result.first_paragraph_html else 'NO'}")
    print(f"  - Infobox: {'YES' if scraped_result.infobox_html else 'NO'}")
    print(f"  - Results table: {'YES' if scraped_result.results_table_html else 'NO'}")
    print(f"  - Bonus awards: {'YES' if scraped_result.bonus_awards_html else 'NO'}")
    
    # Validate data quality
    if scraped_result.results_table_html:
        import re
        links = re.findall(r'href=\"([^\"]*)\"', scraped_result.results_table_html)
        wiki_links = [link for link in links if 'wikipedia.org/wiki/' in link]
        print(f"  - Fighter Wikipedia links: {len(wiki_links)}")
        
        # Check for key UFC 300 fighters
        expected_fighters = ['Alex Pereira', 'Jamahal Hill', 'Zhang Weili']
        found_fighters = []
        for fighter in expected_fighters:
            if fighter in scraped_result.results_table_html:
                found_fighters.append(fighter)
        
        if found_fighters:
            print(f"  - Found expected fighters: {', '.join(found_fighters)}")
    
    # Step 2: Test Gemini AI processing
    print("\nSTEP 2: Testing Gemini AI processing...")
    api_key = "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
    
    try:
        processor = GeminiProcessor(api_key)
        print("SUCCESS: Gemini processor initialized")
        
        print(f"Processing {scraped_result.event_title} with Gemini AI...")
        ufc_event = processor.process_scraped_event(scraped_result)
        
        if not ufc_event:
            print("ERROR: Gemini processing failed")
            return False
        
        print(f"SUCCESS: Gemini processed the event")
        print(f"  - Event name: {ufc_event.event.name}")
        print(f"  - Date: {ufc_event.event.date}")
        print(f"  - Location: {ufc_event.event.location}")
        print(f"  - Fights extracted: {len(ufc_event.fights)}")
        print(f"  - Bonus awards: {len(ufc_event.bonus_awards)}")
        
        # Show some sample fight data
        if ufc_event.fights:
            print(f"  - Sample fights:")
            for i, fight in enumerate(ufc_event.fights[:3]):  # Show first 3 fights
                f1 = fight.fighter1
                f2 = fight.fighter2
                print(f"    {i+1}. {f1.first_name} {f1.last_name} vs {f2.first_name} {f2.last_name}")
                if f1.wikipedia_url:
                    print(f"       - {f1.first_name} Wikipedia: {f1.wikipedia_url}")
                if f2.wikipedia_url:
                    print(f"       - {f2.first_name} Wikipedia: {f2.wikipedia_url}")
        
    except Exception as e:
        print(f"ERROR: Gemini processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Test database import (dry run)
    print("\nSTEP 3: Testing database import (dry run)...")
    try:
        importer = DataImporter(dry_run=True, update_existing=True)
        print("SUCCESS: Data importer initialized")
        
        print(f"Importing {ufc_event.event.name} (dry run)...")
        import_result = importer.import_ufc_event(ufc_event)
        
        if not import_result['success']:
            print(f"ERROR: Import failed: {import_result['errors']}")
            return False
        
        print("SUCCESS: Dry run import completed!")
        print(f"  - Event created: {import_result['event'].name}")
        print(f"  - Fights processed: {len(import_result['fights'])}")
        print(f"  - Import errors: {len(import_result['errors'])}")
        
        # Show statistics
        stats = importer.get_import_statistics()
        fighter_stats = stats['fighter_stats']
        print(f"  - Fighter statistics:")
        print(f"    * Created: {fighter_stats['fighters_created']}")
        print(f"    * Matched: {fighter_stats['fighters_matched']}")
        print(f"    * Updated: {fighter_stats['fighters_updated']}")
        
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Success summary
    print("\n" + "=" * 50)
    print("SUCCESS: COMPLETE PIPELINE WORKING!")
    print("=" * 50)
    print("UFC 300 was successfully:")
    print("1. Scraped from Wikipedia")
    print("2. Processed with Gemini AI")
    print("3. Imported to database (dry run)")
    print("\nThe system is ready for production use!")
    print("=" * 50)
    
    return True


def main():
    """Main test function"""
    try:
        success = test_ufc_300_complete()
        
        if success:
            print("\nNEXT STEPS:")
            print("1. Run with real data: python manage.py scrape_ufc_wikipedia_gemini --events 5 --dry-run")
            print("2. Production import: python manage.py scrape_ufc_wikipedia_gemini --events 10")
            print("3. Specific event: python manage.py scrape_ufc_wikipedia_gemini --event-urls https://en.wikipedia.org/wiki/UFC_300")
        
        return success
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)