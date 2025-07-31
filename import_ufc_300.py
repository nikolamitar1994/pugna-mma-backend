#!/usr/bin/env python3
"""
Simple script to import UFC 300 to database (Windows compatible)
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


def import_ufc_300():
    """Import UFC 300 to database"""
    print("Importing UFC 300 to database...")
    print("=" * 50)
    
    try:
        # Step 1: Scrape Wikipedia
        print("STEP 1: Scraping UFC 300 from Wikipedia...")
        scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
        scraped_result = scraper.scrape_event_page("https://en.wikipedia.org/wiki/UFC_300")
        
        if not scraped_result.extraction_success:
            print(f"ERROR: Failed to scrape UFC 300: {scraped_result.error_messages}")
            return False
        
        print(f"SUCCESS: Scraped {scraped_result.event_title}")
        
        # Step 2: Process with Gemini AI
        print("\nSTEP 2: Processing with Gemini AI...")
        api_key = "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
        processor = GeminiProcessor(api_key)
        
        ufc_event = processor.process_scraped_event(scraped_result)
        if not ufc_event:
            print("ERROR: Gemini processing failed")
            return False
        
        print(f"SUCCESS: Processed {ufc_event.event.name}")
        print(f"  - Fights: {len(ufc_event.fights)}")
        
        # Step 3: Import to database (REAL IMPORT - NO DRY RUN)
        print(f"\nSTEP 3: Importing {ufc_event.event.name} to database...")
        print("WARNING: This will save real data to your database!")
        
        importer = DataImporter(dry_run=False, update_existing=True)  # dry_run=False!
        import_result = importer.import_ufc_event(ufc_event)
        
        if import_result['success']:
            print("SUCCESS: UFC 300 imported to database!")
            print(f"  - Event: {import_result['event'].name}")
            print(f"  - Event ID: {import_result['event'].id}")
            print(f"  - Fights processed: {len(import_result['fights'])}")
            
            # Show fighter statistics
            stats = importer.get_import_statistics()
            fighter_stats = stats['fighter_stats']
            print(f"  - Fighter statistics:")
            print(f"    * Created: {fighter_stats['fighters_created']}")
            print(f"    * Matched: {fighter_stats['fighters_matched']}")
            print(f"    * Updated: {fighter_stats['fighters_updated']}")
            
            if import_result['errors']:
                print(f"  - Import errors: {len(import_result['errors'])}")
                for error in import_result['errors'][:5]:  # Show first 5 errors
                    print(f"    * {error}")
            
            print(f"\nSUCCESS: UFC 300 should now be visible in Django admin!")
            print(f"Event ID: {import_result['event'].id}")
            return True
        else:
            print(f"ERROR: Import failed: {import_result['errors']}")
            return False
            
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("UFC 300 Database Import")
    print("This will import UFC 300 data to your database")
    print("=" * 50)
    
    success = import_ufc_300()
    
    if success:
        print("\n" + "=" * 50)
        print("SUCCESS: UFC 300 imported successfully!")
        print("Check your Django admin panel - the event should be there now.")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED: UFC 300 import failed. Check errors above.")
        print("=" * 50)
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nImport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)