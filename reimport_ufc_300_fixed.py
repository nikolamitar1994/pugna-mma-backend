#!/usr/bin/env python3
"""
Script to delete and reimport UFC 300 with fixed method formatting and fighter participants
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
django.setup()

import logging
from events.models import Event
from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
from events.scrapers.gemini_processor import GeminiProcessor
from events.scrapers.data_importer import DataImporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def delete_ufc_300():
    """Delete existing UFC 300 data"""
    print("Deleting existing UFC 300 data...")
    
    try:
        # Find UFC 300 event
        ufc_300 = Event.objects.filter(name__icontains="UFC 300").first()
        
        if ufc_300:
            event_name = ufc_300.name
            event_id = ufc_300.id
            
            # Delete will cascade to fights and participants
            ufc_300.delete()
            
            print(f"SUCCESS: Deleted {event_name} (ID: {event_id})")
            return True
        else:
            print("No UFC 300 event found to delete")
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to delete UFC 300: {e}")
        return False


def reimport_ufc_300():
    """Import UFC 300 with fixed formatting"""
    print("\nReimporting UFC 300 with fixes...")
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
        
        # Step 2: Process with Gemini AI (with updated prompts)
        print("\nSTEP 2: Processing with Gemini AI (with fixed method formatting)...")
        api_key = "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
        processor = GeminiProcessor(api_key)
        
        ufc_event = processor.process_scraped_event(scraped_result)
        if not ufc_event:
            print("ERROR: Gemini processing failed")
            return False
        
        print(f"SUCCESS: Processed {ufc_event.event.name}")
        print(f"  - Fights: {len(ufc_event.fights)}")
        
        # Show sample method formatting
        if ufc_event.fights:
            fight = ufc_event.fights[0]
            print(f"  - Sample method formatting:")
            print(f"    * Method: '{fight.method}'")
            print(f"    * Method Details: '{fight.method_details}'")
        
        # Step 3: Import to database with fixes
        print(f"\nSTEP 3: Importing {ufc_event.event.name} with fixed participant creation...")
        
        importer = DataImporter(dry_run=False, update_existing=True)
        import_result = importer.import_ufc_event(ufc_event)
        
        if import_result['success']:
            print("SUCCESS: UFC 300 reimported with fixes!")
            print(f"  - Event: {import_result['event'].name}")
            print(f"  - Event ID: {import_result['event'].id}")
            print(f"  - Fights processed: {len(import_result['fights'])}")
            
            # Show statistics
            stats = importer.get_import_statistics()
            fighter_stats = stats['fighter_stats']
            print(f"  - Fighter statistics:")
            print(f"    * Created: {fighter_stats['fighters_created']}")
            print(f"    * Matched: {fighter_stats['fighters_matched']}")
            print(f"    * Updated: {fighter_stats['fighters_updated']}")
            
            if import_result['errors']:
                print(f"  - Import errors: {len(import_result['errors'])}")
                for error in import_result['errors'][:3]:  # Show first 3 errors
                    print(f"    * {error}")
            else:
                print("  - No import errors!")
            
            return True
        else:
            print(f"ERROR: Import failed: {import_result['errors']}")
            return False
            
    except Exception as e:
        print(f"ERROR: Reimport failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("UFC 300 Fixed Reimport")
    print("This will delete and reimport UFC 300 with:")
    print("- Fixed method formatting (KO vs KO (punches))")
    print("- Fixed fighter participant creation")
    print("- Improved Gemini AI prompts")
    print("=" * 60)
    
    # Step 1: Delete existing data
    if not delete_ufc_300():
        print("Failed to delete existing data. Aborting.")
        return False
    
    # Step 2: Reimport with fixes
    success = reimport_ufc_300()
    
    if success:
        print("\n" + "=" * 60)
        print("SUCCESS: UFC 300 reimported with fixes!")
        print("Check your Django admin panel:")
        print("- Methods should show: 'KO' not 'KO (punches) (punches)'")
        print("- Fighters should show proper names, not 'TBA vs TBA'")
        print("- Method details should be in separate field")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("FAILED: UFC 300 reimport failed. Check errors above.")
        print("=" * 60)
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nReimport interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)