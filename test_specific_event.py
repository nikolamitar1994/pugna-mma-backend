#!/usr/bin/env python3
"""
Test UFC Wikipedia scraper with specific event (UFC 300)
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


def test_ufc_300():
    """Test scraping UFC 300 specifically"""
    print("🎯 Testing UFC 300 Wikipedia scraping...")
    
    try:
        scraper = WikipediaGeminiScraper(rate_limit_delay=0.5)
        
        # Test UFC 300 specifically
        ufc_300_url = "https://en.wikipedia.org/wiki/UFC_300"
        print(f"🔍 Scraping {ufc_300_url}...")
        
        result = scraper.scrape_event_page(ufc_300_url)
        
        if result.extraction_success:
            print(f"✅ Successfully scraped: {result.event_title}")
            print(f"  • URL: {result.event_url}")
            print(f"  • First paragraph: {'✅' if result.first_paragraph_html else '❌'}")
            print(f"  • Infobox: {'✅' if result.infobox_html else '❌'}")
            print(f"  • Results table: {'✅' if result.results_table_html else '❌'}")
            print(f"  • Bonus awards: {'✅' if result.bonus_awards_html else '❌'}")
            
            # Show details about extracted data
            if result.first_paragraph_html:
                print(f"  • First paragraph length: {len(result.first_paragraph_html)} characters")
            
            if result.infobox_html:
                print(f"  • Infobox length: {len(result.infobox_html)} characters")
                # Look for key data
                if "April 13, 2024" in result.infobox_html:
                    print("  • ✅ Date found in infobox")
                if "T-Mobile Arena" in result.infobox_html:
                    print("  • ✅ Venue found in infobox")
            
            if result.results_table_html:
                print(f"  • Results table length: {len(result.results_table_html)} characters")
                
                # Look for fighter links
                import re
                links = re.findall(r'href=\"([^\"]*)\"', result.results_table_html)
                wiki_links = [link for link in links if 'wikipedia.org/wiki/' in link]
                print(f"  • Fighter Wikipedia links found: {len(wiki_links)}")
                
                # Look for specific fighters we know were on UFC 300
                known_fighters = ['Alex Pereira', 'Jamahal Hill', 'Zhang Weili', 'Yan Xiaonan']
                found_fighters = []
                for fighter in known_fighters:
                    if fighter in result.results_table_html:
                        found_fighters.append(fighter)
                
                if found_fighters:
                    print(f"  • ✅ Found known fighters: {', '.join(found_fighters)}")
                else:
                    print("  • ⚠️ No known fighters found in results table")
                
                # Look for fight results structure
                if 'def.' in result.results_table_html or 'defeated' in result.results_table_html:
                    print("  • ✅ Fight results structure found")
                else:
                    print("  • ⚠️ Fight results structure not clearly found")
            
            if result.bonus_awards_html:
                print(f"  • Bonus awards length: {len(result.bonus_awards_html)} characters")
                if '$300,000' in result.bonus_awards_html:
                    print("  • ✅ UFC 300 bonus amounts found")
            
            return True
        else:
            print(f"❌ Scraping failed: {result.error_messages}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing UFC 300: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("🚀 UFC 300 Specific Test")
    print("=" * 50)
    
    success = test_ufc_300()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 UFC 300 test PASSED! Core scraping is working.")
        print("\n📋 Next steps:")
        print("1. Test with Gemini AI processing")
        print("2. Run full Django management command")
    else:
        print("❌ UFC 300 test FAILED. Check scraper implementation.")
    
    print("=" * 50)
    
    return success


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