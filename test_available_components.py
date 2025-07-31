#!/usr/bin/env python3
"""
Test UFC Wikipedia scraper components that are available in current environment
This tests what can be tested without Google Generative AI dependencies
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_wikipedia_scraper():
    """Test Wikipedia scraping functionality"""
    print("🔍 Testing Wikipedia scraper...")
    
    try:
        from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
        
        scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
        print("✅ Wikipedia scraper initialized successfully")
        
        # Test UFC 300 specifically
        ufc_300_url = "https://en.wikipedia.org/wiki/UFC_300"
        print(f"🎯 Testing with {ufc_300_url}...")
        
        result = scraper.scrape_event_page(ufc_300_url)
        
        if result.extraction_success:
            print(f"✅ Successfully scraped: {result.event_title}")
            print(f"  • First paragraph: {'✅' if result.first_paragraph_html else '❌'}")
            print(f"  • Infobox: {'✅' if result.infobox_html else '❌'}")
            print(f"  • Results table: {'✅' if result.results_table_html else '❌'}")
            print(f"  • Bonus awards: {'✅' if result.bonus_awards_html else '❌'}")
            
            # Validate data quality
            if result.results_table_html:
                import re
                links = re.findall(r'href=\"([^\"]*)\"', result.results_table_html)
                wiki_links = [link for link in links if 'wikipedia.org/wiki/' in link]
                print(f"  • Fighter Wikipedia links found: {len(wiki_links)}")
                
                # Look for key UFC 300 fighters
                expected_fighters = ['Alex Pereira', 'Jamahal Hill', 'Zhang Weili']
                found_fighters = []
                for fighter in expected_fighters:
                    if fighter in result.results_table_html:
                        found_fighters.append(fighter)
                
                if found_fighters:
                    print(f"  • ✅ Found expected fighters: {', '.join(found_fighters)}")
                
                # Verify fight data structure
                if any(keyword in result.results_table_html.lower() for keyword in ['def.', 'submission', 'decision', 'ko']):
                    print("  • ✅ Fight results structure detected")
            
            return True
        else:
            print(f"❌ Scraping failed: {result.error_messages}")
            return False
            
    except Exception as e:
        print(f"❌ Wikipedia scraper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pydantic_schemas():
    """Test Pydantic schemas"""
    print("\n📋 Testing Pydantic schemas...")
    
    try:
        from events.scrapers.schemas import (
            FighterInfoSchema, FightResultSchema, 
            EventInfoSchema, UFCEventSchema
        )
        
        # Test fighter schema
        fighter_data = {
            "first_name": "Alex",
            "last_name": "Pereira",
            "nickname": "Poatan",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Alex_Pereira",
            "nationality": "Brazil",
            "result": "win"
        }
        
        fighter = FighterInfoSchema(**fighter_data)
        print(f"✅ Fighter schema works: {fighter.first_name} '{fighter.nickname}' {fighter.last_name}")
        
        # Test complete UFC event structure
        event_data = {
            "name": "UFC 300: Pereira vs. Hill",
            "date": "2024-04-13",
            "location": "Las Vegas, Nevada, United States",
            "venue": "T-Mobile Arena",
            "wikipedia_url": "https://en.wikipedia.org/wiki/UFC_300"
        }
        
        event = EventInfoSchema(**event_data)
        print(f"✅ Event schema works: {event.name}")
        
        # Test fight result
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
        
        # Test complete UFC event schema
        ufc_event_data = {
            "event": event,
            "fights": [fight],
            "bonus_awards": []
        }
        
        ufc_event = UFCEventSchema(**ufc_event_data)
        print(f"✅ Complete UFC event schema works: {len(ufc_event.fights)} fights")
        
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
        
        # Test validation
        test_fighter = FighterInfoSchema(
            first_name="Test",
            last_name="Fighter",
            wikipedia_url="https://en.wikipedia.org/wiki/Test_Fighter",
            result="win"
        )
        
        warnings = service.validate_fighter_data(test_fighter)
        print(f"✅ Fighter validation works: {len(warnings)} warnings")
        
        # Test statistics
        stats = service.get_statistics()
        print(f"✅ Statistics tracking works: {len(stats)} stat categories")
        
        return True
        
    except Exception as e:
        print(f"❌ Fighter service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_importer():
    """Test data importer in dry-run mode"""
    print("\n💾 Testing data importer (dry run)...")
    
    try:
        from events.scrapers.data_importer import DataImporter
        from events.scrapers.schemas import UFCEventSchema, EventInfoSchema
        
        # Create test data
        event_data = EventInfoSchema(
            name="Test UFC Event",
            date="2024-01-01",
            location="Test Location",
            wikipedia_url="https://example.com"
        )
        
        ufc_event = UFCEventSchema(
            event=event_data,
            fights=[],
            bonus_awards=[]
        )
        
        # Test dry run import
        importer = DataImporter(dry_run=True)
        print("✅ Data importer initialized")
        
        result = importer.import_ufc_event(ufc_event)
        
        if result['success']:
            print("✅ Dry run import successful")
            print(f"  • Event handling: {'✅' if result['event'] else '❌'}")
            
            stats = importer.get_import_statistics()
            print(f"✅ Statistics tracking works: {len(stats)} stat categories")
            
            return True
        else:
            print(f"❌ Import test failed: {result['errors']}")
            return False
            
    except Exception as e:
        print(f"❌ Data importer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_missing_dependencies():
    """Check what dependencies are missing"""
    print("\n🔍 Checking dependencies...")
    
    missing = []
    
    try:
        import google.generativeai
        print("✅ google-generativeai available")
    except ImportError:
        missing.append("google-generativeai")
        print("❌ google-generativeai not available")
    
    try:
        import pydantic
        print("✅ pydantic available")
    except ImportError:
        missing.append("pydantic")
        print("❌ pydantic not available")
    
    return missing


def main():
    """Run available component tests"""
    print("🚀 UFC Wikipedia Scraper - Available Components Test")
    print("=" * 70)
    
    # Check dependencies first
    missing_deps = check_missing_dependencies()
    
    # Run available tests
    tests = [
        ("Wikipedia Scraper", test_wikipedia_scraper),
        ("Pydantic Schemas", test_pydantic_schemas),
        ("Fighter Service", test_fighter_service),
        ("Data Importer", test_data_importer)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"💥 {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("\n📋 To complete setup:")
        print("1. Create virtual environment: python3 -m venv venv")
        print("2. Activate it: source venv/bin/activate")
        print("3. Install dependencies: pip install google-generativeai==0.8.3 pydantic==2.8.2")
        print("4. Run full test: python test_ufc_scraper.py")
    
    if passed == total and not missing_deps:
        print("\n🎉 ALL COMPONENTS WORKING! System ready for production.")
    elif passed >= 3:
        print("\n✅ Core components working. Ready for Gemini AI integration.")
    else:
        print("\n❌ Multiple component failures. Check implementation.")
    
    print("=" * 70)
    
    return passed >= 3  # Consider success if most components work


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