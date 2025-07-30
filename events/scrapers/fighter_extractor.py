"""
Fighter Extractor - Fighter Data Extraction and Database Integration

This module handles extracting fighter information from Wikipedia event pages
and creating complete Fighter records in the database with Wikipedia URLs.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from django.db import transaction
from fighters.models import Fighter, FighterNameVariation
from organizations.models import WeightClass

logger = logging.getLogger(__name__)


class FighterExtractor:
    """Extracts and creates fighter records from Wikipedia event data"""
    
    def __init__(self):
        self.created_fighters = 0
        self.updated_fighters = 0
        self.matched_fighters = 0
        self.fighter_urls_added = 0
        
    def extract_fighters_from_event(self, event_soup: BeautifulSoup, event_name: str) -> List[Dict]:
        """Extract all fighters from an event page with their Wikipedia URLs"""
        logger.info(f"Extracting fighters from {event_name}")
        
        fighters_data = []
        
        # Find fight results tables
        fight_tables = self._find_fight_tables(event_soup)
        
        for table in fight_tables:
            table_fighters = self._extract_fighters_from_table(table)
            fighters_data.extend(table_fighters)
        
        # Remove duplicates based on name
        unique_fighters = self._deduplicate_fighters(fighters_data)
        
        logger.info(f"Found {len(unique_fighters)} unique fighters in {event_name}")
        return unique_fighters
    
    def _find_fight_tables(self, soup: BeautifulSoup) -> List[Tag]:
        """Find all tables containing fight results"""
        fight_tables = []
        
        # Look for tables with fight results
        tables = soup.find_all('table', {'class': ['toccolours', 'wikitable']})
        
        for table in tables:
            # Check if this table contains fight information
            if self._is_fight_table(table):
                fight_tables.append(table)
        
        return fight_tables
    
    def _is_fight_table(self, table: Tag) -> bool:
        """Check if a table contains fight results"""
        table_text = table.get_text().lower()
        
        fight_indicators = [
            'main card', 'preliminary card', 'early preliminary',
            'def.', 'defeated', 'vs.', 'decision', 'submission', 'ko', 'tko'
        ]
        
        return any(indicator in table_text for indicator in fight_indicators)
    
    def _extract_fighters_from_table(self, table: Tag) -> List[Dict]:
        """Extract fighter information from a fight results table"""
        fighters = []
        
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            
            if len(cells) >= 2:
                row_fighters = self._extract_fighters_from_row(cells)
                fighters.extend(row_fighters)
        
        return fighters
    
    def _extract_fighters_from_row(self, cells) -> List[Dict]:
        """Extract fighter information from a table row"""
        fighters = []
        
        for cell in cells:
            # Look for fighter names and links in each cell
            cell_fighters = self._extract_fighters_from_cell(cell)
            fighters.extend(cell_fighters)
        
        return fighters
    
    def _extract_fighters_from_cell(self, cell: Tag) -> List[Dict]:
        """Extract fighter information from a table cell"""
        fighters = []
        
        # Find all links in the cell
        links = cell.find_all('a')
        
        for link in links:
            fighter_data = self._extract_fighter_from_link(link)
            if fighter_data:
                fighters.append(fighter_data)
        
        # Also check for fighter names without links
        cell_text = cell.get_text()
        text_fighters = self._extract_fighters_from_text(cell_text)
        fighters.extend(text_fighters)
        
        return fighters
    
    def _extract_fighter_from_link(self, link: Tag) -> Optional[Dict]:
        """Extract fighter information from a Wikipedia link"""
        href = link.get('href', '')
        text = link.get_text().strip()
        
        # Skip non-fighter links
        if not self._is_fighter_link(href, text):
            return None
        
        # Parse fighter name
        first_name, last_name = self._parse_fighter_name(text)
        
        if not (first_name or last_name):
            return None
        
        # Construct full Wikipedia URL
        wikipedia_url = f"https://en.wikipedia.org{href}" if href.startswith('/wiki/') else None
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'display_name': text,
            'wikipedia_url': wikipedia_url,
            'source': 'wikipedia_link'
        }
    
    def _extract_fighters_from_text(self, text: str) -> List[Dict]:
        """Extract fighter names from plain text (when no Wikipedia link exists)"""
        fighters = []
        
        # Clean the text
        text = re.sub(r'\[\d+\]', '', text)  # Remove references
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        # Look for fighter name patterns in text like "Fighter A def. Fighter B"
        fight_patterns = [
            r'([A-Za-z\s\-\'\.]+)\s+(?:def\.|defeated)\s+([A-Za-z\s\-\'\.]+)',
            r'([A-Za-z\s\-\'\.]+)\s+vs\.?\s+([A-Za-z\s\-\'\.]+)',
        ]
        
        for pattern in fight_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                for i in range(1, match.lastindex + 1):
                    fighter_name = match.group(i).strip()
                    if self._is_valid_fighter_name(fighter_name):
                        first_name, last_name = self._parse_fighter_name(fighter_name)
                        if first_name or last_name:
                            fighters.append({
                                'first_name': first_name,
                                'last_name': last_name,
                                'display_name': fighter_name,
                                'wikipedia_url': None,
                                'source': 'text_extraction'
                            })
        
        return fighters
    
    def _is_fighter_link(self, href: str, text: str) -> bool:
        """Check if a link is likely to be a fighter profile"""
        if not href or not text:
            return False
        
        # Skip obvious non-fighter links
        skip_patterns = [
            r'/wiki/UFC_\d+',  # Event pages
            r'/wiki/Mixed_martial_arts',
            r'/wiki/Ultimate_Fighting_Championship',
            r'/wiki/\d+',  # Year pages
            r'/wiki/[A-Z]{2,4}$',  # Abbreviations
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, href):
                return False
        
        # Check if text looks like a fighter name
        return self._is_valid_fighter_name(text)
    
    def _is_valid_fighter_name(self, name: str) -> bool:
        """Check if a string looks like a valid fighter name"""
        if not name or len(name) < 3:
            return False
        
        # Skip obvious non-names
        skip_patterns = [
            r'^\d+$',  # Just numbers
            r'^[A-Z]{2,4}$',  # Abbreviations
            r'^\[[a-z]\]$',  # Wikipedia reference markers like [a], [b], [c]
            r'^\[\d+\]$',  # Wikipedia references like [1], [2], [3]
            r'decision|submission|ko|tko|draw',  # Fight results
            r'main card|preliminary|early',  # Card sections
            r'round \d+',  # Round references
            r'^def\.?$',  # Just "def." or "def"
            r'^vs\.?$',  # Just "vs" or "vs."
            r'weight',  # Weight class indicators
            r'time',  # Time indicators
            r'method',  # Method indicators
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.search(pattern, name_lower):
                return False
        
        # Should contain at least one letter and reasonable length
        return bool(re.search(r'[a-zA-Z]', name)) and len(name) <= 50
    
    def _parse_fighter_name(self, full_name: str) -> Tuple[str, str]:
        """Parse a full name into first and last name"""
        if not full_name:
            return "", ""
        
        # Clean the name
        name = re.sub(r'\([^)]*\)', '', full_name)  # Remove parentheses
        name = re.sub(r'[^\w\s\-\']', '', name)  # Remove special chars except hyphens and apostrophes
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize whitespace
        
        # Split into parts
        parts = name.split()
        
        if len(parts) == 0:
            return "", ""
        elif len(parts) == 1:
            # Single name - could be first or last
            return parts[0], ""
        elif len(parts) == 2:
            # First and last name
            return parts[0], parts[1]
        else:
            # Multiple parts - first part is first name, rest is last name
            return parts[0], " ".join(parts[1:])
    
    def _deduplicate_fighters(self, fighters_data: List[Dict]) -> List[Dict]:
        """Remove duplicate fighters based on name similarity"""
        unique_fighters = []
        seen_names = set()
        
        for fighter in fighters_data:
            # Create a normalized name for comparison
            normalized_name = self._normalize_name_for_comparison(fighter['display_name'])
            
            if normalized_name not in seen_names:
                seen_names.add(normalized_name)
                unique_fighters.append(fighter)
        
        return unique_fighters
    
    def _normalize_name_for_comparison(self, name: str) -> str:
        """Normalize a name for duplicate detection"""
        if not name:
            return ""
        
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    @transaction.atomic
    def create_or_update_fighters(self, fighters_data: List[Dict]) -> List[Fighter]:
        """Create or update Fighter records in the database"""
        logger.info(f"Creating/updating {len(fighters_data)} fighters in database")
        
        created_fighters = []
        
        for fighter_data in fighters_data:
            try:
                fighter = self._create_or_update_fighter(fighter_data)
                if fighter:
                    created_fighters.append(fighter)
            except Exception as e:
                logger.error(f"Error creating fighter {fighter_data.get('display_name', 'Unknown')}: {str(e)}")
        
        logger.info(f"Successfully processed {len(created_fighters)} fighters")
        return created_fighters
    
    def _create_or_update_fighter(self, fighter_data: Dict) -> Optional[Fighter]:
        """Create or update a single fighter record"""
        first_name = fighter_data.get('first_name', '').strip()
        last_name = fighter_data.get('last_name', '').strip()
        display_name = fighter_data.get('display_name', '').strip()
        wikipedia_url = fighter_data.get('wikipedia_url')
        
        if not (first_name or last_name or display_name):
            return None
        
        # Try to find existing fighter
        existing_fighter = self._find_existing_fighter(first_name, last_name, display_name)
        
        if existing_fighter:
            # Update existing fighter with Wikipedia URL if we have one
            updated = False
            if wikipedia_url and not existing_fighter.wikipedia_url:
                existing_fighter.wikipedia_url = wikipedia_url
                updated = True
                self.fighter_urls_added += 1
            
            if updated:
                existing_fighter.save()
                self.updated_fighters += 1
                logger.debug(f"Updated fighter: {existing_fighter.get_full_name()}")
            else:
                self.matched_fighters += 1
            
            return existing_fighter
        
        # Create new fighter
        fighter = Fighter.objects.create(
            first_name=first_name or "",
            last_name=last_name or "",
            display_name=display_name,
            wikipedia_url=wikipedia_url or "",
            data_source="wikipedia_scraper"
        )
        
        # Create name variation if display name is different from first + last
        if display_name and display_name != f"{first_name} {last_name}".strip():
            FighterNameVariation.objects.create(
                fighter=fighter,
                full_name_variation=display_name,
                variation_type="alternative",
                source="wikipedia_scraper"
            )
        
        self.created_fighters += 1
        logger.debug(f"Created new fighter: {fighter.get_full_name()}")
        
        return fighter
    
    def _find_existing_fighter(self, first_name: str, last_name: str, display_name: str) -> Optional[Fighter]:
        """Find existing fighter using multiple matching strategies"""
        
        # Strategy 1: Exact first and last name match
        if first_name and last_name:
            fighter = Fighter.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            ).first()
            if fighter:
                return fighter
        
        # Strategy 2: Display name match
        if display_name:
            fighter = Fighter.objects.filter(display_name__iexact=display_name).first()
            if fighter:
                return fighter
        
        # Strategy 3: Name variation match
        if display_name:
            variation = FighterNameVariation.objects.filter(
                full_name_variation__iexact=display_name
            ).first()
            if variation:
                return variation.fighter
        
        # Strategy 4: Partial name matching (last resort)
        if last_name:
            fighters = Fighter.objects.filter(last_name__iexact=last_name)
            if fighters.count() == 1:
                return fighters.first()
        
        return None
    
    def get_stats(self) -> Dict:
        """Get extraction statistics"""
        return {
            'created_fighters': self.created_fighters,
            'updated_fighters': self.updated_fighters,
            'matched_fighters': self.matched_fighters,
            'fighter_urls_added': self.fighter_urls_added,
            'total_processed': self.created_fighters + self.updated_fighters + self.matched_fighters
        }
    
    def reset_stats(self):
        """Reset extraction statistics"""
        self.created_fighters = 0
        self.updated_fighters = 0
        self.matched_fighters = 0
        self.fighter_urls_added = 0