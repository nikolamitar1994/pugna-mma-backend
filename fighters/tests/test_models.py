import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from fighters.models import Fighter, FighterNameVariation
from decimal import Decimal


class FighterModelTest(TestCase):
    """Test Fighter model functionality and validation"""
    
    def setUp(self):
        """Set up test data"""
        self.fighter_data = {
            'first_name': 'Jon',
            'last_name': 'Jones',
            'nickname': 'Bones',
            'nationality': 'USA',
            'height_cm': 193,
            'weight_kg': Decimal('93.5'),
            'reach_cm': 215,
            'stance': 'orthodox',
            'wins': 26,
            'losses': 1,
            'draws': 0,
            'no_contests': 0
        }
    
    def test_fighter_creation_with_structured_names(self):
        """Test creating fighter with proper name structure"""
        fighter = Fighter.objects.create(**self.fighter_data)
        
        assert fighter.first_name == 'Jon'
        assert fighter.last_name == 'Jones'
        assert fighter.get_full_name() == 'Jon Jones'
        assert fighter.nickname == 'Bones'
        assert str(fighter) == 'Jon Jones'
    
    def test_single_name_fighter(self):
        """Test single-name fighter (Brazilian style)"""
        fighter_data = {
            'first_name': 'Shogun',
            'last_name': '',
            'nickname': 'Shogun',
            'nationality': 'Brazil'
        }
        fighter = Fighter.objects.create(**fighter_data)
        
        assert fighter.first_name == 'Shogun'
        assert fighter.last_name == ''
        assert fighter.get_full_name() == 'Shogun'
        assert str(fighter) == 'Shogun'
    
    def test_display_name_auto_generation(self):
        """Test automatic display_name generation"""
        fighter = Fighter.objects.create(**self.fighter_data)
        assert fighter.display_name == 'Jon Jones'
        
        # Test custom display name
        custom_fighter = Fighter.objects.create(
            first_name='Conor',
            last_name='McGregor',
            display_name='The Notorious Conor McGregor'
        )
        assert custom_fighter.get_display_name() == 'The Notorious Conor McGregor'
    
    def test_record_string_generation(self):
        """Test fight record string formatting"""
        fighter = Fighter.objects.create(**self.fighter_data)
        assert fighter.get_record_string() == '26-1-0'
        
        # Test with no contests
        fighter.no_contests = 1
        fighter.save()
        assert fighter.get_record_string() == '26-1-0 (1 NC)'
    
    def test_finish_rate_calculation(self):
        """Test finish rate calculation"""
        fighter_data = {
            'first_name': 'Test',
            'last_name': 'Fighter',
            'wins': 10,
            'wins_by_ko': 5,
            'wins_by_tko': 2,
            'wins_by_submission': 1,
            'wins_by_decision': 2
        }
        fighter = Fighter.objects.create(**fighter_data)
        
        # (5 KO + 2 TKO + 1 Sub) / 10 wins = 80%
        assert fighter.get_finish_rate() == 80.0
        
        # Test zero wins
        no_wins_fighter = Fighter.objects.create(
            first_name='No', last_name='Wins', wins=0
        )
        assert no_wins_fighter.get_finish_rate() == 0.0
    
    def test_physical_attribute_validation(self):
        """Test validation of physical attributes"""
        # Test invalid height
        with pytest.raises(ValidationError):
            fighter = Fighter(**self.fighter_data)
            fighter.height_cm = 300  # Too tall
            fighter.full_clean()
        
        # Test invalid weight
        with pytest.raises(ValidationError):
            fighter = Fighter(**self.fighter_data)
            fighter.weight_kg = Decimal('300')  # Too heavy
            fighter.full_clean()
        
        # Test valid ranges
        fighter = Fighter(**self.fighter_data)
        fighter.height_cm = 180
        fighter.weight_kg = Decimal('80.5')
        fighter.full_clean()  # Should not raise
    
    def test_data_quality_score_validation(self):
        """Test data quality score validation"""
        fighter_data = self.fighter_data.copy()
        
        # Test invalid score (too high)
        with pytest.raises(ValidationError):
            fighter = Fighter(**fighter_data)
            fighter.data_quality_score = Decimal('1.5')
            fighter.full_clean()
        
        # Test invalid score (negative)
        with pytest.raises(ValidationError):
            fighter = Fighter(**fighter_data)
            fighter.data_quality_score = Decimal('-0.1')
            fighter.full_clean()
        
        # Test valid score
        fighter = Fighter(**fighter_data)
        fighter.data_quality_score = Decimal('0.85')
        fighter.full_clean()  # Should not raise
    
    def test_stance_choices_validation(self):
        """Test stance field validation"""
        # Valid stance
        fighter = Fighter.objects.create(
            first_name='Test',
            last_name='Fighter',
            stance='orthodox'
        )
        assert fighter.stance == 'orthodox'
        
        # Invalid stance should be caught at model validation
        with pytest.raises(ValidationError):
            fighter = Fighter(
                first_name='Test',
                last_name='Fighter',
                stance='invalid_stance'
            )
            fighter.full_clean()
    
    def test_social_media_json_field(self):
        """Test social media JSON field functionality"""
        social_data = {
            'twitter': '@jonnybones',
            'instagram': '@jonnybones',
            'facebook': 'JonJonesMMA'
        }
        
        fighter = Fighter.objects.create(
            **self.fighter_data,
            social_media=social_data
        )
        
        assert fighter.social_media['twitter'] == '@jonnybones'
        assert fighter.social_media['instagram'] == '@jonnybones'
        assert len(fighter.social_media) == 3
    
    def test_search_vector_update(self):
        """Test search vector update functionality"""
        fighter = Fighter.objects.create(**self.fighter_data)
        
        # Search vector should be updated after save
        fighter.update_search_vector()
        
        # Verify fighter can be found via search
        # Note: This requires PostgreSQL for full testing
        # In SQLite, search_vector will be None
        
    def test_fighter_ordering(self):
        """Test default model ordering"""
        Fighter.objects.create(first_name='Alpha', last_name='Beta')
        Fighter.objects.create(first_name='Charlie', last_name='Alpha')
        Fighter.objects.create(first_name='Beta', last_name='Alpha')
        
        fighters = list(Fighter.objects.all())
        
        # Should be ordered by last_name, then first_name
        assert fighters[0].last_name == 'Alpha'
        assert fighters[0].first_name == 'Beta'  # Beta Alpha comes before Charlie Alpha
        assert fighters[1].first_name == 'Charlie'
        assert fighters[2].last_name == 'Beta'


class FighterNameVariationTest(TestCase):
    """Test FighterNameVariation model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.fighter = Fighter.objects.create(
            first_name='Conor',
            last_name='McGregor',
            nickname='The Notorious'
        )
    
    def test_name_variation_creation(self):
        """Test creating name variations"""
        variation = FighterNameVariation.objects.create(
            fighter=self.fighter,
            first_name_variation='Connor',
            last_name_variation='McGregor',
            variation_type='alternative',
            source='manual_entry'
        )
        
        assert variation.fighter == self.fighter
        assert variation.first_name_variation == 'Connor'
        assert variation.last_name_variation == 'McGregor'
        assert variation.full_name_variation == 'Connor McGregor'
        assert str(variation) == 'Conor McGregor → Connor McGregor'
    
    def test_single_name_variation(self):
        """Test variation for single-name fighter"""
        single_fighter = Fighter.objects.create(
            first_name='Shogun',
            last_name=''
        )
        
        variation = FighterNameVariation.objects.create(
            fighter=single_fighter,
            first_name_variation='Ricardo',
            last_name_variation='Arona',
            variation_type='alias'
        )
        
        assert variation.full_name_variation == 'Ricardo Arona'
    
    def test_auto_full_name_generation(self):
        """Test automatic full_name_variation generation"""
        # With both names
        variation = FighterNameVariation.objects.create(
            fighter=self.fighter,
            first_name_variation='Connor',
            last_name_variation='MacGregor'
        )
        assert variation.full_name_variation == 'Connor MacGregor'
        
        # With only first name
        nickname_variation = FighterNameVariation.objects.create(
            fighter=self.fighter,
            first_name_variation='Notorious',
            last_name_variation=''
        )
        assert nickname_variation.full_name_variation == 'Notorious'
    
    def test_variation_uniqueness(self):
        """Test unique constraint on fighter + full_name_variation"""
        FighterNameVariation.objects.create(
            fighter=self.fighter,
            full_name_variation='Connor McGregor'
        )
        
        # Creating duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            FighterNameVariation.objects.create(
                fighter=self.fighter,
                full_name_variation='Connor McGregor'
            )
    
    def test_variation_types(self):
        """Test different variation types"""
        variations = [
            ('alternative', 'Connor McGregor'),
            ('translation', 'Конор МакГрегор'),
            ('nickname', 'Notorious'),
            ('alias', 'The Notorious One')
        ]
        
        for var_type, name in variations:
            variation = FighterNameVariation.objects.create(
                fighter=self.fighter,
                full_name_variation=name,
                variation_type=var_type
            )
            assert variation.variation_type == var_type
    
    def test_related_name_access(self):
        """Test accessing variations through fighter"""
        FighterNameVariation.objects.create(
            fighter=self.fighter,
            full_name_variation='Connor McGregor',
            variation_type='alternative'
        )
        FighterNameVariation.objects.create(
            fighter=self.fighter,
            full_name_variation='Notorious',
            variation_type='nickname'
        )
        
        variations = self.fighter.name_variations.all()
        assert variations.count() == 2
        
        alternative_vars = self.fighter.name_variations.filter(
            variation_type='alternative'
        )
        assert alternative_vars.count() == 1
        assert alternative_vars.first().full_name_variation == 'Connor McGregor'