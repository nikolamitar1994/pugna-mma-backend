"""
Enhanced Wikipedia UFC Scraper - Improved Fight Extraction Logic

This module contains the enhanced fight extraction logic specifically designed
for UFC Wikipedia pages with proper table structure parsing.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class WikipediaEnhancedScraper:
    """Enhanced scraper with improved UFC Wikipedia page parsing"""
    
    def __init__(self):
        self.debug_enabled = True
        
    def extract_fight_card(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract fight card information from UFC Wikipedia page"""
        fights_data = []
        
        # Find the main results table with class 'toccolours'
        fight_table = soup.find('table', {'class': 'toccolours'})
        
        if not fight_table:
            logger.warning("No toccolours table found on page")
            return fights_data
            
        logger.debug("Found toccolours table")
        
        # Parse all rows in the table
        rows = fight_table.find_all('tr')
        logger.debug(f"Found {len(rows)} rows in fight table")
        
        fight_order = 1
        current_card_section = "Main Card"  # Default section
        
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            row_text = row.get_text().strip()
            
            logger.debug(f"Row {i+1}: {len(cells)} cells, text: {row_text[:100]}...")
            
            # Check if this is a section header row
            if self._is_section_header(row_text):
                current_card_section = self._extract_card_section(row_text)
                logger.debug(f"Found card section: {current_card_section}")
                continue
                
            # Skip header rows or rows with insufficient cells
            if len(cells) < 8:
                logger.debug(f"Skipping row {i+1} - insufficient cells ({len(cells)})")
                continue
                
            # Parse fight row (UFC table structure: 8 cells)
            fight_data = self._parse_ufc_fight_row(cells, fight_order, current_card_section)
            
            if fight_data:
                logger.debug(f"✅ Successfully parsed fight {fight_order}: {fight_data['winner']} def. {fight_data['loser']}")
                fights_data.append(fight_data)
                fight_order += 1
            else:
                logger.debug(f"❌ Failed to parse fight from row {i+1}")
        
        logger.info(f"Total fights extracted: {len(fights_data)}")
        return fights_data
    
    def _is_section_header(self, row_text: str) -> bool:
        """Check if row is a card section header"""
        section_indicators = [
            'main card',
            'preliminary card', 
            'early preliminary',
            'prelims'
        ]
        
        row_lower = row_text.lower()
        return any(indicator in row_lower for indicator in section_indicators)
    
    def _extract_card_section(self, row_text: str) -> str:
        """Extract card section name from header row"""
        row_lower = row_text.lower()
        
        if 'main card' in row_lower:
            return "Main Card"
        elif 'early preliminary' in row_lower:
            return "Early Preliminary Card"
        elif 'preliminary' in row_lower or 'prelims' in row_lower:
            return "Preliminary Card"
        else:
            return "Unknown Card"
    
    def _parse_ufc_fight_row(self, cells: List[Tag], fight_order: int, card_section: str) -> Optional[Dict]:
        """Parse a UFC fight row with 8-cell structure"""
        try:
            # UFC table structure: weight_class | fighter1 | "def." | fighter2 | method | round | time | notes
            if len(cells) < 8:
                return None
                
            # Extract raw cell texts
            cell_texts = [cell.get_text().strip() for cell in cells]
            logger.debug(f"Raw cell texts: {cell_texts}")
            
            # Parse each component
            weight_class = self._clean_weight_class(cell_texts[0])
            fighter1_raw = cell_texts[1]
            def_indicator = cell_texts[2]
            fighter2_raw = cell_texts[3]
            method_raw = cell_texts[4]
            round_raw = cell_texts[5]
            time_raw = cell_texts[6]
            notes_raw = cell_texts[7] if len(cell_texts) > 7 else ""
            
            # Validate basic structure
            if def_indicator.lower() not in ['def.', 'def', 'defeated']:
                logger.debug(f"Invalid def indicator: '{def_indicator}'")
                return None
            
            # Clean fighter names
            winner = self._clean_fighter_name(fighter1_raw)
            loser = self._clean_fighter_name(fighter2_raw)
            
            # Validate fighter names
            if not self._is_valid_fighter_name(winner) or not self._is_valid_fighter_name(loser):
                logger.debug(f"Invalid fighter names: winner='{winner}', loser='{loser}'")
                return None
            
            # Parse round and time
            ending_round = self._parse_round(round_raw)
            ending_time = self._clean_time(time_raw)
            
            # Detect title fight
            is_title_fight = '(c)' in fighter1_raw or '(c)' in fighter2_raw
            is_main_event = card_section == "Main Card" and fight_order == 1
            
            # Build fight data
            fight_data = {
                'fight_order': fight_order,
                'weight_class': weight_class,
                'winner': winner,
                'loser': loser,
                'fighters': [
                    {'name': winner, 'corner': 'red', 'result': 'win'},
                    {'name': loser, 'corner': 'blue', 'result': 'loss'}
                ],
                'method': self._parse_method_text(method_raw),
                'method_details': method_raw,
                'ending_round': ending_round,
                'ending_time': ending_time,
                'is_main_event': is_main_event,
                'is_title_fight': is_title_fight,
                'scheduled_rounds': 5 if is_title_fight or is_main_event else 3,
                'card_section': card_section,
                'notes': notes_raw,
                'fighter_urls': self._extract_fighter_urls(cells[1], cells[3])
            }
            
            logger.debug(f"Parsed fight data: {fight_data['winner']} def. {fight_data['loser']} via {fight_data['method']}")
            return fight_data
            
        except Exception as e:
            logger.warning(f"Error parsing UFC fight row: {str(e)}")
            return None
    
    def _clean_fighter_name(self, name: str) -> str:
        """Clean fighter name removing Wikipedia artifacts"""
        if not name:
            return ""
            
        # Remove reference markers like [a], [b], [c]
        name = re.sub(r'\[[a-z]\]', '', name)
        
        # Remove numeric references like [1], [2], [3]
        name = re.sub(r'\[\d+\]', '', name)
        
        # Remove championship indicator (c) but keep the name
        name = re.sub(r'\s*\(c\)\s*', '', name)
        
        # Remove other parenthetical content that's not part of the name
        name = re.sub(r'\([^)]*\)', '', name)
        
        # Normalize whitespace
        return ' '.join(name.split()).strip()
    
    def _clean_weight_class(self, weight_class: str) -> str:
        """Clean and standardize weight class name"""
        if not weight_class:
            return ""
            
        # Remove references
        cleaned = re.sub(r'\[\d+\]', '', weight_class).strip()
        
        # Standardize common weight classes
        weight_mapping = {
            'lightweight': 'Lightweight',
            'welterweight': 'Welterweight',
            'middleweight': 'Middleweight',
            'light heavyweight': 'Light Heavyweight',
            'heavyweight': 'Heavyweight',
            'featherweight': 'Featherweight',
            'bantamweight': 'Bantamweight',
            'flyweight': 'Flyweight',
            'strawweight': 'Strawweight'
        }
        
        cleaned_lower = cleaned.lower()
        for key, value in weight_mapping.items():
            if key in cleaned_lower:
                return value
        
        return cleaned.title()
    
    def _clean_time(self, time_str: str) -> str:
        """Clean fight time string"""
        if not time_str:
            return ""
            
        # Remove references and normalize
        cleaned = re.sub(r'\[\d+\]', '', time_str).strip()
        
        # Match time patterns like "3:14", "5:00"
        time_match = re.search(r'\d+:\d+', cleaned)
        if time_match:
            return time_match.group()
            
        return cleaned
    
    def _parse_round(self, round_str: str) -> Optional[int]:
        """Parse round number from string"""
        if not round_str:
            return None
            
        # Extract just the number
        round_match = re.search(r'\d+', round_str)
        if round_match:
            try:
                return int(round_match.group())
            except ValueError:
                pass
                
        return None
    
    def _parse_method_text(self, method_raw: str) -> str:
        """Parse and standardize fight method"""
        if not method_raw:
            return ""
            
        method_lower = method_raw.lower()
        
        # Decision types
        if 'decision' in method_lower:
            if 'unanimous' in method_lower:
                return 'Unanimous Decision'
            elif 'majority' in method_lower:
                return 'Majority Decision'
            elif 'split' in method_lower:
                return 'Split Decision'
            else:
                return 'Decision'
        
        # Finish types
        elif 'submission' in method_lower:
            return 'Submission'
        elif 'ko' in method_lower and 'tko' not in method_lower:
            return 'KO'
        elif 'tko' in method_lower:
            return 'TKO'
        elif 'dq' in method_lower or 'disqualification' in method_lower:
            return 'DQ'
        elif 'nc' in method_lower or 'no contest' in method_lower:
            return 'No Contest'
        
        # Default
        return method_raw.strip()
    
    def _extract_fighter_urls(self, fighter1_cell: Tag, fighter2_cell: Tag) -> Dict[str, str]:
        """Extract Wikipedia URLs for fighters from table cells"""
        urls = {}
        
        # Extract URL from first fighter
        link1 = fighter1_cell.find('a')
        if link1 and link1.get('href'):
            href = link1.get('href')
            if href.startswith('/wiki/'):
                urls['winner_url'] = f"https://en.wikipedia.org{href}"
        
        # Extract URL from second fighter  
        link2 = fighter2_cell.find('a')
        if link2 and link2.get('href'):
            href = link2.get('href')
            if href.startswith('/wiki/'):
                urls['loser_url'] = f"https://en.wikipedia.org{href}"
        
        return urls
    
    def _is_valid_fighter_name(self, name: str) -> bool:
        """Check if string looks like a valid fighter name"""
        if not name or len(name) < 2:
            return False
        
        # Skip obvious non-names
        skip_patterns = [
            r'^\d+$',  # Just numbers
            r'^[A-Z]{2,4}$',  # Abbreviations
            r'^\[[a-z]\]$',  # Reference markers like [a], [b], [c]
            r'^\[\d+\]$',  # Numeric references like [1], [2], [3]
            r'^def\.?$',  # Just "def." or "def"
            r'^vs\.?$',  # Just "vs" or "vs."
            r'decision|submission|ko|tko',  # Fight result terms
            r'main card|preliminary|early',  # Card sections
            r'round \d+',  # Round references
            r'weight',  # Weight class indicators
            r'time|method',  # Other table headers
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if re.search(pattern, name_lower):
                return False
        
        # Must contain letters and be reasonable length
        has_letters = bool(re.search(r'[a-zA-Z]', name))
        reasonable_length = len(name) <= 50
        
        return has_letters and reasonable_length