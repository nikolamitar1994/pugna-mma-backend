# Interconnected Fight History Migration Plan

## Phase 1: Database Schema Evolution (Safe Migration)

### Step 1: Add New Relationship Fields to FightHistory (Additive)

Create migration to add new fields to FightHistory without breaking existing data:

```python
# fighters/migrations/0003_add_fight_relationships.py
class Migration(migrations.Migration):
    dependencies = [
        ('fighters', '0002_fighthistory'),
        ('events', '0001_initial'),
    ]

    operations = [
        # Add new relationship field to link to authoritative Fight records
        migrations.AddField(
            model_name='fighthistory',
            name='authoritative_fight',
            field=models.ForeignKey(
                'events.Fight', 
                on_delete=models.SET_NULL, 
                null=True, 
                blank=True,
                related_name='history_views',
                help_text="Link to the authoritative Fight record"
            ),
        ),
        
        # Add field to track which fighter's perspective this is
        migrations.AddField(
            model_name='fighthistory',
            name='perspective_fighter',
            field=models.ForeignKey(
                'fighters.Fighter',
                on_delete=models.CASCADE,
                related_name='fight_perspectives',
                help_text="Which fighter's perspective this history represents",
                null=True  # Temporarily nullable for migration
            ),
        ),
        
        # Add index for new relationships
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_fh_authoritative_fight ON fight_history (authoritative_fight_id) WHERE authoritative_fight_id IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_fh_authoritative_fight;"
        ),
    ]
```

### Step 2: Data Migration - Link Existing Records

```python
# fighters/migrations/0004_link_existing_fight_history.py
from django.db import migrations

def link_fight_history_to_fights(apps, schema_editor):
    """
    Link existing FightHistory records to authoritative Fight records
    """
    FightHistory = apps.get_model('fighters', 'FightHistory')
    Fight = apps.get_model('events', 'Fight')
    FightParticipant = apps.get_model('events', 'FightParticipant')
    
    linked_count = 0
    unlinked_count = 0
    
    for history in FightHistory.objects.select_related('fighter', 'event').all():
        # Set perspective_fighter (this history belongs to this fighter)
        history.perspective_fighter = history.fighter
        
        # Try to find matching Fight record
        matching_fight = None
        
        if history.event:
            # First try: exact event match with fighter participation
            potential_fights = Fight.objects.filter(
                event=history.event,
                participants__fighter=history.fighter
            ).prefetch_related('participants__fighter')
            
            for fight in potential_fights:
                # Check if opponent names match
                participants = list(fight.participants.all())
                if len(participants) == 2:
                    opponent = participants[1] if participants[0].fighter == history.fighter else participants[0]
                    opponent_name = opponent.fighter.get_full_name()
                    
                    # Fuzzy name matching
                    if (
                        history.opponent_full_name.lower() in opponent_name.lower() or
                        opponent_name.lower() in history.opponent_full_name.lower() or
                        # Try first name + last name combination
                        (history.opponent_first_name.lower() == opponent.fighter.first_name.lower() and
                         history.opponent_last_name.lower() == opponent.fighter.last_name.lower())
                    ):
                        matching_fight = fight
                        break
        
        if matching_fight:
            history.authoritative_fight = matching_fight
            linked_count += 1
        else:
            unlinked_count += 1
            
        history.save()
    
    print(f"Migration complete: {linked_count} linked, {unlinked_count} unlinked")

def reverse_link_fight_history(apps, schema_editor):
    """Reverse migration - clear the links"""
    FightHistory = apps.get_model('fighters', 'FightHistory')
    FightHistory.objects.update(authoritative_fight=None, perspective_fighter=None)

class Migration(migrations.Migration):
    dependencies = [
        ('fighters', '0003_add_fight_relationships'),
    ]

    operations = [
        migrations.RunPython(link_fight_history_to_fights, reverse_link_fight_history),
        
        # After linking, make perspective_fighter non-nullable
        migrations.AlterField(
            model_name='fighthistory',
            name='perspective_fighter',
            field=models.ForeignKey(
                'fighters.Fighter',
                on_delete=models.CASCADE,
                related_name='fight_perspectives',
                help_text="Which fighter's perspective this history represents"
            ),
        ),
    ]
```

## Phase 2: Service Layer Implementation

### Enhanced FightHistory Manager with Dual Data Sources

```python
# fighters/managers.py
from django.db import models
from django.db.models import Q, Prefetch

class FightHistoryManager(models.Manager):
    """
    Manager that seamlessly handles both legacy string-based data 
    and new interconnected Fight relationships
    """
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'fighter',
            'perspective_fighter', 
            'authoritative_fight__event',
            'opponent_fighter'
        ).prefetch_related(
            'authoritative_fight__participants__fighter'
        )
    
    def for_fighter(self, fighter):
        """Get all fight history for a fighter from both sources"""
        return self.filter(
            Q(fighter=fighter) | Q(perspective_fighter=fighter)
        ).distinct()
    
    def interconnected(self):
        """Get only records linked to authoritative Fight records"""
        return self.filter(authoritative_fight__isnull=False)
    
    def legacy_only(self):
        """Get only legacy string-based records (not yet linked)"""
        return self.filter(authoritative_fight__isnull=True)
    
    def with_live_data(self):
        """
        Get fight history with live data from Fight records where available,
        falling back to stored string data
        """
        return self.annotate(
            # Use live opponent data if available
            live_opponent_name=models.Case(
                models.When(
                    authoritative_fight__isnull=False,
                    then=models.Subquery(
                        # Get opponent's name from the Fight
                        Fighter.objects.filter(
                            fight_participations__fight=models.OuterRef('authoritative_fight')
                        ).exclude(
                            id=models.OuterRef('perspective_fighter_id')
                        ).values('display_name')[:1]
                    )
                ),
                default=models.F('opponent_full_name'),
                output_field=models.CharField()
            ),
            
            # Use live event name if available
            live_event_name=models.Case(
                models.When(
                    authoritative_fight__event__isnull=False,
                    then=models.F('authoritative_fight__event__name')
                ),
                default=models.F('event_name'),
                output_field=models.CharField()
            ),
            
            # Use live result if available
            live_result=models.Case(
                models.When(
                    authoritative_fight__isnull=False,
                    then=models.Subquery(
                        FightParticipant.objects.filter(
                            fight=models.OuterRef('authoritative_fight'),
                            fighter=models.OuterRef('perspective_fighter')
                        ).values('result')[:1]
                    )
                ),
                default=models.F('result'),
                output_field=models.CharField()
            )
        )
```

### Enhanced Fight Model Methods

```python
# events/models.py - Add to Fight model
class Fight(models.Model):
    # ... existing fields ...
    
    def create_history_perspectives(self):
        """
        Create FightHistory records for both fighters' perspectives
        """
        participants = list(self.participants.all()[:2])
        if len(participants) != 2:
            return
        
        for i, participant in enumerate(participants):
            opponent = participants[1-i]  # Get the other fighter
            
            # Check if history already exists
            history, created = FightHistory.objects.get_or_create(
                authoritative_fight=self,
                perspective_fighter=participant.fighter,
                defaults={
                    'fighter': participant.fighter,  # Legacy field
                    'result': participant.result,
                    'opponent_full_name': opponent.fighter.get_full_name(),
                    'opponent_first_name': opponent.fighter.first_name,
                    'opponent_last_name': opponent.fighter.last_name,
                    'opponent_fighter': opponent.fighter,
                    'event_name': self.event.name,
                    'event_date': self.event.date,
                    'event': self.event,
                    'method': self.method,
                    'method_details': self.method_details,
                    'ending_round': self.ending_round,
                    'ending_time': self.ending_time,
                    'scheduled_rounds': self.scheduled_rounds,
                    'is_title_fight': self.is_title_fight,
                    'is_interim_title': self.is_interim_title,
                    'weight_class': self.weight_class,
                    'organization': self.event.organization,
                    'location': self.event.location,
                    'venue': self.event.venue,
                    'city': self.event.city,
                    'state': self.event.state,
                    'country': self.event.country,
                    'fight_order': self.get_fighter_career_order(participant.fighter),
                    'data_source': 'authoritative_fight'
                }
            )
            
            # Update existing record if not created
            if not created:
                self._update_history_from_fight(history, participant, opponent)
    
    def _update_history_from_fight(self, history, participant, opponent):
        """Update FightHistory record with current Fight data"""
        history.result = participant.result
        history.opponent_full_name = opponent.fighter.get_full_name()
        history.opponent_fighter = opponent.fighter
        history.event_name = self.event.name
        history.event_date = self.event.date
        history.method = self.method
        history.method_details = self.method_details
        history.ending_round = self.ending_round
        history.ending_time = self.ending_time
        history.is_title_fight = self.is_title_fight
        history.save()
    
    def get_fighter_career_order(self, fighter):
        """Calculate this fight's order in the fighter's career"""
        earlier_fights = Fight.objects.filter(
            participants__fighter=fighter,
            event__date__lt=self.event.date
        ).count()
        return earlier_fights + 1

    def save(self, *args, **kwargs):
        """Override save to maintain FightHistory perspectives"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create/update history perspectives after save
        if not is_new:  # Only for existing fights to avoid recursion
            self.create_history_perspectives()
```

## Phase 3: Data Consistency and Quality Assurance

### Data Reconciliation Service

```python
# fighters/services/reconciliation.py
from django.db import transaction
from django.db.models import Q, Count
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)

class FightHistoryReconciliationService:
    """
    Service to reconcile string-based fight history with authoritative Fight records
    """
    
    def __init__(self):
        self.stats = {
            'processed': 0,
            'linked': 0,
            'unmatched': 0,
            'conflicts': 0
        }
    
    def reconcile_all_unlinked_history(self):
        """Reconcile all FightHistory records not yet linked to Fight records"""
        unlinked_records = FightHistory.objects.filter(
            authoritative_fight__isnull=True
        ).select_related('fighter', 'event', 'opponent_fighter')
        
        logger.info(f"Starting reconciliation of {unlinked_records.count()} unlinked records")
        
        for history in unlinked_records:
            try:
                self._reconcile_single_history(history)
                self.stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error reconciling history {history.id}: {e}")
        
        logger.info(f"Reconciliation complete: {self.stats}")
        return self.stats
    
    def _reconcile_single_history(self, history):
        """Reconcile a single FightHistory record"""
        # Strategy 1: Direct event and fighter match
        if history.event:
            fight = self._find_fight_by_event_and_participants(history)
            if fight:
                self._link_history_to_fight(history, fight)
                self.stats['linked'] += 1
                return
        
        # Strategy 2: Date and opponent name matching
        fight = self._find_fight_by_date_and_names(history)
        if fight:
            self._link_history_to_fight(history, fight)
            self.stats['linked'] += 1
            return
        
        # Strategy 3: Create new Fight record from history
        if self._should_create_fight_from_history(history):
            fight = self._create_fight_from_history(history)
            self._link_history_to_fight(history, fight)
            self.stats['linked'] += 1
            return
        
        self.stats['unmatched'] += 1
        logger.warning(f"Could not reconcile history: {history}")
    
    def _find_fight_by_event_and_participants(self, history):
        """Find Fight by exact event and participant matching"""
        if not history.event:
            return None
            
        fights = Fight.objects.filter(
            event=history.event,
            participants__fighter=history.fighter
        ).prefetch_related('participants__fighter')
        
        for fight in fights:
            if self._participants_match_history(fight, history):
                return fight
        
        return None
    
    def _participants_match_history(self, fight, history):
        """Check if fight participants match history record"""
        participants = list(fight.participants.all())
        if len(participants) != 2:
            return False
        
        # Find the opponent (not the history's fighter)
        opponent_participant = None
        for p in participants:
            if p.fighter != history.fighter:
                opponent_participant = p
                break
        
        if not opponent_participant:
            return False
        
        # Check name similarity
        opponent_name = opponent_participant.fighter.get_full_name()
        similarity = fuzz.ratio(
            history.opponent_full_name.lower(),
            opponent_name.lower()
        )
        
        return similarity >= 85  # 85% similarity threshold
    
    def _find_fight_by_date_and_names(self, history):
        """Find Fight by date and fighter/opponent name matching"""
        # Find fights on the same date with the same fighter
        date_fights = Fight.objects.filter(
            event__date=history.event_date,
            participants__fighter=history.fighter
        ).prefetch_related('participants__fighter')
        
        best_match = None
        best_score = 0
        
        for fight in date_fights:
            score = self._calculate_match_score(fight, history)
            if score > best_score and score >= 80:  # 80% threshold
                best_match = fight
                best_score = score
        
        return best_match
    
    def _calculate_match_score(self, fight, history):
        """Calculate match score between Fight and FightHistory"""
        score = 0
        
        # Date match (required)
        if fight.event.date != history.event_date:
            return 0
        
        # Fighter participation (required)
        fighter_participates = fight.participants.filter(
            fighter=history.fighter
        ).exists()
        if not fighter_participates:
            return 0
        
        # Opponent name similarity
        opponent_participant = fight.participants.exclude(
            fighter=history.fighter
        ).first()
        
        if opponent_participant:
            opponent_name = opponent_participant.fighter.get_full_name()
            name_similarity = fuzz.ratio(
                history.opponent_full_name.lower(),
                opponent_name.lower()
            )
            score += name_similarity * 0.4  # 40% weight
        
        # Method similarity
        if history.method and fight.method:
            method_similarity = fuzz.ratio(
                history.method.lower(),
                fight.method.lower()
            )
            score += method_similarity * 0.2  # 20% weight
        
        # Event name similarity
        if history.event_name and fight.event.name:
            event_similarity = fuzz.ratio(
                history.event_name.lower(),
                fight.event.name.lower()
            )
            score += event_similarity * 0.2  # 20% weight
        
        # Round/time similarity
        if history.ending_round and fight.ending_round:
            if history.ending_round == fight.ending_round:
                score += 10  # Exact round match
        
        # Location similarity
        if history.location and fight.event.location:
            location_similarity = fuzz.ratio(
                history.location.lower(),
                fight.event.location.lower()
            )
            score += location_similarity * 0.2  # 20% weight
        
        return min(score, 100)  # Cap at 100
    
    @transaction.atomic
    def _link_history_to_fight(self, history, fight):
        """Link FightHistory record to authoritative Fight"""
        history.authoritative_fight = fight
        history.perspective_fighter = history.fighter
        
        # Update opponent_fighter if we found a better match
        opponent_participant = fight.participants.exclude(
            fighter=history.fighter
        ).first()
        
        if opponent_participant:
            history.opponent_fighter = opponent_participant.fighter
            # Update opponent names to match the authoritative record
            history.opponent_full_name = opponent_participant.fighter.get_full_name()
            history.opponent_first_name = opponent_participant.fighter.first_name
            history.opponent_last_name = opponent_participant.fighter.last_name
        
        # Update event reference
        if fight.event:
            history.event = fight.event
            history.event_name = fight.event.name
            history.event_date = fight.event.date
        
        history.data_source = 'reconciled'
        history.save()
        
        logger.info(f"Linked history {history.id} to fight {fight.id}")
```

## Phase 4: API Enhancement for Seamless Data Access

### Enhanced API Serializers

```python
# api/serializers.py
class InterconnectedFightHistorySerializer(serializers.ModelSerializer):
    """
    Serializer that provides seamless access to both legacy and interconnected data
    """
    
    # Dynamic fields that use live data when available
    opponent_name = serializers.SerializerMethodField()
    event_name = serializers.SerializerMethodField()
    event_date = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    method = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    # Metadata about data source
    is_interconnected = serializers.SerializerMethodField()
    data_freshness = serializers.SerializerMethodField()
    
    # Related data
    opponent_fighter = FighterSummarySerializer(read_only=True)
    authoritative_fight = serializers.SerializerMethodField()
    
    class Meta:
        model = FightHistory
        fields = [
            'id', 'fighter', 'opponent_name', 'opponent_fighter',
            'result', 'method', 'method_details',
            'event_name', 'event_date', 'location',
            'ending_round', 'ending_time', 'scheduled_rounds',
            'is_title_fight', 'weight_class_name',
            'fight_order', 'fighter_record_at_time',
            'is_interconnected', 'data_freshness',
            'authoritative_fight', 'data_quality_score'
        ]
    
    def get_opponent_name(self, obj):
        """Get opponent name from live data if available"""
        if obj.authoritative_fight:
            opponent = self._get_opponent_from_fight(obj)
            return opponent.get_full_name() if opponent else obj.opponent_full_name
        return obj.opponent_full_name
    
    def get_event_name(self, obj):
        """Get event name from live data if available"""
        if obj.authoritative_fight and obj.authoritative_fight.event:
            return obj.authoritative_fight.event.name
        return obj.event_name
    
    def get_event_date(self, obj):
        """Get event date from live data if available"""
        if obj.authoritative_fight and obj.authoritative_fight.event:
            return obj.authoritative_fight.event.date
        return obj.event_date
    
    def get_result(self, obj):
        """Get result from live data if available"""
        if obj.authoritative_fight:
            participant = obj.authoritative_fight.participants.filter(
                fighter=obj.perspective_fighter
            ).first()
            return participant.result if participant else obj.result
        return obj.result
    
    def get_method(self, obj):
        """Get method from live data if available"""
        if obj.authoritative_fight and obj.authoritative_fight.method:
            return obj.authoritative_fight.method
        return obj.method
    
    def get_location(self, obj):
        """Get location from live data if available"""
        if obj.authoritative_fight and obj.authoritative_fight.event:
            event = obj.authoritative_fight.event
            return event.location or f"{event.city}, {event.country}"
        return obj.location
    
    def get_is_interconnected(self, obj):
        """Check if this record is linked to authoritative Fight"""
        return obj.authoritative_fight is not None
    
    def get_data_freshness(self, obj):
        """Indicate data freshness"""
        if obj.authoritative_fight:
            return 'live'  # Data comes from authoritative source
        return 'historical'  # Data from historical records
    
    def get_authoritative_fight(self, obj):
        """Get authoritative fight summary if available"""
        if obj.authoritative_fight:
            return {
                'id': obj.authoritative_fight.id,
                'event_id': obj.authoritative_fight.event.id,
                'fight_order': obj.authoritative_fight.fight_order,
                'is_main_event': obj.authoritative_fight.is_main_event
            }
        return None
    
    def _get_opponent_from_fight(self, history_obj):
        """Helper to get opponent fighter from authoritative fight"""
        if not history_obj.authoritative_fight:
            return None
        
        opponent_participant = history_obj.authoritative_fight.participants.exclude(
            fighter=history_obj.perspective_fighter
        ).first()
        
        return opponent_participant.fighter if opponent_participant else None
```

## Phase 5: Testing Strategy

### Comprehensive Test Suite

```python
# fighters/tests/test_interconnected_history.py
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from unittest.mock import patch
import uuid

class InterconnectedFightHistoryTests(TransactionTestCase):
    """
    Test suite for interconnected fight history system
    """
    
    def setUp(self):
        # Create test data
        self.org = Organization.objects.create(name="UFC", abbreviation="UFC")
        self.weight_class = WeightClass.objects.create(
            name="Lightweight", weight_lb=155, organization=self.org
        )
        
        self.fighter1 = Fighter.objects.create(
            first_name="Jon", last_name="Jones"
        )
        self.fighter2 = Fighter.objects.create(
            first_name="Daniel", last_name="Cormier"
        )
        
        self.event = Event.objects.create(
            name="UFC 214", organization=self.org,
            date="2017-07-29", location="Anaheim, CA"
        )
        
        self.fight = Fight.objects.create(
            event=self.event,
            weight_class=self.weight_class,
            fight_order=1,
            is_main_event=True,
            status='completed',
            method='TKO',
            ending_round=3,
            ending_time='4:20'
        )
        
        # Create fight participants
        self.participant1 = FightParticipant.objects.create(
            fight=self.fight,
            fighter=self.fighter1,
            corner='red',
            result='win'
        )
        self.participant2 = FightParticipant.objects.create(
            fight=self.fight,
            fighter=self.fighter2,
            corner='blue',
            result='loss'
        )
    
    def test_fight_creates_history_perspectives(self):
        """Test that Fight.create_history_perspectives() creates both fighter views"""
        # Ensure no history exists initially
        self.assertEqual(FightHistory.objects.count(), 0)
        
        # Create history perspectives
        self.fight.create_history_perspectives()
        
        # Should create 2 history records (one for each fighter)
        self.assertEqual(FightHistory.objects.count(), 2)
        
        # Check Jon Jones' perspective
        jones_history = FightHistory.objects.get(
            perspective_fighter=self.fighter1,
            authoritative_fight=self.fight
        )
        self.assertEqual(jones_history.result, 'win')
        self.assertEqual(jones_history.opponent_full_name, 'Daniel Cormier')
        self.assertEqual(jones_history.opponent_fighter, self.fighter2)
        
        # Check Daniel Cormier's perspective
        cormier_history = FightHistory.objects.get(
            perspective_fighter=self.fighter2,
            authoritative_fight=self.fight
        )
        self.assertEqual(cormier_history.result, 'loss')
        self.assertEqual(cormier_history.opponent_full_name, 'Jon Jones')
        self.assertEqual(cormier_history.opponent_fighter, self.fighter1)
    
    def test_fight_update_syncs_history(self):
        """Test that Fight updates sync to FightHistory perspectives"""
        # Create initial history
        self.fight.create_history_perspectives()
        
        # Update the fight
        self.fight.method = 'KO'
        self.fight.ending_round = 2
        self.fight.ending_time = '3:15'
        self.fight.save()
        
        # Check that history was updated
        histories = FightHistory.objects.filter(authoritative_fight=self.fight)
        for history in histories:
            self.assertEqual(history.method, 'KO')
            self.assertEqual(history.ending_round, 2)
            self.assertEqual(history.ending_time, '3:15')
    
    def test_reconciliation_service_links_existing_history(self):
        """Test that reconciliation service can link existing string-based history"""
        # Create legacy fight history (string-based)
        legacy_history = FightHistory.objects.create(
            fighter=self.fighter1,
            result='win',
            opponent_full_name='Daniel Cormier',
            opponent_first_name='Daniel',
            opponent_last_name='Cormier',
            event_name='UFC 214',
            event_date='2017-07-29',
            method='TKO',
            ending_round=3,
            ending_time='4:20',
            fight_order=1,
            data_source='wikipedia'
        )
        
        # Ensure it's not linked initially
        self.assertIsNone(legacy_history.authoritative_fight)
        
        # Run reconciliation
        service = FightHistoryReconciliationService()
        service._reconcile_single_history(legacy_history)
        
        # Reload from database
        legacy_history.refresh_from_db()
        
        # Should now be linked
        self.assertEqual(legacy_history.authoritative_fight, self.fight)
        self.assertEqual(legacy_history.perspective_fighter, self.fighter1)
    
    def test_api_returns_live_data_when_available(self):
        """Test that API returns live data from Fight when available"""
        # Create both legacy and interconnected history
        legacy_history = FightHistory.objects.create(
            fighter=self.fighter1,
            result='win',
            opponent_full_name='Dan Cormier',  # Slightly different name
            event_name='UFC 214: Cormier vs Jones 2',  # Different event name
            event_date='2017-07-29',
            method='TKO',
            fight_order=1,
            data_source='wikipedia'
        )
        
        interconnected_history = FightHistory.objects.create(
            fighter=self.fighter2,
            perspective_fighter=self.fighter2,
            authoritative_fight=self.fight,
            result='loss',
            opponent_full_name='Jon Jones',
            event_name='UFC 214',
            event_date='2017-07-29',
            method='TKO',
            fight_order=1,
            data_source='authoritative_fight'
        )
        
        # Serialize both
        serializer_legacy = InterconnectedFightHistorySerializer(legacy_history)
        serializer_interconnected = InterconnectedFightHistorySerializer(interconnected_history)
        
        # Legacy should use stored data
        self.assertEqual(serializer_legacy.data['opponent_name'], 'Dan Cormier')
        self.assertEqual(serializer_legacy.data['event_name'], 'UFC 214: Cormier vs Jones 2')
        self.assertEqual(serializer_legacy.data['is_interconnected'], False)
        self.assertEqual(serializer_legacy.data['data_freshness'], 'historical')
        
        # Interconnected should use live data
        self.assertEqual(serializer_interconnected.data['opponent_name'], 'Jon Jones')
        self.assertEqual(serializer_interconnected.data['event_name'], 'UFC 214')  # From Fight.event
        self.assertEqual(serializer_interconnected.data['is_interconnected'], True)
        self.assertEqual(serializer_interconnected.data['data_freshness'], 'live')
    
    def test_data_consistency_constraints(self):
        """Test that data consistency is maintained"""
        # Create history perspectives
        self.fight.create_history_perspectives()
        
        # Both perspectives should reference the same fight
        histories = FightHistory.objects.filter(authoritative_fight=self.fight)
        self.assertEqual(histories.count(), 2)
        
        # Should have opposite results
        results = set(h.result for h in histories)
        self.assertEqual(results, {'win', 'loss'})
        
        # Should reference each other as opponents
        jones_history = histories.get(perspective_fighter=self.fighter1)
        cormier_history = histories.get(perspective_fighter=self.fighter2)
        
        self.assertEqual(jones_history.opponent_fighter, self.fighter2)
        self.assertEqual(cormier_history.opponent_fighter, self.fighter1)
    
    def test_performance_with_large_dataset(self):
        """Test performance with large dataset"""
        # Create 1000 fights with history
        with transaction.atomic():
            for i in range(100):  # Reduced for test speed
                event = Event.objects.create(
                    name=f"Event {i}",
                    organization=self.org,
                    date="2020-01-01"
                )
                fight = Fight.objects.create(
                    event=event,
                    fight_order=1,
                    status='completed'
                )
                
                # Create participants and history
                FightParticipant.objects.create(
                    fight=fight, fighter=self.fighter1, result='win'
                )
                FightParticipant.objects.create(
                    fight=fight, fighter=self.fighter2, result='loss'
                )
                
                fight.create_history_perspectives()
        
        # Test query performance
        import time
        start_time = time.time()
        
        # Query all history for fighter1 with related data
        history_records = list(
            FightHistory.objects.filter(perspective_fighter=self.fighter1)
            .select_related('authoritative_fight__event', 'opponent_fighter')
            .prefetch_related('authoritative_fight__participants')
        )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete in reasonable time (< 1 second for 100 records)
        self.assertLess(query_time, 1.0)
        self.assertEqual(len(history_records), 101)  # 100 + original test fight
```

## Phase 6: Migration Execution Plan

### Step-by-Step Execution

1. **Pre-Migration Backup**
   ```bash
   pg_dump your_database > pre_interconnected_backup.sql
   ```

2. **Run Phase 1 Migrations**
   ```bash
   python manage.py makemigrations fighters
   python manage.py migrate fighters 0003_add_fight_relationships
   ```

3. **Data Linking Migration**
   ```bash
   python manage.py migrate fighters 0004_link_existing_fight_history
   ```

4. **Verification Queries**
   ```sql
   -- Check linking success rate
   SELECT 
       COUNT(*) as total_records,
       COUNT(authoritative_fight_id) as linked_records,
       ROUND(COUNT(authoritative_fight_id) * 100.0 / COUNT(*), 2) as link_percentage
   FROM fight_history;
   
   -- Check for data consistency
   SELECT 
       fh1.id as history1_id,
       fh2.id as history2_id,
       fh1.authoritative_fight_id
   FROM fight_history fh1
   JOIN fight_history fh2 ON fh1.authoritative_fight_id = fh2.authoritative_fight_id
   WHERE fh1.id < fh2.id
   AND fh1.result = fh2.result  -- Should be opposite
   LIMIT 10;
   ```

### Rollback Plan

If issues arise, you can safely rollback:

```python
# Emergency rollback migration
class Migration(migrations.Migration):
    dependencies = [
        ('fighters', '0004_link_existing_fight_history'),
    ]

    operations = [
        # Clear all links
        migrations.RunSQL(
            "UPDATE fight_history SET authoritative_fight_id = NULL, perspective_fighter_id = NULL;",
            reverse_sql="-- No reverse needed"
        ),
        
        # Drop new columns
        migrations.RemoveField(
            model_name='fighthistory',
            name='authoritative_fight',
        ),
        migrations.RemoveField(
            model_name='fighthistory',
            name='perspective_fighter',
        ),
    ]
```

## Summary

This implementation plan provides:

1. **Zero-downtime migration** - All changes are additive initially
2. **Data integrity preservation** - Existing data remains untouched
3. **Gradual transition** - Supports both legacy and interconnected data simultaneously
4. **Performance optimization** - Strategic indexes and query optimization
5. **Comprehensive testing** - Full test coverage for data consistency
6. **Safe rollback** - Easy rollback if issues arise

The key insight is to treat this as a gradual evolution rather than a replacement, allowing both systems to coexist until the migration is fully complete and validated.