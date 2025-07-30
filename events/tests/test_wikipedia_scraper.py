"""
Comprehensive Test Suite for UFC Wikipedia Scraper
==================================================

Tests all components of the Wikipedia scraper system including
API integration, data extraction, fighter creation, and error handling.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from django.test import TestCase, TransactionTestCase
from django.db import transaction

from events.scrapers.wikipedia_base import WikipediaUFCScraper, WikipediaAPIError
from events.scrapers.fighter_extractor import FighterExtractor, FighterExtractionError
from events.scrapers.event_processor import EventProcessor, EventProcessingError
from events.scrapers.wikipedia_ufc_scraper import WikipediaUFCScraperComplete
from events.scrapers.error_handling import ErrorCollector, SafeOperationContext

from events.models import Event, Fight, FightParticipant
from fighters.models import Fighter, FighterNameVariation
from organizations.models import Organization, WeightClass


class MockHTMLContent:
    """Mock HTML content for testing"""
    
    UFC_EVENTS_LIST_HTML = """
    <table class="wikitable">
        <tr>
            <th>Event</th>
            <th>Date</th>
            <th>Venue</th>
            <th>Location</th>
            <th>Attendance</th>
        </tr>
        <tr>
            <td><a href="/wiki/UFC_300">UFC 300</a></td>
            <td>April 13, 2024</td>
            <td>T-Mobile Arena</td>
            <td>Las Vegas, Nevada, United States</td>
            <td>17,845 $16.5 million</td>
        </tr>
        <tr>
            <td><a href="/wiki/UFC_299">UFC 299</a></td>
            <td>March 9, 2024</td>
            <td>Kaseya Center</td>
            <td>Miami, Florida, United States</td>
            <td>15,112 $8.2 million</td>
        </tr>
    </table>
    """
    
    UFC_EVENT_DETAIL_HTML = """
    <table class="infobox">
        <tr>
            <th>Date</th>
            <td>April 13, 2024</td>
        </tr>
        <tr>
            <th>Venue</th>
            <td>T-Mobile Arena</td>
        </tr>
        <tr>
            <th>City</th>
            <td>Las Vegas, Nevada</td>
        </tr>
    </table>
    
    <table class="toccolours">
        <tr>
            <th colspan="5">Main card</th>
        </tr>
        <tr>
            <td>Light Heavyweight</td>
            <td>Alex Pereira def. Jamahal Hill</td>
            <td>KO (left hook)</td>
            <td>1</td>
            <td>3:19</td>
        </tr>
        <tr>
            <td>Women's Strawweight</td>
            <td>Zhang Weili def. Yan Xiaonan</td>
            <td>Submission (rear naked choke)</td>
            <td>1</td>
            <td>4:32</td>
        </tr>
    </table>
    """
    
    FIGHTER_PAGE_HTML = """
    <table class="infobox">
        <tr>
            <th>Born</th>
            <td>July 7, 1987 (age 36)<br>São Bernardo do Campo, Brazil</td>
        </tr>
        <tr>
            <th>Nationality</th>
            <td>Brazilian</td>
        </tr>
        <tr>
            <th>Height</th>
            <td>6 ft 4 in (193 cm)</td>
        </tr>
        <tr>
            <th>Weight</th>
            <td>205 lb (93 kg)</td>
        </tr>
        <tr>
            <th>Reach</th>
            <td>79 in (201 cm)</td>
        </tr>
        <tr>
            <th>Stance</th>
            <td>Orthodox</td>
        </tr>
    </table>
    """


class WikipediaUFCScraperTest(TestCase):
    """Test Wikipedia base scraper functionality"""
    
    def setUp(self):
        self.scraper = WikipediaUFCScraper()
    
    @patch('events.scrapers.wikipedia_base.requests.Session.get')
    def test_make_api_request_success(self, mock_get):
        """Test successful API request"""
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'parse': {'text': 'test content'}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        params = {'action': 'parse', 'page': 'test'}
        result = self.scraper._make_api_request(params)
        
        self.assertIn('parse', result)
        self.assertEqual(result['parse']['text'], 'test content')
    
    @patch('events.scrapers.wikipedia_base.requests.Session.get')
    def test_make_api_request_with_retries(self, mock_get):
        """Test API request with retry logic"""
        
        # Mock first two calls to fail, third to succeed
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = {'parse': {'text': 'success'}}
        mock_response_success.raise_for_status.return_value = None
        
        mock_get.side_effect = [Exception("Network error"), Exception("Network error"), mock_response_success]
        
        params = {'action': 'parse', 'page': 'test'}
        result = self.scraper._make_api_request(params)
        
        self.assertEqual(result['parse']['text'], 'success')
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('events.scrapers.wikipedia_base.BeautifulSoup')
    @patch.object(WikipediaUFCScraper, '_make_api_request')
    def test_get_page_content(self, mock_api_request, mock_soup):
        """Test getting page content"""
        
        # Mock API response
        mock_api_request.return_value = {
            'parse': {
                'text': MockHTMLContent.UFC_EVENTS_LIST_HTML,
                'displaytitle': 'List of UFC events',
                'categories': []
            }
        }
        
        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance
        
        result = self.scraper.get_page_content('List_of_UFC_events')
        
        self.assertIsNotNone(result)
        self.assertIn('soup', result)
        mock_api_request.assert_called_once()
    
    def test_clean_text(self):
        """Test text cleaning functionality"""
        
        dirty_text = "UFC 300[1][2]  Extra   spaces\n\tTabs"
        clean_text = self.scraper._clean_text(dirty_text)
        
        self.assertEqual(clean_text, "UFC 300 Extra spaces Tabs")
    
    def test_parse_date(self):
        """Test date parsing"""
        
        test_cases = [
            ("April 13, 2024", "2024-04-13"),
            ("13 April 2024", "2024-04-13"),
            ("2024-04-13", "2024-04-13"),
            ("Invalid date", None)
        ]
        
        for date_text, expected in test_cases:
            result_str, result_obj = self.scraper._parse_date(date_text)
            if expected:
                self.assertEqual(result_str, expected)
                self.assertIsInstance(result_obj, date)
            else:
                self.assertIsNone(result_str)
                self.assertIsNone(result_obj)
    
    def test_extract_event_number(self):
        """Test event number extraction"""
        
        test_cases = [
            ("UFC 300", 300),
            ("UFC Fight Night 123", 123),
            ("UFC on ESPN 45", 45),
            ("Invalid event", None)
        ]
        
        for event_name, expected in test_cases:
            result = self.scraper._extract_event_number(event_name)
            self.assertEqual(result, expected)
    
    def test_parse_fighters_text(self):
        """Test fighter name parsing"""
        
        test_cases = [
            ("Alex Pereira def. Jamahal Hill", {
                'fighters': ['Alex Pereira', 'Jamahal Hill'],
                'winner': 'Alex Pereira',
                'loser': 'Jamahal Hill',
                'result_type': 'win'
            }),
            ("Zhang Weili vs Yan Xiaonan", {
                'fighters': ['Zhang Weili', 'Yan Xiaonan'],
                'winner': '',
                'loser': '',
                'result_type': 'scheduled'
            })
        ]
        
        for fighters_text, expected in test_cases:
            result = self.scraper._parse_fighters_text(fighters_text)
            self.assertEqual(result['fighters'], expected['fighters'])
            self.assertEqual(result['result_type'], expected['result_type'])


class FighterExtractorTest(TestCase):
    """Test fighter extraction functionality"""
    
    def setUp(self):
        self.scraper = Mock()
        self.extractor = FighterExtractor(self.scraper)
    
    def test_parse_fighter_name(self):
        """Test fighter name parsing"""
        
        test_cases = [
            ("Alex Pereira", {
                'first_name': 'Alex',
                'last_name': 'Pereira',
                'nickname': ''
            }),
            ('Jon "Bones" Jones', {
                'first_name': 'Jon',
                'last_name': 'Jones',
                'nickname': 'Bones'
            }),
            ("Shogun", {
                'first_name': 'Shogun',
                'last_name': '',
                'nickname': ''
            })
        ]
        
        for fighter_name, expected in test_cases:
            result = self.extractor._parse_fighter_name(fighter_name)
            self.assertEqual(result['first_name'], expected['first_name'])
            self.assertEqual(result['last_name'], expected['last_name'])
            self.assertEqual(result['nickname'], expected['nickname'])
    
    def test_clean_fighter_name(self):
        """Test fighter name cleaning"""
        
        test_cases = [
            ("[[Alex Pereira]]", "Alex Pereira"),
            ("Jon Jones[1][2]", "Jon Jones"),
            ("Anderson Silva (fighter)", "Anderson Silva"),
            ("José Aldo (Brazilian)", "José Aldo")
        ]
        
        for dirty_name, expected in test_cases:
            result = self.extractor._clean_fighter_name(dirty_name)
            self.assertEqual(result, expected)
    
    @patch.object(FighterExtractor, '_get_fighter_wikipedia_data')
    @patch.object(FighterExtractor, '_find_existing_fighter')
    @patch.object(FighterExtractor, '_create_fighter_record')
    def test_extract_and_create_fighter_new(self, mock_create, mock_find, mock_wiki):
        """Test creating new fighter"""
        
        # Mock no existing fighter found
        mock_find.return_value = None
        
        # Mock Wikipedia data
        mock_wiki.return_value = {
            'nationality': 'Brazilian',
            'height_cm': 193,
            'wikipedia_url': 'https://en.wikipedia.org/wiki/Alex_Pereira'
        }
        
        # Mock created fighter
        mock_fighter = Mock()
        mock_fighter.get_full_name.return_value = "Alex Pereira"
        mock_create.return_value = mock_fighter
        
        result = self.extractor.extract_and_create_fighter("Alex Pereira")
        
        self.assertEqual(result, mock_fighter)
        mock_create.assert_called_once()
    
    @patch.object(FighterExtractor, '_find_existing_fighter')
    def test_extract_and_create_fighter_existing(self, mock_find):
        """Test finding existing fighter"""
        
        # Mock existing fighter
        mock_fighter = Mock()
        mock_fighter.get_full_name.return_value = "Alex Pereira"
        mock_find.return_value = mock_fighter
        
        result = self.extractor.extract_and_create_fighter("Alex Pereira")
        
        self.assertEqual(result, mock_fighter)
    
    def test_parse_height(self):
        """Test height parsing"""
        
        test_cases = [
            ("6 ft 4 in (193 cm)", 193),
            ("193 cm", 193),
            ("6'4\"", 193),
            ("Invalid height", None)
        ]
        
        for height_text, expected in test_cases:
            result = self.extractor._parse_height(height_text)
            if expected:
                self.assertEqual(result, expected)
            else:
                self.assertIsNone(result)
    
    def test_parse_weight(self):
        """Test weight parsing"""
        
        test_cases = [
            ("205 lb (93 kg)", 93.0),
            ("93 kg", 93.0),
            ("205 lb", 92.99),  # Converted from pounds
            ("Invalid weight", None)
        ]
        
        for weight_text, expected in test_cases:
            result = self.extractor._parse_weight(weight_text)
            if expected:
                self.assertAlmostEqual(result, expected, places=1)
            else:
                self.assertIsNone(result)


class EventProcessorTest(TransactionTestCase):
    """Test event processing functionality"""
    
    def setUp(self):
        self.scraper = Mock()
        self.fighter_extractor = Mock()
        self.processor = EventProcessor(self.scraper, self.fighter_extractor)
        
        # Create test organization
        self.ufc_org = Organization.objects.create(
            name="Ultimate Fighting Championship",
            abbreviation="UFC"
        )
        
        # Mock fighter extractor
        self.fighter_extractor.get_or_create_ufc_organization.return_value = self.ufc_org
    
    def test_process_event_data(self):
        """Test event data processing"""
        
        event_data = {
            'event_name': 'UFC 300',
            'event_number': 300,
            'date': '2024-04-13',
            'venue': 'T-Mobile Arena',
            'city': 'Las Vegas',
            'state': 'Nevada',
            'country': 'United States',
            'attendance': 17845,
            'gate_revenue': 16500000
        }
        
        result = self.processor._process_event_data(event_data, self.ufc_org)
        
        self.assertEqual(result['name'], 'UFC 300')
        self.assertEqual(result['event_number'], 300)
        self.assertEqual(result['organization'], self.ufc_org)
        self.assertEqual(result['attendance'], 17845)
    
    def test_parse_event_date(self):
        """Test event date parsing"""
        
        test_cases = [
            ("2024-04-13", date(2024, 4, 13)),
            ("April 13, 2024", date(2024, 4, 13)),
            ("Invalid date", None)
        ]
        
        for date_str, expected in test_cases:
            result = self.processor._parse_event_date(date_str)
            self.assertEqual(result, expected)
    
    @patch.object(EventProcessor, '_process_fight_card')
    def test_process_event_creation(self, mock_process_fights):
        """Test event creation"""
        
        event_data = {
            'event_name': 'UFC Test Event',
            'date': '2024-04-13',
            'venue': 'Test Arena',
            'fights': []
        }
        
        event = self.processor.process_event(event_data)
        
        self.assertIsInstance(event, Event)
        self.assertEqual(event.name, 'UFC Test Event')
        self.assertEqual(event.organization, self.ufc_org)
        mock_process_fights.assert_called_once()
    
    def test_extract_fight_fighters(self):
        """Test fighter extraction from fight data"""
        
        fight_data = {
            'fighters': ['Alex Pereira', 'Jamahal Hill']
        }
        
        result = self.processor._extract_fight_fighters(fight_data)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Alex Pereira')
        self.assertEqual(result[1]['name'], 'Jamahal Hill')
    
    def test_normalize_weight_class_name(self):
        """Test weight class name normalization"""
        
        test_cases = [
            ("lightweight", "Lightweight"),
            ("women's bantamweight", "Women's Bantamweight"),
            ("Light Heavyweight", "Light Heavyweight")
        ]
        
        for input_name, expected in test_cases:
            result = self.processor._normalize_weight_class_name(input_name)
            self.assertEqual(result, expected)


class WikipediaUFCScraperCompleteTest(TestCase):
    """Test complete scraper integration"""
    
    def setUp(self):
        self.scraper = WikipediaUFCScraperComplete()
    
    @patch.object(WikipediaUFCScraper, 'get_ufc_events_list')
    @patch.object(EventProcessor, 'process_event')
    def test_scrape_all_ufc_events(self, mock_process, mock_get_events):
        """Test scraping all events"""
        
        # Mock events list
        mock_events = [
            {
                'event_name': 'UFC 300',
                'date': '2024-04-13',
                'date_obj': date(2024, 4, 13),
                'wiki_page_title': 'UFC_300'
            },
            {
                'event_name': 'UFC 299',
                'date': '2024-03-09',
                'date_obj': date(2024, 3, 9),
                'wiki_page_title': 'UFC_299'
            }
        ]
        mock_get_events.return_value = mock_events
        
        # Mock event processing
        mock_event = Mock()
        mock_event.name = "UFC 300"
        mock_process.return_value = mock_event
        
        result = self.scraper.scrape_all_ufc_events(limit=2)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['events_processed']), 2)
        self.assertEqual(mock_process.call_count, 2)
    
    def test_filter_events_list(self):
        """Test event filtering by date"""
        
        events_list = [
            {'event_name': 'UFC 300', 'date_obj': date(2024, 4, 13)},
            {'event_name': 'UFC 299', 'date_obj': date(2024, 3, 9)},
            {'event_name': 'UFC 298', 'date_obj': date(2024, 2, 17)}
        ]
        
        # Filter by start date
        filtered = self.scraper._filter_events_list(
            events_list, 
            start_date=date(2024, 3, 1)
        )
        
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]['event_name'], 'UFC 300')
        self.assertEqual(filtered[1]['event_name'], 'UFC 299')
    
    def test_resolve_event_identifier(self):
        """Test event identifier resolution"""
        
        # Test direct page title
        result = self.scraper._resolve_event_identifier('UFC_300')
        self.assertEqual(result, 'UFC_300')
        
        # Test with spaces
        result = self.scraper._resolve_event_identifier('UFC 300')
        self.assertEqual(result, 'UFC_300')


class ErrorHandlingTest(TestCase):
    """Test error handling functionality"""
    
    def test_error_collector(self):
        """Test error collection"""
        
        collector = ErrorCollector()
        
        # Add some errors
        collector.add_error(ValueError("Test error"), {'context': 'test'})
        collector.add_error(RuntimeError("Another error"), severity='critical')
        
        summary = collector.get_summary()
        
        self.assertEqual(summary['total_errors'], 2)
        self.assertTrue(summary['has_critical_errors'])
        self.assertIn('ValueError', summary['error_types'])
        self.assertIn('RuntimeError', summary['error_types'])
    
    def test_safe_operation_context_success(self):
        """Test safe operation context with success"""
        
        collector = ErrorCollector()
        
        with SafeOperationContext(
            "test operation",
            error_collector=collector,
            continue_on_error=True
        ) as ctx:
            # Simulate successful operation
            pass
        
        self.assertTrue(ctx.success)
        self.assertFalse(collector.has_errors())
    
    def test_safe_operation_context_with_error(self):
        """Test safe operation context with error"""
        
        collector = ErrorCollector()
        
        with SafeOperationContext(
            "test operation",
            error_collector=collector,
            continue_on_error=True
        ) as ctx:
            raise ValueError("Test error")
        
        self.assertFalse(ctx.success)
        self.assertTrue(collector.has_errors())
        self.assertEqual(collector.get_summary()['total_errors'], 1)


class IntegrationTest(TransactionTestCase):
    """Integration tests for the complete scraping workflow"""
    
    def setUp(self):
        # Create test organization
        self.ufc_org = Organization.objects.create(
            name="Ultimate Fighting Championship",
            abbreviation="UFC"
        )
        
        # Create test weight class
        self.weight_class = WeightClass.objects.create(
            organization=self.ufc_org,
            name="Light Heavyweight",
            weight_limit_lbs=205,
            weight_limit_kg=92.99
        )
    
    @patch('events.scrapers.wikipedia_base.requests.Session.get')
    @patch('events.scrapers.wikipedia_base.BeautifulSoup')
    def test_complete_scraping_workflow(self, mock_soup, mock_get):
        """Test complete scraping workflow with mocked data"""
        
        # Mock API responses
        mock_response = Mock()
        mock_response.json.return_value = {
            'parse': {
                'text': MockHTMLContent.UFC_EVENT_DETAIL_HTML,
                'displaytitle': 'UFC 300',
                'categories': []
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock BeautifulSoup parsing
        mock_soup_instance = Mock()
        
        # Mock infobox
        mock_infobox = Mock()
        mock_infobox.find_all.return_value = [
            Mock(**{
                'find_all.return_value': [
                    Mock(**{'get_text.return_value': 'Date'}),
                    Mock(**{'get_text.return_value': 'April 13, 2024'})
                ]
            })
        ]
        
        # Mock fight table
        mock_table = Mock()
        mock_table.get_text.return_value = "main card def. vs decision"
        mock_table.find_all.return_value = [
            Mock(**{  # Header row
                'find_all.return_value': []
            }),
            Mock(**{  # Fight row
                'find_all.return_value': [
                    Mock(**{'get_text.return_value': 'Light Heavyweight'}),
                    Mock(**{'get_text.return_value': 'Alex Pereira def. Jamahal Hill'}),
                    Mock(**{'get_text.return_value': 'KO (left hook)'}),
                    Mock(**{'get_text.return_value': '1'}),
                    Mock(**{'get_text.return_value': '3:19'})
                ]
            })
        ]
        
        mock_soup_instance.find.return_value = mock_infobox
        mock_soup_instance.find_all.return_value = [mock_table]
        mock_soup.return_value = mock_soup_instance
        
        # Initialize scraper
        scraper = WikipediaUFCScraperComplete()
        
        # Test event processing
        event_data = {
            'event_name': 'UFC 300',
            'date': '2024-04-13',
            'venue': 'T-Mobile Arena',
            'fights': [
                {
                    'weight_class': 'Light Heavyweight',
                    'fighters': ['Alex Pereira', 'Jamahal Hill'],
                    'winner': 'Alex Pereira',
                    'method_clean': 'ko',
                    'round': 1,
                    'time': '3:19'
                }
            ]
        }
        
        event = scraper.event_processor.process_event(event_data)
        
        # Verify event creation
        self.assertIsInstance(event, Event)
        self.assertEqual(event.name, 'UFC 300')
        
        # Verify fighters were created
        alex_pereira = Fighter.objects.filter(first_name='Alex', last_name='Pereira').first()
        jamahal_hill = Fighter.objects.filter(first_name='Jamahal', last_name='Hill').first()
        
        self.assertIsNotNone(alex_pereira)
        self.assertIsNotNone(jamahal_hill)
        
        # Verify fight creation
        fights = event.fights.all()
        self.assertEqual(fights.count(), 1)
        
        fight = fights.first()
        self.assertEqual(fight.participants.count(), 2)
        self.assertEqual(fight.winner, alex_pereira)


# Pytest fixtures and test configuration

@pytest.fixture
def mock_wikipedia_response():
    """Fixture providing mock Wikipedia API response"""
    
    return {
        'parse': {
            'text': MockHTMLContent.UFC_EVENTS_LIST_HTML,
            'displaytitle': 'List of UFC events',
            'categories': ['Mixed martial arts-related lists']
        }
    }


@pytest.fixture
def sample_event_data():
    """Fixture providing sample event data"""
    
    return {
        'event_name': 'UFC 300',
        'event_number': 300,
        'date': '2024-04-13',
        'venue': 'T-Mobile Arena',
        'location': 'Las Vegas, Nevada, United States',
        'attendance': 17845,
        'gate_revenue': 16500000,
        'fights': [
            {
                'weight_class': 'Light Heavyweight',
                'fighters': ['Alex Pereira', 'Jamahal Hill'],
                'winner': 'Alex Pereira',
                'method_clean': 'ko',
                'method_details': 'left hook',
                'round': 1,
                'time': '3:19'
            }
        ]
    }


@pytest.fixture
def ufc_organization(db):
    """Fixture providing UFC organization"""
    
    return Organization.objects.create(
        name="Ultimate Fighting Championship",
        abbreviation="UFC"
    )


# Performance tests

class PerformanceTest(TestCase):
    """Test scraper performance with larger datasets"""
    
    def test_batch_fighter_processing_performance(self):
        """Test performance of batch fighter processing"""
        
        import time
        
        scraper = Mock()
        extractor = FighterExtractor(scraper)
        
        # Mock Wikipedia data fetching to return quickly
        extractor._get_fighter_wikipedia_data = Mock(return_value={})
        extractor._find_existing_fighter = Mock(return_value=None)
        extractor._create_fighter_record = Mock(return_value=Mock())
        extractor._create_name_variations = Mock()
        
        # Test with 50 fighters
        fighter_names = [f"Fighter {i}" for i in range(50)]
        
        start_time = time.time()
        fighters = extractor.batch_extract_fighters(fighter_names)
        end_time = time.time()
        
        # Should process 50 fighters in reasonable time (< 1 second for mocked operations)
        processing_time = end_time - start_time
        self.assertLess(processing_time, 1.0)
        self.assertEqual(len(fighters), 50)


# Test runner configuration

if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    # Configure Django settings for testing
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'events',
                'fighters',
                'organizations',
                'users',
            ],
            SECRET_KEY='test-secret-key'
        )
    
    django.setup()
    
    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["events.tests.test_wikipedia_scraper"])
    
    if failures:
        exit(1)