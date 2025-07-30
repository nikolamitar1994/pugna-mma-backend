"""
Event Processor - Event and Fight Card Processing

This module handles processing Wikipedia event data and creating Event, Fight,
and FightParticipant records in the database.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from django.db import transaction
from django.utils.dateparse import parse_date

from events.models import Event, Fight, FightParticipant
from organizations.models import Organization, WeightClass
from fighters.models import Fighter
from .wikipedia_enhanced_scraper import WikipediaEnhancedScraper

logger = logging.getLogger(__name__)


class EventProcessor:
    """Processes Wikipedia event data and creates database records"""
    
    def __init__(self):
        self.created_events = 0
        self.updated_events = 0
        self.created_fights = 0
        self.created_participants = 0
        self.processed_fighters = {}  # Cache for fighter lookups
        self.enhanced_scraper = WikipediaEnhancedScraper()  # Enhanced scraper instance
        
    @transaction.atomic
    def process_event(self, event_data: Dict, event_soup: BeautifulSoup, fighters: List[Fighter]) -> Optional[Event]:
        """Process a complete event with all fights and participants"""
        try:
            # Extract additional event data from the Wikipedia page
            enhanced_event_data = self._enhance_event_data(event_data, event_soup)
            
            # Create or update the event record
            event = self._create_or_update_event(enhanced_event_data)
            if not event:
                return None
            
            # Process fight card using enhanced scraper
            fights_data = self.enhanced_scraper.extract_fight_card(event_soup)
            
            # Create fight records
            for fight_data in fights_data:
                fight = self._create_fight(event, fight_data, fighters)
                if fight:
                    self._create_fight_participants(fight, fight_data, fighters)
            
            logger.info(f"Successfully processed event: {event.name}")
            return event
            
        except Exception as e:
            logger.error(f"Error processing event {event_data.get('event_name', 'Unknown')}: {str(e)}")
            return None
    
    def _enhance_event_data(self, event_data: Dict, soup: BeautifulSoup) -> Dict:
        """Extract additional event information from the Wikipedia page"""
        enhanced_data = event_data.copy()
        
        # Extract date from infobox or content
        if not enhanced_data.get('date'):
            date_str = self._extract_date_from_page(soup)
            if date_str:
                enhanced_data['date'] = date_str
        
        # Extract venue if not provided
        if not enhanced_data.get('venue'):
            venue = self._extract_venue_from_page(soup)
            if venue:
                enhanced_data['venue'] = venue
        
        # Extract location if not provided
        if not enhanced_data.get('location'):
            location = self._extract_location_from_page(soup)
            if location:
                enhanced_data['location'] = location
        
        # Extract attendance if available
        if not enhanced_data.get('attendance'):
            attendance = self._extract_attendance_from_page(soup)
            if attendance:
                enhanced_data['attendance'] = attendance
        
        return enhanced_data
    
    def _extract_date_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract event date from Wikipedia page"""
        # Look for date in the infobox
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            # Look for date row in infobox
            rows = infobox.find_all('tr')
            for row in rows:
                header = row.find('th')
                if header and ('date' in header.get_text().lower()):
                    data_cell = row.find('td')
                    if data_cell:
                        return data_cell.get_text().strip()
        
        # Look for date in the first paragraph
        first_para = soup.find('p')
        if first_para:
            para_text = first_para.get_text()
            # Look for patterns like "took place on [date]" or "was held on [date]"
            date_patterns = [
                r'(?:took place|was held|occurred) on ([^.;]+)',
                r'(\w+ \d{1,2}, \d{4})',  # "April 13, 2024"
                r'(\d{1,2} \w+ \d{4})',   # "13 April 2024"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, para_text, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
                    # Clean up common Wikipedia artifacts
                    date_str = re.sub(r'\[\d+\]', '', date_str)  # Remove references
                    date_str = re.sub(r'\s+', ' ', date_str)      # Normalize spaces
                    return date_str
        
        return None
    
    def _extract_venue_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract venue from Wikipedia page"""
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                header = row.find('th')
                if header and ('venue' in header.get_text().lower()):
                    data_cell = row.find('td')
                    if data_cell:
                        return data_cell.get_text().strip()
        return None
    
    def _extract_location_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract location from Wikipedia page"""
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                header = row.find('th')
                if header and ('location' in header.get_text().lower()):
                    data_cell = row.find('td')
                    if data_cell:
                        return data_cell.get_text().strip()
        return None
    
    def _extract_attendance_from_page(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract attendance from Wikipedia page"""
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                header = row.find('th')
                if header and ('attendance' in header.get_text().lower()):
                    data_cell = row.find('td')
                    if data_cell:
                        text = data_cell.get_text().strip()
                        # Extract number from text like "15,656" or "15,656 (sold out)"
                        match = re.search(r'([\d,]+)', text)
                        if match:
                            try:
                                return int(match.group(1).replace(',', ''))
                            except ValueError:
                                pass
        return None
    
    def _create_or_update_event(self, event_data: Dict) -> Optional[Event]:
        """Create or update an Event record"""
        event_name = event_data.get('event_name', '').strip()
        if not event_name:
            return None
        
        # Get or create UFC organization
        ufc_org, _ = Organization.objects.get_or_create(
            name="Ultimate Fighting Championship",
            defaults={
                'abbreviation': 'UFC',
                'country': 'United States',
                'founded_year': 1993
            }
        )
        
        # Parse event date
        event_date = self._parse_event_date(event_data.get('date', ''))
        if not event_date:
            logger.warning(f"Could not parse date for event: {event_name}")
            return None
        
        # Parse location details
        location_data = self._parse_location(event_data.get('location', ''), event_data.get('venue', ''))
        
        # Extract event number if available
        event_number = self._extract_event_number(event_name)
        
        # Check if event already exists
        existing_event = Event.objects.filter(
            name__iexact=event_name,
            organization=ufc_org
        ).first()
        
        if existing_event:
            # Update existing event with any new information
            updated = False
            
            if event_data.get('attendance') and not existing_event.attendance:
                existing_event.attendance = event_data['attendance']
                updated = True
            
            if event_data.get('gate') and not existing_event.gate_revenue:
                existing_event.gate_revenue = Decimal(str(event_data['gate']))
                updated = True
            
            if updated:
                existing_event.save()
                self.updated_events += 1
                logger.debug(f"Updated event: {existing_event.name}")
            
            return existing_event
        
        # Create new event
        event = Event.objects.create(
            organization=ufc_org,
            name=event_name,
            event_number=event_number,
            date=event_date,
            location=location_data['full_location'],
            venue=location_data['venue'],
            city=location_data['city'],
            state=location_data['state'],
            country=location_data['country'],
            attendance=event_data.get('attendance'),
            gate_revenue=Decimal(str(event_data['gate'])) if event_data.get('gate') else None,
            status='completed'  # Wikipedia events are historical
        )
        
        self.created_events += 1
        logger.debug(f"Created event: {event.name}")
        
        return event
    
    def _parse_event_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse event date from various Wikipedia date formats"""
        if not date_str:
            return None
        
        # Clean the date string
        date_str = re.sub(r'\[\d+\]', '', date_str)  # Remove references
        date_str = date_str.strip()
        
        # Try different date formats commonly used on Wikipedia
        date_patterns = [
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "January 1, 2024" or "January 1 2024"
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',    # "1 January 2024"
            r'(\d{4})-(\d{1,2})-(\d{1,2})',    # "2024-01-01"
            r'(\d{1,2})/(\d{1,2})/(\d{4})',    # "01/01/2024"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if pattern == date_patterns[0]:  # Month Day, Year
                        month_name, day, year = match.groups()
                        date_obj = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
                    elif pattern == date_patterns[1]:  # Day Month Year
                        day, month_name, year = match.groups()
                        date_obj = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
                    elif pattern == date_patterns[2]:  # ISO format
                        year, month, day = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    elif pattern == date_patterns[3]:  # MM/DD/YYYY
                        month, day, year = match.groups()
                        date_obj = datetime(int(year), int(month), int(day))
                    
                    return date_obj.date()
                except (ValueError, AttributeError):
                    continue
        
        # Try Django's parse_date as fallback
        try:
            return parse_date(date_str)
        except:
            pass
        
        return None
    
    def _parse_location(self, location_str: str, venue_str: str) -> Dict[str, str]:
        """Parse location string into components"""
        location_data = {
            'full_location': location_str,
            'venue': venue_str,
            'city': '',
            'state': '',
            'country': ''
        }
        
        if not location_str:
            return location_data
        
        # Clean location string
        location = re.sub(r'\[\d+\]', '', location_str).strip()
        
        # Common patterns for UFC locations
        # "City, State, Country" or "City, Country"
        parts = [part.strip() for part in location.split(',')]
        
        if len(parts) >= 3:
            # City, State, Country
            location_data['city'] = parts[0]
            location_data['state'] = parts[1]
            location_data['country'] = parts[2]
        elif len(parts) == 2:
            # City, Country or City, State
            location_data['city'] = parts[0]
            # Determine if second part is state or country
            if parts[1] in ['United States', 'Canada', 'United Kingdom', 'Australia', 'Brazil']:
                location_data['country'] = parts[1]
            else:
                location_data['state'] = parts[1]
                # Try to infer country from state
                if parts[1] in ['Nevada', 'California', 'New York', 'Florida', 'Texas']:
                    location_data['country'] = 'United States'
        elif len(parts) == 1:
            # Just city or country
            location_data['city'] = parts[0]
        
        return location_data
    
    def _extract_event_number(self, event_name: str) -> Optional[int]:
        """Extract UFC event number from event name"""
        if not event_name:
            return None
        
        # Look for "UFC XXX" pattern
        match = re.search(r'UFC\s+(\d+)', event_name, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def _extract_fight_card(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract fight card information from event page using enhanced scraper"""
        # Delegate to enhanced scraper
        logger.debug("Using enhanced scraper for fight extraction")
        fights = self.enhanced_scraper.extract_fight_card(soup)
        logger.debug(f"Enhanced scraper extracted {len(fights)} fights")
        return fights
    
    # Note: _is_fight_results_table method removed - now handled by enhanced scraper
    
    # Note: _parse_fight_table method removed - now handled by enhanced scraper
    
    # Note: _parse_fight_row method removed - now handled by enhanced scraper
    
    # Note: Weight class extraction methods removed - now handled by enhanced scraper
    
    # Note: _extract_fight_result method removed - now handled by enhanced scraper
    
    # Note: _is_valid_fighter_name method removed - now handled by enhanced scraper
    
    # Note: _normalize_method removed - now handled by enhanced scraper
    
    @transaction.atomic
    def _create_fight(self, event: Event, fight_data: Dict, fighters: List[Fighter]) -> Optional[Fight]:
        """Create a Fight record"""
        try:
            # Get or create weight class
            weight_class = None
            if fight_data.get('weight_class'):
                weight_class = self._get_or_create_weight_class(fight_data['weight_class'])
            
            # Determine winner from enhanced scraper data
            winner = None
            if fight_data.get('winner'):
                winner = self._find_fighter_by_name(fight_data['winner'], fighters)
            elif fight_data.get('fighters'):
                # Fallback to fighters array if winner not directly specified
                for fighter_data in fight_data['fighters']:
                    if fighter_data.get('result') == 'win':
                        winner = self._find_fighter_by_name(fighter_data['name'], fighters)
                        break
            
            # Use scheduled_rounds from enhanced scraper data
            scheduled_rounds = fight_data.get('scheduled_rounds', 5 if fight_data.get('is_title_fight') or fight_data.get('is_main_event') else 3)
            
            fight = Fight.objects.create(
                event=event,
                weight_class=weight_class,
                fight_order=fight_data.get('fight_order', 1),
                is_main_event=fight_data.get('is_main_event', False),
                is_title_fight=fight_data.get('is_title_fight', False),
                scheduled_rounds=scheduled_rounds,
                status='completed',
                winner=winner,
                method=fight_data.get('method', ''),
                method_details=fight_data.get('method_details', ''),
                ending_round=fight_data.get('ending_round'),
                ending_time=fight_data.get('ending_time', '')
            )
            
            self.created_fights += 1
            return fight
            
        except Exception as e:
            logger.error(f"Error creating fight: {str(e)}")
            return None
    
    def _get_or_create_weight_class(self, weight_class_name: str) -> Optional[WeightClass]:
        """Get or create a weight class"""
        try:
            # Normalize weight class name
            normalized_name = weight_class_name.strip().title()
            
            weight_class, created = WeightClass.objects.get_or_create(
                name=normalized_name,
                defaults={
                    'weight_limit_kg': self._get_weight_limit(normalized_name),
                    'is_active': True
                }
            )
            
            return weight_class
            
        except Exception as e:
            logger.warning(f"Error creating weight class {weight_class_name}: {str(e)}")
            return None
    
    def _get_weight_limit(self, weight_class_name: str) -> Optional[Decimal]:
        """Get weight limit for a weight class"""
        weight_limits = {
            'Heavyweight': Decimal('120.2'),  # 265 lbs
            'Light Heavyweight': Decimal('93.0'),  # 205 lbs
            'Middleweight': Decimal('83.9'),  # 185 lbs
            'Welterweight': Decimal('77.1'),  # 170 lbs
            'Lightweight': Decimal('70.3'),  # 155 lbs
            'Featherweight': Decimal('65.8'),  # 145 lbs
            'Bantamweight': Decimal('61.2'),  # 135 lbs
            'Flyweight': Decimal('56.7'),  # 125 lbs
            "Women's Strawweight": Decimal('52.2'),  # 115 lbs
            "Women's Flyweight": Decimal('56.7'),  # 125 lbs
            "Women's Bantamweight": Decimal('61.2'),  # 135 lbs
            "Women's Featherweight": Decimal('65.8'),  # 145 lbs
        }
        
        return weight_limits.get(weight_class_name)
    
    def _create_fight_participants(self, fight: Fight, fight_data: Dict, fighters: List[Fighter]):
        """Create FightParticipant records"""
        if not fight_data.get('fighters'):
            return
        
        for fighter_data in fight_data['fighters']:
            fighter = self._find_fighter_by_name(fighter_data['name'], fighters)
            if fighter:
                try:
                    FightParticipant.objects.create(
                        fight=fight,
                        fighter=fighter,
                        corner=fighter_data.get('corner', 'red'),
                        result=fighter_data.get('result', '')
                    )
                    self.created_participants += 1
                except Exception as e:
                    logger.warning(f"Error creating participant for {fighter.get_full_name()}: {str(e)}")
    
    def _find_fighter_by_name(self, name: str, fighters: List[Fighter]) -> Optional[Fighter]:
        """Find a fighter by name from the provided list"""
        if not name:
            return None
        
        # Use cache to avoid repeated searches
        if name in self.processed_fighters:
            return self.processed_fighters[name]
        
        # Try exact matches first
        for fighter in fighters:
            if (fighter.display_name and fighter.display_name.lower() == name.lower()) or \
               f"{fighter.first_name} {fighter.last_name}".strip().lower() == name.lower():
                self.processed_fighters[name] = fighter
                return fighter
        
        # Try partial matches
        name_parts = name.lower().split()
        for fighter in fighters:
            fighter_full_name = f"{fighter.first_name} {fighter.last_name}".lower()
            if all(part in fighter_full_name for part in name_parts):
                self.processed_fighters[name] = fighter
                return fighter
        
        self.processed_fighters[name] = None
        return None
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            'created_events': self.created_events,
            'updated_events': self.updated_events,
            'created_fights': self.created_fights,
            'created_participants': self.created_participants,
            'total_events': self.created_events + self.updated_events
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.created_events = 0
        self.updated_events = 0
        self.created_fights = 0
        self.created_participants = 0
        self.processed_fighters.clear()