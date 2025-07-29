import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from fighters.models import Fighter, FightHistory
from organizations.models import Organization, WeightClass


class WikipediaFightHistoryParser:
    """Parser for Wikipedia MMA record tables"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MMA Backend Data Import Tool (Educational Use)'
        })
    
    def fetch_wikipedia_page(self, url):
        """Fetch and parse Wikipedia page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html5lib')
        except requests.RequestException as e:
            raise CommandError(f"Failed to fetch Wikipedia page: {e}")
    
    def find_mma_record_table(self, soup):
        """Find the MMA record table on the page"""
        # Common patterns for MMA record tables
        table_patterns = [
            lambda t: t.name == 'table' and t.find('th', string=re.compile(r'Result|Res\.', re.I)),
            lambda t: t.name == 'table' and 'wikitable' in t.get('class', []),
            lambda t: t.name == 'table' and t.find('th', string=re.compile(r'Opponent', re.I)),
        ]
        
        for pattern in table_patterns:
            tables = soup.find_all(pattern)
            for table in tables:
                # Check if this looks like an MMA record table
                headers = [th.get_text().strip().lower() for th in table.find_all('th')]
                if any(header in ['result', 'res.', 'opponent', 'method', 'event', 'date'] for header in headers):
                    return table
        
        raise CommandError("Could not find MMA record table on Wikipedia page")
    
    def parse_record_table(self, table):
        """Parse the MMA record table into structured data"""
        headers = []
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text().strip().lower() for th in header_row.find_all(['th', 'td'])]
        
        # Map common header variations to standard field names
        header_mapping = {
            'result': 'result',
            'res.': 'result',
            'res': 'result',
            'record': 'fighter_record_at_time',
            'opponent': 'opponent_full_name',
            'method': 'method',
            'event': 'event_name',
            'date': 'event_date',
            'round': 'ending_round',
            'time': 'ending_time',
            'location': 'location',
            'notes': 'notes',
            'ref.': 'notes',
            'weight': 'weight_class_name',
        }
        
        fights = []
        fight_order = 1
        
        # Skip header row and parse data rows
        for row in table.find_all('tr')[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:  # Skip rows with too few cells
                continue
            
            fight_data = {'fight_order': fight_order}
            
            # Map cell data to fields based on headers
            for i, cell in enumerate(cells):
                if i < len(headers):
                    header = headers[i]
                    mapped_field = header_mapping.get(header)
                    
                    if mapped_field:
                        cell_text = cell.get_text().strip()
                        
                        # Clean and parse cell data
                        if mapped_field == 'result':
                            fight_data[mapped_field] = self.parse_result(cell_text)
                        elif mapped_field == 'method':
                            fight_data[mapped_field] = self.parse_method(cell_text)
                        elif mapped_field == 'event_date':
                            fight_data[mapped_field] = self.parse_date(cell_text)
                        elif mapped_field == 'opponent_full_name':
                            fight_data.update(self.parse_opponent_name(cell_text))
                        elif mapped_field == 'ending_round':
                            fight_data[mapped_field] = self.parse_round(cell_text)
                        elif mapped_field == 'ending_time':
                            fight_data[mapped_field] = self.parse_time(cell_text)
                        else:
                            fight_data[mapped_field] = cell_text[:255] if cell_text else ''
            
            # Only add fights with essential data
            if fight_data.get('result') and fight_data.get('opponent_full_name'):
                fights.append(fight_data)
                fight_order += 1
        
        return fights
    
    def parse_result(self, result_text):
        """Parse result text to standard format"""
        result_text = result_text.lower().strip()
        if result_text in ['win', 'w']:
            return 'win'
        elif result_text in ['loss', 'l']:
            return 'loss'
        elif result_text in ['draw', 'd']:
            return 'draw'
        elif result_text in ['nc', 'no contest']:
            return 'no_contest'
        return ''
    
    def parse_method(self, method_text):
        """Parse method text to standard format"""
        method_text = method_text.lower().strip()
        
        # Map common Wikipedia method descriptions to our choices
        method_mapping = {
            'ko': 'ko',
            'knockout': 'ko',
            'tko': 'tko',
            'technical knockout': 'tko',
            'submission': 'submission',
            'sub': 'submission',
            'decision': 'decision_unanimous',
            'unanimous decision': 'decision_unanimous',
            'majority decision': 'decision_majority',
            'split decision': 'decision_split',
            'disqualification': 'disqualification',
            'dq': 'disqualification',
            'no contest': 'no_contest',
        }
        
        # Check for specific submission types
        if 'rear naked choke' in method_text or 'rnc' in method_text:
            return 'submission_rear_naked_choke'
        elif 'guillotine' in method_text:
            return 'submission_guillotine'
        elif 'triangle' in method_text:
            return 'submission_triangle'
        elif 'armbar' in method_text:
            return 'submission_armbar'
        elif 'kimura' in method_text:
            return 'submission_kimura'
        
        # Check for TKO variations
        if 'tko' in method_text and 'punches' in method_text:
            return 'tko_punches'
        elif 'tko' in method_text and ('doctor' in method_text or 'medical' in method_text):
            return 'tko_doctor_stoppage'
        
        # Use mapping for common terms
        for key, value in method_mapping.items():
            if key in method_text:
                return value
        
        return 'other'
    
    def parse_date(self, date_text):
        """Parse date text to datetime object"""
        date_text = date_text.strip()
        
        # Common date formats in Wikipedia
        date_formats = [
            '%B %d, %Y',     # January 1, 2023
            '%b %d, %Y',     # Jan 1, 2023
            '%Y-%m-%d',      # 2023-01-01
            '%d %B %Y',      # 1 January 2023
            '%d %b %Y',      # 1 Jan 2023
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(date_text, date_format).date()
            except ValueError:
                continue
        
        return None
    
    def parse_opponent_name(self, opponent_text):
        """Parse opponent name into structured format"""
        opponent_text = opponent_text.strip()
        
        # Remove common formatting and references
        opponent_text = re.sub(r'\\[\\d+\\]', '', opponent_text)  # Remove [1], [2] references
        opponent_text = re.sub(r'\\(.*?\\)', '', opponent_text)   # Remove parentheses content
        
        # Split name into parts
        name_parts = opponent_text.split()
        
        if len(name_parts) >= 2:
            return {
                'opponent_first_name': name_parts[0],
                'opponent_last_name': ' '.join(name_parts[1:]),
                'opponent_full_name': opponent_text
            }
        else:
            return {
                'opponent_first_name': opponent_text,
                'opponent_last_name': '',
                'opponent_full_name': opponent_text
            }
    
    def parse_round(self, round_text):
        """Parse round text to integer"""
        round_text = round_text.strip()
        match = re.search(r'(\\d+)', round_text)
        if match:
            return int(match.group(1))
        return None
    
    def parse_time(self, time_text):
        """Parse time text to MM:SS format"""
        time_text = time_text.strip()
        # Match MM:SS format
        match = re.search(r'(\\d{1,2}:\\d{2})', time_text)
        if match:
            return match.group(1)
        return ''


class Command(BaseCommand):
    help = 'Import fight history from Wikipedia MMA record pages'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fighter-url',
            type=str,
            help='Wikipedia URL of the fighter page'
        )
        parser.add_argument(
            '--fighter-name',
            type=str,
            help='Fighter name to search for in database'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate data without saving to database'
        )
        parser.add_argument(
            '--bulk-import',
            type=str,
            help='JSON file with multiple fighter URLs for bulk import'
        )
    
    def handle(self, *args, **options):
        parser = WikipediaFightHistoryParser()
        
        if options['bulk_import']:
            self.handle_bulk_import(options['bulk_import'], parser, options['dry_run'])
        elif options['fighter_url']:
            self.handle_single_import(
                options['fighter_url'], 
                options.get('fighter_name'), 
                parser, 
                options['dry_run']
            )
        else:
            raise CommandError('Must specify --fighter-url or --bulk-import')
    
    def handle_single_import(self, fighter_url, fighter_name, parser, dry_run):
        """Handle import for a single fighter"""
        self.stdout.write(f'Importing fight history from: {fighter_url}')
        
        # Find or create fighter
        fighter = self.get_or_create_fighter(fighter_name, fighter_url)
        
        # Parse Wikipedia page
        soup = parser.fetch_wikipedia_page(fighter_url)
        table = parser.find_mma_record_table(soup)
        fights = parser.parse_record_table(table)
        
        if dry_run:
            self.stdout.write(f'DRY RUN: Would import {len(fights)} fights for {fighter.get_full_name()}')
            for fight in fights[:5]:  # Show first 5 fights as preview
                self.stdout.write(f'  - Fight {fight["fight_order"]}: {fight.get("result", "N/A")} vs {fight.get("opponent_full_name", "N/A")}')
            return
        
        # Import fights
        self.import_fights(fighter, fights, fighter_url)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {len(fights)} fights for {fighter.get_full_name()}')
        )
    
    def handle_bulk_import(self, bulk_file, parser, dry_run):
        """Handle bulk import from JSON file"""
        import json
        
        try:
            with open(bulk_file, 'r') as f:
                fighters_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise CommandError(f'Error reading bulk import file: {e}')
        
        for fighter_data in fighters_data:
            fighter_url = fighter_data.get('url')
            fighter_name = fighter_data.get('name')
            
            if not fighter_url:
                self.stdout.write(f'Skipping entry without URL: {fighter_data}')
                continue
            
            try:
                self.handle_single_import(fighter_url, fighter_name, parser, dry_run)
            except Exception as e:
                self.stdout.write(f'Error importing {fighter_name}: {e}')
                continue
    
    def get_or_create_fighter(self, fighter_name, wikipedia_url):
        """Get existing fighter or create new one"""
        if fighter_name:
            # Try to find existing fighter by name
            name_parts = fighter_name.split()
            if len(name_parts) >= 2:
                fighters = Fighter.objects.filter(
                    first_name__iexact=name_parts[0],
                    last_name__iexact=' '.join(name_parts[1:])
                )
                if fighters.exists():
                    fighter = fighters.first()
                    # Update Wikipedia URL if not set
                    if not fighter.wikipedia_url:
                        fighter.wikipedia_url = wikipedia_url
                        fighter.save()
                    return fighter
        
        # Extract fighter name from Wikipedia URL if not provided
        if not fighter_name:
            url_parts = wikipedia_url.split('/')
            fighter_name = url_parts[-1].replace('_', ' ')
            
            # Remove common Wikipedia URL patterns
            fighter_name = re.sub(r'\\(.*?\\)', '', fighter_name).strip()
        
        # Create new fighter
        name_parts = fighter_name.split()
        fighter_data = {
            'first_name': name_parts[0] if name_parts else 'Unknown',
            'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
            'wikipedia_url': wikipedia_url,
            'data_source': 'wikipedia',
        }
        
        fighter = Fighter.objects.create(**fighter_data)
        self.stdout.write(f'Created new fighter: {fighter.get_full_name()}')
        return fighter
    
    def import_fights(self, fighter, fights_data, source_url):
        """Import fight history for a fighter"""
        # Clear existing Wikipedia-sourced fight history
        FightHistory.objects.filter(
            fighter=fighter,
            data_source='wikipedia'
        ).delete()
        
        fight_objects = []
        
        for fight_data in fights_data:
            # Add common fields
            fight_data.update({
                'fighter': fighter,
                'data_source': 'wikipedia',
                'source_url': source_url,
                'parsed_data': fight_data.copy(),  # Store original parsed data
            })
            
            # Try to link to existing opponents
            opponent_name = fight_data.get('opponent_full_name', '')
            if opponent_name:
                opponent_fighter = self.find_opponent_fighter(
                    fight_data.get('opponent_first_name', ''),
                    fight_data.get('opponent_last_name', '')
                )
                if opponent_fighter:
                    fight_data['opponent_fighter'] = opponent_fighter
            
            # Create FightHistory object
            fight_objects.append(FightHistory(**fight_data))
        
        # Bulk create all fights
        with transaction.atomic():
            FightHistory.objects.bulk_create(fight_objects, batch_size=100)
        
        self.stdout.write(f'Imported {len(fight_objects)} fights')
    
    def find_opponent_fighter(self, first_name, last_name):
        """Try to find existing Fighter record for opponent"""
        if not first_name:
            return None
        
        fighters = Fighter.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name or ''
        )
        
        if fighters.count() == 1:
            return fighters.first()
        
        return None