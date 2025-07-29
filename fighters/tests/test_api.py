import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from fighters.models import Fighter, FighterNameVariation
from decimal import Decimal
import json


class FighterAPITest(TestCase):
    """Test Fighter API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user for authentication (if needed)
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create sample fighters
        self.fighter1 = Fighter.objects.create(
            first_name='Jon',
            last_name='Jones',
            nickname='Bones',
            nationality='USA',
            height_cm=193,
            weight_kg=Decimal('93.5'),
            wins=26,
            losses=1,
            draws=0,
            stance='orthodox'
        )
        
        self.fighter2 = Fighter.objects.create(
            first_name='Conor',
            last_name='McGregor',
            nickname='The Notorious',
            nationality='Ireland',
            height_cm=175,
            weight_kg=Decimal('70.0'),
            wins=22,
            losses=6,
            draws=0,
            stance='southpaw'
        )
        
        # Single-name fighter
        self.fighter3 = Fighter.objects.create(
            first_name='Shogun',
            last_name='',
            nickname='Shogun',
            nationality='Brazil',
            wins=26,
            losses=11
        )
        
        # Create name variations for testing search
        FighterNameVariation.objects.create(
            fighter=self.fighter2,
            first_name_variation='Connor',
            last_name_variation='McGregor',
            variation_type='alternative',
            source='manual_entry'
        )
    
    def test_fighter_list_endpoint(self):
        """Test GET /api/v1/fighters/"""
        url = reverse('fighter-list')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check pagination structure
        assert 'results' in data
        assert 'count' in data
        assert len(data['results']) == 3  # Our 3 test fighters
        
        # Check fighter data structure
        fighter_data = data['results'][0]
        expected_fields = [
            'id', 'first_name', 'last_name', 'full_name', 'nickname',
            'nationality', 'record', 'finish_rate', 'is_active'
        ]
        for field in expected_fields:
            assert field in fighter_data
    
    def test_fighter_detail_endpoint(self):
        """Test GET /api/v1/fighters/{id}/"""
        url = reverse('fighter-detail', kwargs={'pk': self.fighter1.pk})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check detailed fields
        assert data['first_name'] == 'Jon'
        assert data['last_name'] == 'Jones'
        assert data['full_name'] == 'Jon Jones'
        assert data['nickname'] == 'Bones'
        assert data['nationality'] == 'USA'
        assert data['height_cm'] == 193
        assert float(data['weight_kg']) == 93.5
        assert data['wins'] == 26
        assert data['losses'] == 1
        assert data['record'] == '26-1-0'
        
        # Check computed fields
        assert 'finish_rate' in data
        assert 'name_variations' in data
    
    def test_fighter_create_endpoint(self):
        """Test POST /api/v1/fighters/"""
        url = reverse('fighter-list')
        
        new_fighter_data = {
            'first_name': 'Test',
            'last_name': 'Fighter',
            'nickname': 'The Test',
            'nationality': 'USA',
            'height_cm': 180,
            'weight_kg': '80.5',
            'stance': 'orthodox'
        }
        
        response = self.client.post(url, new_fighter_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Check created fighter
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'Fighter'
        assert data['nickname'] == 'The Test'
        
        # Verify in database
        created_fighter = Fighter.objects.get(pk=data['id'])
        assert created_fighter.get_full_name() == 'Test Fighter'
    
    def test_fighter_update_endpoint(self):
        """Test PUT/PATCH /api/v1/fighters/{id}/"""
        url = reverse('fighter-detail', kwargs={'pk': self.fighter1.pk})
        
        update_data = {
            'nickname': 'Bones Updated',
            'wins': 27
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify update in database
        self.fighter1.refresh_from_db()
        assert self.fighter1.nickname == 'Bones Updated'
        # Note: wins is read-only in the update serializer, so it shouldn't change
    
    def test_fighter_search_endpoint(self):
        """Test GET /api/v1/fighters/search/?q={query}"""
        url = reverse('fighter-search')
        
        # Test exact name match
        response = self.client.get(url, {'q': 'Jon Jones'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['count'] >= 1
        assert data['query'] == 'Jon Jones'
        assert 'search_strategies_used' in data
        assert 'max_confidence' in data
        
        # Verify Jon Jones is in results
        jon_jones = next(
            (r for r in data['results'] if r['first_name'] == 'Jon'), 
            None
        )
        assert jon_jones is not None
        assert jon_jones['match_type'] in ['exact', 'fulltext', 'partial']
    
    def test_fighter_search_single_name(self):
        """Test search for single-name fighter"""
        url = reverse('fighter-search')
        
        response = self.client.get(url, {'q': 'Shogun'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['count'] >= 1
        shogun = next(
            (r for r in data['results'] if r['first_name'] == 'Shogun'),
            None
        )
        assert shogun is not None
        assert shogun['last_name'] == ''
    
    def test_fighter_search_nickname(self):
        """Test search by nickname"""
        url = reverse('fighter-search')
        
        response = self.client.get(url, {'q': 'Bones'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['count'] >= 1
        bones = next(
            (r for r in data['results'] if r['nickname'] == 'Bones'),
            None
        )
        assert bones is not None
        assert bones['first_name'] == 'Jon'
    
    def test_fighter_search_name_variation(self):
        """Test search using name variations"""
        url = reverse('fighter-search')
        
        # Search for "Connor" which is a variation of "Conor"
        response = self.client.get(url, {'q': 'Connor McGregor'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should find Conor McGregor through name variation
        conor = next(
            (r for r in data['results'] if r['first_name'] == 'Conor'),
            None
        )
        assert conor is not None
        assert conor['match_type'] in ['variation', 'fuzzy', 'partial']
    
    def test_fighter_search_partial_name(self):
        """Test partial name matching"""
        url = reverse('fighter-search')
        
        # Search with "Last First" format
        response = self.client.get(url, {'q': 'Jones Jon'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should find Jon Jones
        jon = next(
            (r for r in data['results'] if r['first_name'] == 'Jon'),
            None
        )
        assert jon is not None
    
    def test_fighter_search_empty_query(self):
        """Test search with empty query"""
        url = reverse('fighter-search')
        
        response = self.client.get(url, {'q': ''})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data['count'] == 0
        assert data['results'] == []
        assert data['query'] == ''
    
    def test_fighter_filtering(self):
        """Test fighter filtering by various fields"""
        url = reverse('fighter-list')
        
        # Filter by nationality
        response = self.client.get(url, {'nationality': 'USA'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return Jon Jones (USA)
        assert data['count'] == 1
        assert data['results'][0]['first_name'] == 'Jon'
        
        # Filter by stance
        response = self.client.get(url, {'stance': 'southpaw'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return Conor McGregor
        assert data['count'] == 1
        conor = data['results'][0]
        assert conor['first_name'] == 'Conor'
    
    def test_fighter_ordering(self):
        """Test fighter ordering"""
        url = reverse('fighter-list')
        
        # Test ordering by last name
        response = self.client.get(url, {'ordering': 'last_name'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should be ordered: "" (Shogun), Jones, McGregor
        results = data['results']
        assert results[0]['last_name'] == ''  # Shogun first
        assert results[1]['last_name'] == 'Jones'
        assert results[2]['last_name'] == 'McGregor'
        
        # Test reverse ordering
        response = self.client.get(url, {'ordering': '-wins'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should be ordered by wins descending
        wins = [r['wins'] for r in data['results']]
        assert wins == sorted(wins, reverse=True)
    
    def test_fighter_statistics_endpoint(self):
        """Test GET /api/v1/fighters/{id}/statistics/"""
        url = reverse('fighter-statistics', kwargs={'pk': self.fighter1.pk})
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check statistics structure
        assert 'career_record' in data
        assert 'win_methods' in data
        assert 'finish_rate' in data
        assert 'activity' in data
        
        # Check career record
        career = data['career_record']
        assert career['wins'] == 26
        assert career['losses'] == 1
        assert career['draws'] == 0
    
    def test_active_fighters_endpoint(self):
        """Test GET /api/v1/fighters/active/"""
        # Mark one fighter as inactive
        self.fighter3.is_active = False
        self.fighter3.save()
        
        url = reverse('fighter-active')
        response = self.client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only return active fighters (2 out of 3)
        assert data['count'] == 2
        for fighter in data['results']:
            assert fighter['is_active'] is True
    
    def test_fighter_validation_errors(self):
        """Test validation errors in fighter creation"""
        url = reverse('fighter-list')
        
        # Test missing required field
        invalid_data = {
            'last_name': 'Fighter',  # Missing first_name
            'nationality': 'USA'
        }
        
        response = self.client.post(url, invalid_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test invalid height
        invalid_data = {
            'first_name': 'Test',
            'last_name': 'Fighter',
            'height_cm': 300  # Too tall
        }
        
        response = self.client.post(url, invalid_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'height_cm' in data
    
    def test_fighter_search_performance(self):
        """Test search performance with multiple strategies"""
        url = reverse('fighter-search')
        
        # Test complex query that should use multiple strategies
        response = self.client.get(url, {'q': 'Jon'})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have metadata about search strategies
        assert 'search_strategies_used' in data
        assert 'max_confidence' in data
        assert data['max_confidence'] > 0
        
        # Results should have match metadata
        if data['results']:
            result = data['results'][0]
            assert 'match_type' in result
            assert 'confidence' in result
            assert result['match_type'] in [
                'exact', 'variation', 'partial', 'fulltext', 'fuzzy'
            ]