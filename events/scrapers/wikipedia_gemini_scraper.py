"""
Enhanced Wikipedia UFC Scraper for Gemini AI Integration
Extracts HTML sections and fighter Wikipedia URLs for structured processing
"""
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from datetime import datetime

from .schemas import ScrapingResultSchema

logger = logging.getLogger(__name__)


class WikipediaGeminiScraper:
    """Enhanced Wikipedia scraper optimized for Gemini AI processing"""
    
    def __init__(self, rate_limit_delay: float = 1.0, request_timeout: int = 30):
        self.rate_limit_delay = rate_limit_delay
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UFC-MMA-Backend-Scraper/1.0 (Educational Research Purpose)'
        })
        
        # Configure session with timeout and retry settings
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Track consecutive failures for circuit breaking
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
    def test_connectivity(self) -> Tuple[bool, str]:
        """
        Test connectivity to Wikipedia
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.info("Testing Wikipedia connectivity...")
            start_time = time.time()
            response = self.session.get("https://en.wikipedia.org", timeout=10)
            response.raise_for_status()
            elapsed = time.time() - start_time
            
            message = f"✅ Wikipedia connectivity OK ({elapsed:.2f}s)"
            logger.info(message)
            return True, message
            
        except requests.exceptions.Timeout:
            message = "❌ Wikipedia connectivity timeout"
            logger.error(message)
            return False, message
        except Exception as e:
            message = f"❌ Wikipedia connectivity error: {str(e)}"
            logger.error(message)
            return False, message
    
    def reset_circuit_breaker(self):
        """Reset the circuit breaker and consecutive failure count"""
        logger.info(f"Resetting circuit breaker (was at {self.consecutive_failures} failures)")
        self.consecutive_failures = 0
    
    def get_circuit_breaker_status(self) -> Dict[str, any]:
        """Get current circuit breaker status"""
        return {
            'consecutive_failures': self.consecutive_failures,
            'max_failures': self.max_consecutive_failures,
            'is_open': self.consecutive_failures >= self.max_consecutive_failures
        }
    
    def get_ufc_event_urls(self, limit: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        Get list of UFC event URLs from the main UFC events list page
        
        Returns:
            List of (event_name, wikipedia_url) tuples
        """
        list_url = "https://en.wikipedia.org/wiki/List_of_UFC_events"
        
        try:
            response = self.session.get(list_url, timeout=self.request_timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            event_urls = []
            
            # Find tables containing UFC event links
            tables = soup.find_all('table', class_='wikitable')
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 2:
                        # Look for event links in the first few cells
                        for cell in cells[:3]:
                            link = cell.find('a', href=True)
                            if link and '/wiki/UFC_' in link['href']:
                                event_name = link.get_text().strip()
                                event_url = urljoin("https://en.wikipedia.org", link['href'])
                                
                                # Avoid duplicates
                                if (event_name, event_url) not in event_urls:
                                    event_urls.append((event_name, event_url))
                                    
                                    if limit and len(event_urls) >= limit:
                                        return event_urls
                                break
            
            logger.info(f"Found {len(event_urls)} UFC event URLs")
            return event_urls
            
        except Exception as e:
            logger.error(f"Error fetching UFC event URLs: {e}")
            return []
    
    def scrape_event_page(self, event_url: str) -> ScrapingResultSchema:
        """
        Scrape a UFC Wikipedia event page and extract HTML sections
        
        Args:
            event_url: Wikipedia URL of the UFC event
            
        Returns:
            ScrapingResultSchema with extracted HTML sections
        """
        logger.info(f"Scraping UFC event: {event_url}")
        
        # Check circuit breaker
        if self.consecutive_failures >= self.max_consecutive_failures:
            logger.error(f"Circuit breaker triggered after {self.consecutive_failures} failures")
            result = ScrapingResultSchema(
                event_url=event_url,
                event_title="",
                scraping_timestamp=datetime.now().isoformat(),
                extraction_success=False,
                error_messages=[f"Circuit breaker open - {self.consecutive_failures} consecutive failures"]
            )
            return result
        
        # Rate limiting
        time.sleep(self.rate_limit_delay)
        
        result = ScrapingResultSchema(
            event_url=event_url,
            event_title="",
            scraping_timestamp=datetime.now().isoformat(),
            extraction_success=False
        )
        
        try:
            logger.debug(f"Fetching {event_url} with {self.request_timeout}s timeout")
            response = self.session.get(event_url, timeout=self.request_timeout)
            response.raise_for_status()
            logger.debug(f"Response received: {len(response.content)} bytes")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract page title
            title_elem = soup.find('h1', class_='firstHeading')
            result.event_title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract first paragraph
            result.first_paragraph_html = self._extract_first_paragraph(soup)
            
            # Extract infobox
            result.infobox_html = self._extract_infobox(soup)
            
            # Extract results table with fighter links
            result.results_table_html = self._extract_results_table(soup)
            
            # Extract announced bouts section (for upcoming events)
            announced_bouts_html = self._extract_announced_bouts(soup)
            if announced_bouts_html:
                # Append announced bouts to results table HTML or create separate section
                if result.results_table_html:
                    result.results_table_html += "\n\n<!-- ANNOUNCED BOUTS SECTION -->\n" + announced_bouts_html
                else:
                    result.results_table_html = announced_bouts_html
            
            # Extract bonus awards
            result.bonus_awards_html = self._extract_bonus_awards(soup)
            
            # Mark as successful if we got at least the results table
            result.extraction_success = bool(result.results_table_html)
            
            if result.extraction_success:
                logger.info(f"✅ Successfully scraped {result.event_title}")
                # Reset consecutive failures on success
                self.consecutive_failures = 0
            else:
                logger.warning(f"⚠️ Limited data extracted from {result.event_title}")
                result.error_messages.append("No results table found")
                # Increment consecutive failures for parsing issues
                self.consecutive_failures += 1
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error scraping {event_url} after {self.request_timeout}s: {e}")
            result.error_messages.append(f"Request timeout after {self.request_timeout}s: {str(e)}")
            self.consecutive_failures += 1
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error scraping {event_url}: {e}")
            result.error_messages.append(f"Connection error: {str(e)}")
            self.consecutive_failures += 1
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error scraping {event_url}: {e}")
            result.error_messages.append(f"HTTP error: {str(e)}")
            self.consecutive_failures += 1
        except requests.RequestException as e:
            logger.error(f"Request error scraping {event_url}: {e}")
            result.error_messages.append(f"Request error: {str(e)}")
            self.consecutive_failures += 1
        except Exception as e:
            logger.error(f"Unexpected error scraping {event_url}: {e}")
            result.error_messages.append(f"Parsing error: {str(e)}")
            # Don't increment failures for parsing errors - these might be page-specific
        
        return result
    
    def _extract_first_paragraph(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the first paragraph after the infobox"""
        try:
            # Find the first paragraph that's not part of navigation or infobox
            paragraphs = soup.find_all('p')
            
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50 and not text.startswith('Coordinates:'):
                    return str(p)
            
            return None
        except Exception as e:
            logger.debug(f"Error extracting first paragraph: {e}")
            return None
    
    def _extract_infobox(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the event infobox table"""
        try:
            # Look for infobox
            infobox = soup.find('table', class_='infobox')
            if not infobox:
                # Try alternative selectors
                infobox = soup.find('table', class_='infobox-event')
            
            if infobox:
                return str(infobox)
            
            return None
        except Exception as e:
            logger.debug(f"Error extracting infobox: {e}")
            return None
    
    def _extract_results_table(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the fight results table with preserved fighter links"""
        try:
            # Look for the main results table
            results_table = None
            
            # Try multiple selectors for results table
            selectors = [
                'table.toccolours',
                'table.wikitable.sortable',
                'table.wikitable'
            ]
            
            for selector in selectors:
                tables = soup.select(selector)
                for table in tables:
                    # Check if this looks like a results table
                    if self._is_results_table(table):
                        results_table = table
                        break
                if results_table:
                    break
            
            if not results_table:
                logger.warning("No results table found")
                return None
            
            # Preserve fighter Wikipedia links
            self._preserve_fighter_links(results_table)
            
            return str(results_table)
            
        except Exception as e:
            logger.debug(f"Error extracting results table: {e}")
            return None
    
    def _extract_announced_bouts(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract announced bouts section from upcoming events"""
        try:
            # Look for "Announced bouts" section
            announced_section = None
            
            # Search for headers containing "announced" or "bout"
            headers = soup.find_all(['h2', 'h3', 'h4'])
            for header in headers:
                header_text = header.get_text().lower()
                if any(term in header_text for term in ['announced', 'upcoming', 'scheduled bout', 'future bout']):
                    # Get the section content after this header
                    announced_section = self._get_section_content(header)
                    break
            
            if not announced_section:
                # Alternative: look for lists containing fight information
                # Sometimes announced bouts are in unordered lists
                lists = soup.find_all('ul')
                for ul in lists:
                    list_text = ul.get_text().lower()
                    if 'bout:' in list_text or 'vs.' in list_text or 'vs' in list_text:
                        # Check if this looks like fight announcements
                        list_items = ul.find_all('li')
                        fight_like_items = 0
                        for li in list_items:
                            li_text = li.get_text()
                            if 'vs.' in li_text or 'vs' in li_text:
                                fight_like_items += 1
                        
                        # If multiple items look like fights, include this list
                        if fight_like_items >= 1:
                            announced_section = ul
                            break
            
            if announced_section:
                # Preserve fighter links in announced bouts
                self._preserve_fighter_links(announced_section)
                logger.info("Found announced bouts section")
                return str(announced_section)
            else:
                logger.debug("No announced bouts section found")
                return None
            
        except Exception as e:
            logger.debug(f"Error extracting announced bouts: {e}")
            return None
    
    def _extract_bonus_awards(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract bonus awards section"""
        try:
            # Look for bonus awards section
            bonus_section = None
            
            # Search for headers containing bonus-related terms
            headers = soup.find_all(['h2', 'h3', 'h4'])
            for header in headers:
                header_text = header.get_text().lower()
                if any(term in header_text for term in ['bonus', 'award', 'performance']):
                    # Get the section content after this header
                    bonus_section = self._get_section_content(header)
                    break
            
            return str(bonus_section) if bonus_section else None
            
        except Exception as e:
            logger.debug(f"Error extracting bonus awards: {e}")
            return None
    
    def _is_results_table(self, table: Tag) -> bool:
        """Determine if a table is the fight results table"""
        try:
            # Check table headers
            headers = table.find_all(['th'])
            header_text = ' '.join([th.get_text().lower() for th in headers])
            
            # Look for fight-related terms in headers
            fight_terms = ['weight', 'method', 'round', 'time', 'def', 'defeated']
            return any(term in header_text for term in fight_terms)
            
        except Exception:
            return False
    
    def _preserve_fighter_links(self, table: Tag) -> None:
        """Ensure fighter Wikipedia links are preserved in the table HTML"""
        try:
            # Find all links in the table
            links = table.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                
                # Convert relative Wikipedia URLs to absolute
                if href.startswith('/wiki/'):
                    absolute_url = urljoin("https://en.wikipedia.org", href)
                    link['href'] = absolute_url
                    
                    # Add a data attribute to help Gemini identify fighter links
                    if self._is_fighter_link(link):
                        link['data-fighter-link'] = 'true'
            
        except Exception as e:
            logger.debug(f"Error preserving fighter links: {e}")
    
    def _is_fighter_link(self, link: Tag) -> bool:
        """Determine if a link is likely a fighter profile link"""
        try:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Skip non-Wikipedia links
            if 'wikipedia.org/wiki/' not in href:
                return False
            
            # Skip common non-fighter pages
            skip_terms = [
                'UFC_', 'List_of', 'Category:', 'Template:', 'File:',
                '_Arena', '_Center', 'Las_Vegas', '_Championship',
                'Mixed_martial_arts', 'Ultimate_Fighting'
            ]
            
            if any(term in href for term in skip_terms):
                return False
            
            # Likely a fighter if it's a person's name pattern
            return len(text.split()) >= 1 and text[0].isupper()
            
        except Exception:
            return False
    
    def _get_section_content(self, header: Tag) -> Optional[Tag]:
        """Get content following a section header until the next header"""
        try:
            content_elements = []
            current = header.next_sibling
            
            while current:
                if hasattr(current, 'name'):
                    # Stop at next header of same or higher level
                    if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        if current.name <= header.name:
                            break
                    
                    # Collect content elements
                    if current.name in ['p', 'ul', 'ol', 'table', 'div']:
                        content_elements.append(str(current))
                
                current = current.next_sibling
            
            if content_elements:
                # Wrap in a div for clean extraction
                return BeautifulSoup(
                    f'<div class="bonus-section">{"".join(content_elements)}</div>',
                    'html.parser'
                ).div
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting section content: {e}")
            return None
    
    def batch_scrape_events(self, event_urls: List[str], 
                           batch_size: int = 5, max_retries: int = 2) -> List[ScrapingResultSchema]:
        """
        Scrape multiple UFC events in batches with rate limiting
        
        Args:
            event_urls: List of Wikipedia URLs to scrape
            batch_size: Number of events to process in each batch
            
        Returns:
            List of ScrapingResultSchema results
        """
        results = []
        total_events = len(event_urls)
        
        logger.info(f"Starting batch scraping of {total_events} UFC events")
        
        for i in range(0, total_events, batch_size):
            batch = event_urls[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} events)")
            
            for event_url in batch:
                success = False
                last_error = None
                
                # Retry logic for failed events
                for attempt in range(max_retries + 1):
                    try:
                        if attempt > 0:
                            logger.info(f"Retry {attempt}/{max_retries} for {event_url}")
                            # Longer delay for retries
                            time.sleep(self.rate_limit_delay * 2)
                        
                        result = self.scrape_event_page(event_url)
                        results.append(result)
                        success = True
                        
                        if result.extraction_success:
                            logger.info(f"✅ Successfully scraped: {result.event_title}")
                        else:
                            logger.warning(f"⚠️  Scraped but limited data: {result.event_title}")
                        
                        # Additional delay between events in same batch
                        time.sleep(self.rate_limit_delay * 0.5)
                        break
                        
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Attempt {attempt + 1} failed for {event_url}: {e}")
                        if attempt < max_retries:
                            continue
                
                # If all retries failed, create error result
                if not success:
                    logger.error(f"❌ All {max_retries + 1} attempts failed for {event_url}: {last_error}")
                    error_result = ScrapingResultSchema(
                        event_url=event_url,
                        event_title="Error",
                        scraping_timestamp=datetime.now().isoformat(),
                        extraction_success=False,
                        error_messages=[f"All {max_retries + 1} attempts failed: {str(last_error)}"]
                    )
                    results.append(error_result)
            
            # Longer delay between batches
            if i + batch_size < total_events:
                logger.info(f"Waiting {self.rate_limit_delay * 2}s before next batch...")
                time.sleep(self.rate_limit_delay * 2)
        
        successful = sum(1 for r in results if r.extraction_success)
        logger.info(f"Batch scraping completed: {successful}/{total_events} successful")
        
        return results