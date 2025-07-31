#!/usr/bin/env python3
"""
Basic test for UFC Wikipedia scraper components
Tests without Gemini AI to validate core functionality
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_scraping():
    """Test basic Wikipedia scraping without Gemini"""
    print("🔍 Testing basic Wikipedia scraper...")
    
    try:
        scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
        print("✅ Scraper initialized successfully")
        
        # Test getting event URLs
        print("📋 Getting sample UFC event URLs...")
        event_urls = scraper.get_ufc_event_urls(limit=2)
        
        if not event_urls:
            print("❌ No event URLs found")
            return False
        
        print(f"✅ Found {len(event_urls)} event URLs:")
        for name, url in event_urls:
            print(f"  • {name}: {url}")
        
        # Test scraping one event
        print("\n🔍 Testing event page scraping...")
        _, test_url = event_urls[0]
        
        scraped_result = scraper.scrape_event_page(test_url)
        
        if scraped_result.extraction_success:
            print(f"✅ Successfully scraped: {scraped_result.event_title}")
            print(f"  • URL: {scraped_result.event_url}")
            print(f"  • First paragraph: {'✅' if scraped_result.first_paragraph_html else '❌'}")
            print(f"  • Infobox: {'✅' if scraped_result.infobox_html else '❌'}")
            print(f"  • Results table: {'✅' if scraped_result.results_table_html else '❌'}")
            print(f"  • Bonus awards: {'✅' if scraped_result.bonus_awards_html else '❌'}")
            
            # Show sample of extracted data
            if scraped_result.results_table_html:
                print(f"  • Results table length: {len(scraped_result.results_table_html)} characters")
                # Look for fighter links
                import re
                links = re.findall(r'href="([^"]*)"', scraped_result.results_table_html)
                wiki_links = [link for link in links if 'wikipedia.org/wiki/' in link]
                print(f"  • Fighter Wikipedia links found: {len(wiki_links)}")
                if wiki_links:
                    print(f"    Sample links: {wiki_links[:3]}")
            
            return True
        else:
            print(f"❌ Scraping failed: {scraped_result.error_messages}")
            return False
            
    except Exception as e:
        print(f"❌ Error in basic scraping test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas():
    """Test Pydantic schemas without Gemini"""
    print("\n📋 Testing Pydantic schemas...")
    
    try:
        from events.scrapers.schemas import (
            FighterInfoSchema, FightResultSchema, 
            EventInfoSchema, UFCEventSchema
        )
        
        # Test fighter schema
        fighter_data = {
            "first_name": "Jon",
            "last_name": "Jones",
            "nickname": "Bones",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Jon_Jones",
            "nationality": "United States",
            "result": "win"
        }
        
        fighter = FighterInfoSchema(**fighter_data)
        print(f"✅ Fighter schema works: {fighter.first_name} {fighter.last_name}")
        
        # Test event schema
        event_data = {
            "name": "UFC 300",
            "date": "2024-04-13",
            "location": "T-Mobile Arena, Las Vegas, Nevada",
            "wikipedia_url": "https://en.wikipedia.org/wiki/UFC_300"
        }
        
        event = EventInfoSchema(**event_data)
        print(f"✅ Event schema works: {event.name}")
        
        # Test fight schema
        fight_data = {
            "fight_order": 1,
            "is_main_event": True,
            "weight_class": "Light Heavyweight",
            "fighter1": fighter,
            "fighter2": FighterInfoSchema(
                first_name="Jamahal", last_name="Hill",
                result="loss"
            )
        }
        
        fight = FightResultSchema(**fight_data)
        print(f"✅ Fight schema works: {fight.fighter1.first_name} vs {fight.fighter2.first_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fighter_service():
    """Test fighter service functionality"""
    print("\n🥊 Testing fighter service...")
    
    try:
        from events.scrapers.fighter_service import FighterService
        from events.scrapers.schemas import FighterInfoSchema
        
        service = FighterService()
        print("✅ Fighter service initialized")
        
        # Test with a sample fighter
        sample_fighter = FighterInfoSchema(
            first_name="Test",
            last_name="Fighter", 
            wikipedia_url="https://en.wikipedia.org/wiki/Test_Fighter",
            result="win"
        )
        
        # Validate fighter data
        warnings = service.validate_fighter_data(sample_fighter)
        print(f"✅ Fighter validation works: {len(warnings)} warnings")
        
        print("✅ Fighter service basic functionality confirmed")
        return True
        
    except Exception as e:
        print(f"❌ Fighter service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run basic test suite"""
    print("🚀 Starting UFC Wikipedia Scraper Basic Test Suite")
    print("=" * 60)
    
    # Test 1: Basic Wikipedia scraping
    scraping_success = test_basic_scraping()
    if not scraping_success:
        print("\n❌ Basic scraping test failed.")
    
    # Test 2: Schema validation
    schema_success = test_schemas()
    if not schema_success:
        print("\n❌ Schema test failed.")
    
    # Test 3: Fighter service
    fighter_success = test_fighter_service()
    if not fighter_success:
        print("\n❌ Fighter service test failed.")
    
    # Results
    print("\n" + "=" * 60)
    if scraping_success and schema_success and fighter_success:
        print("🎉 BASIC TESTS PASSED!")
        print("Core functionality is working correctly.")
        print("\n📋 Next steps:")
        print("1. Install Google Generative AI: pip install google-generativeai")
        print("2. Run full test: python test_ufc_scraper.py")
        print("3. Test Django command: python manage.py scrape_ufc_wikipedia_gemini --help")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    print("=" * 60)
    
    return scraping_success and schema_success and fighter_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)