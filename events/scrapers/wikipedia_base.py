"""
Wikipedia Base Scraper - Core MediaWiki API Integration

This module provides the foundation for scraping UFC data from Wikipedia
using the MediaWiki API with proper rate limiting and error handling.
"""

import requests
import time
import logging
from functools import wraps
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import re


logger = logging.getLogger(__name__)


def rate_limit(calls_per_second=1):
    """Decorator to rate limit API calls"""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


class WikipediaUFCScraperBase:
    """Base class for Wikipedia UFC data scraping with MediaWiki API integration"""
    
    def __init__(self, rate_limit_calls_per_second=1):
        self.base_url = "https://en.wikipedia.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MMA-Database-Scraper/1.0 (https://github.com/nikolamitar1994/pugna-mma-backend)'
        })
        self.rate_limit_calls_per_second = rate_limit_calls_per_second
        
        # Statistics tracking
        self.stats = {
            'api_calls': 0,
            'pages_scraped': 0,
            'errors': 0,
            'retries': 0
        }
    
    @rate_limit(calls_per_second=1)
    def _make_api_call(self, params: Dict[str, Any], max_retries: int = 3) -> Optional[Dict]:
        """Make a rate-limited API call with retry logic"""
        for attempt in range(max_retries):
            try:
                self.stats['api_calls'] += 1
                response = self.session.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                if 'error' in data:
                    logger.warning(f"Wikipedia API error: {data['error']}")
                    return None
                
                return data
                
            except requests.exceptions.RequestException as e:
                self.stats['retries'] += 1
                logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    self.stats['errors'] += 1
                    logger.error(f"API call failed after {max_retries} attempts: {str(e)}")
                    return None
                
                # Exponential backoff
                wait_time = 2 ** attempt
                time.sleep(wait_time)
        
        return None
    
    def get_page_content(self, page_title: str) -> Optional[str]:
        """Get the HTML content of a Wikipedia page"""
        params = {
            'action': 'parse',
            'page': page_title,
            'prop': 'text',
            'format': 'json',
            'formatversion': '2'
        }
        
        data = self._make_api_call(params)
        if data and 'parse' in data and 'text' in data['parse']:
            self.stats['pages_scraped'] += 1
            return data['parse']['text']
        
        return None
    
    def get_page_info(self, page_title: str) -> Optional[Dict]:
        """Get page information including sections and metadata"""
        params = {
            'action': 'parse',
            'page': page_title,
            'prop': 'text|sections|displaytitle',
            'format': 'json',
            'formatversion': '2'
        }
        
        data = self._make_api_call(params)
        if data and 'parse' in data:
            return data['parse']
        
        return None
    
    def search_pages(self, search_term: str, limit: int = 10) -> List[str]:
        """Search for Wikipedia pages"""
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': search_term,
            'srlimit': limit,
            'format': 'json',
            'formatversion': '2'
        }
        
        data = self._make_api_call(params)
        if data and 'query' in data and 'search' in data['query']:
            return [page['title'] for page in data['query']['search']]
        
        return []
    
    def get_ufc_events_list(self) -> List[Dict]:
        """Get list of UFC events from the main UFC events page"""
        logger.info("Fetching UFC events list from Wikipedia")
        
        content = self.get_page_content('List_of_UFC_events')
        if not content:
            logger.error("Could not fetch UFC events list page")
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        events = []
        
        # Find all tables with UFC events
        tables = soup.find_all('table', {'class': 'wikitable'})
        
        for table in tables:
            rows = table.find_all('tr')
            
            # Skip header row
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 4:
                    event_data = self._parse_event_row(cells)
                    if event_data:
                        events.append(event_data)
        
        logger.info(f"Found {len(events)} UFC events")
        return events
    
    def _parse_event_row(self, cells) -> Optional[Dict]:
        """Parse a table row containing event information"""
        try:
            # Extract event name and link
            event_cell = cells[0]
            event_link = event_cell.find('a')
            
            if not event_link:
                return None
            
            event_name = self._clean_text(event_link.text)
            wiki_link = event_link.get('href', '').replace('/wiki/', '')
            
            # Extract other event details
            date = self._clean_text(cells[1].text) if len(cells) > 1 else ''
            venue = self._clean_text(cells[2].text) if len(cells) > 2 else ''
            location = self._clean_text(cells[3].text) if len(cells) > 3 else ''
            
            # Extract attendance and gate if available
            attendance = None
            gate = None
            if len(cells) > 4:
                extra_info = self._clean_text(cells[4].text)
                attendance = self._extract_attendance(extra_info)
                gate = self._extract_gate(extra_info)
            
            return {
                'event_name': event_name,
                'date': date,
                'venue': venue,
                'location': location,
                'attendance': attendance,
                'gate': gate,
                'wiki_link': wiki_link
            }
            
        except Exception as e:
            logger.warning(f"Error parsing event row: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text data"""
        if not text:
            return ""
        
        # Remove references [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _extract_attendance(self, text: str) -> Optional[int]:
        """Extract attendance number from text"""
        if not text:
            return None
        
        match = re.search(r'([\d,]+)\s*(?:attendance|fans)', text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                pass
        return None
    
    def _extract_gate(self, text: str) -> Optional[float]:
        """Extract gate revenue from text"""
        if not text:
            return None
        
        match = re.search(r'\$?\s*([\d,]+(?:\.\d+)?)\s*(?:million|[kK])?', text)
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                if 'million' in text.lower():
                    return amount * 1000000
                elif 'k' in text.lower():
                    return amount * 1000
                return amount
            except ValueError:
                pass
        return None
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset scraping statistics"""
        self.stats = {
            'api_calls': 0,
            'pages_scraped': 0,
            'errors': 0,
            'retries': 0
        }