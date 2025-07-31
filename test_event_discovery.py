#!/usr/bin/env python3
"""
Test script to analyze UFC event discovery from Wikipedia
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/351f0834473bf4d2e391b5acf0ea9c949254dbec9244c1e72e733cbf7c7b0651')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings')
django.setup()

from events.scrapers.wikipedia_gemini_scraper import WikipediaGeminiScraper
import requests
from bs4 import BeautifulSoup

def analyze_ufc_events_page():
    """Analyze the UFC events list page to understand structure"""
    
    print("🔍 Analyzing UFC Events List Page")
    print("=" * 50)
    
    url = "https://en.wikipedia.org/wiki/List_of_UFC_events"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Successfully fetched page ({len(response.content)} bytes)")
        print()
        
        # Find all tables
        tables = soup.find_all('table', class_='wikitable')
        print(f"📊 Found {len(tables)} wikitable tables")
        
        total_events = 0
        event_types = {}
        
        for i, table in enumerate(tables):
            print(f"\n--- Table {i+1} ---")
            
            # Get table caption/headers to identify what type of events
            caption = table.find('caption')
            if caption:
                print(f"Caption: {caption.get_text().strip()}")
            
            # Check nearby headings
            prev_heading = table.find_previous(['h2', 'h3', 'h4'])
            if prev_heading:
                heading_text = prev_heading.get_text().strip()
                print(f"Previous heading: {heading_text}")
            
            # Count rows and look for UFC event links
            rows = table.find_all('tr')[1:]  # Skip header
            ufc_events_in_table = 0
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells[:3]:  # Check first 3 cells
                    link = cell.find('a', href=True)
                    if link and '/wiki/UFC_' in link['href']:
                        event_name = link.get_text().strip()
                        event_url = link['href']
                        
                        # Categorize event type
                        if 'Fight Night' in event_name:
                            event_type = 'Fight Night'
                        elif 'UFC on ESPN' in event_name:
                            event_type = 'UFC on ESPN'
                        elif 'UFC on ABC' in event_name:
                            event_type = 'UFC on ABC'
                        elif event_name.startswith('UFC ') and event_name.split()[1].isdigit():
                            event_type = 'Numbered PPV'
                        else:
                            event_type = 'Other'
                        
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                        ufc_events_in_table += 1
                        total_events += 1
                        
                        if ufc_events_in_table <= 5:  # Show first 5 from each table
                            print(f"  {event_name} -> {event_url}")
                        break
            
            print(f"UFC events found in this table: {ufc_events_in_table}")
        
        print(f"\n🎯 SUMMARY:")
        print(f"Total UFC events found: {total_events}")
        print(f"Event types breakdown:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {event_type}: {count}")
        
        print(f"\n🤖 Current scraper test:")
        scraper = WikipediaGeminiScraper()
        current_results = scraper.get_ufc_event_urls(limit=50)
        print(f"Current scraper finds: {len(current_results)} events")
        
        if current_results:
            print("First 10 events found by current scraper:")
            for i, (name, url) in enumerate(current_results[:10]):
                print(f"  {i+1}. {name}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_ufc_events_page()