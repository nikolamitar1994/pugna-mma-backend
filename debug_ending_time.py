#!/usr/bin/env python3
"""
Debug script to examine what ending_time values Gemini is extracting from UFC 1
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
django.setup()

from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
from events.scrapers.gemini_processor import GeminiProcessor
import json

def debug_ufc_1():
    """Debug UFC 1 data extraction"""
    print("=== DEBUG: UFC 1 Ending Time Extraction ===")
    
    # Initialize scrapers
    scraper = WikipediaGeminiScraper()
    
    # Use environment variable for API key, or fallback to hardcoded key
    api_key = os.getenv('GEMINI_API_KEY') or "AIzaSyCT4G_BMOgIB-Ll3dzo4Xmk2ZFlq3ODEcM"
    if not api_key:
        print("ERROR: No API key available")
        return
    
    processor = GeminiProcessor(api_key=api_key)
    
    # Scrape UFC 1
    url = "https://en.wikipedia.org/wiki/UFC_1"
    print(f"Scraping: {url}")
    
    raw_data = scraper.scrape_event_page(url)
    if not raw_data or not raw_data.extraction_success:
        print("ERROR: Failed to scrape UFC 1")
        return
    
    print("SUCCESS: Successfully scraped raw data")
    
    # Process with Gemini
    result = processor.process_scraped_event(raw_data)
    if not result:
        print("ERROR: Failed to process with Gemini")
        return
    
    print("SUCCESS: Successfully processed with Gemini")
    print(f"Found {len(result.fights)} fights")
    print()
    
    # Debug each fight's ending_time
    for i, fight in enumerate(result.fights, 1):
        print(f"Fight {i}: {fight.fighter1.first_name} {fight.fighter1.last_name} vs {fight.fighter2.first_name} {fight.fighter2.last_name}")
        print(f"  ending_time: '{fight.ending_time}'")
        print(f"  ending_round: {fight.ending_round}")
        print(f"  method: '{fight.method}'")
        print(f"  method_details: '{fight.method_details}'")
        print(f"  fight_section: '{fight.fight_section}'")
        print()

if __name__ == "__main__":
    debug_ufc_1()