"""
Comprehensive test suite for the interconnected fight history system.

Tests cover:
- Data integrity and consistency
- Bidirectional relationships 
- Live data prioritization
- Reconciliation accuracy
- Performance with large datasets
"""

from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from datetime import datetime, date
import uuid

from fighters.models import Fighter, FightHistory, FighterNameVariation
from events.models import Event, Fight, FightParticipant
from organizations.models import Organization, WeightClass
from fighters.services.reconciliation import (
    FightHistoryReconciliationService,
    FightHistoryConsistencyChecker
)
from api.serializers_interconnected import (
    InterconnectedFightHistorySerializer,
    FighterInterconnectedSerializer
)


class InterconnectedFightHistoryTestCase(TransactionTestCase):
    """Base test case with common setup for interconnected system tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create organization and weight class
        self.ufc = Organization.objects.create(
            name="Ultimate Fighting Championship",
            abbreviation="UFC"
        )
        self.lightweight = WeightClass.objects.create(
            name="Lightweight",
            weight_lb=155,
            organization=self.ufc
        )
        
        # Create fighters
        self.jones = Fighter.objects.create(
            first_name="Jon",
            last_name="Jones",
            nickname="Bones",
            nationality="USA"
        )
        self.cormier = Fighter.objects.create(
            first_name="Daniel",
            last_name="Cormier",
            nickname="DC",
            nationality="USA"
        )
        self.gustafsson = Fighter.objects.create(
            first_name="Alexander",
            last_name="Gustafsson",
            nickname="The Mauler",
            nationality="Sweden"
        )
        
        # Create events
        self.ufc214 = Event.objects.create(
            name="UFC 214: Cormier vs. Jones 2",
            organization=self.ufc,
            date=date(2017, 7, 29),
            location="Anaheim, CA",
            venue="Honda Center"
        )
        self.ufc165 = Event.objects.create(
            name="UFC 165: Jones vs. Gustafsson",
            organization=self.ufc,
            date=date(2013, 9, 21),
            location="Toronto, ON",
            venue="Air Canada Centre"
        )
        
        # Create fights
        self.jones_cormier_fight = Fight.objects.create(
            event=self.ufc214,
            weight_class=self.lightweight,
            fight_order=1,
            is_main_event=True,
            is_title_fight=True,
            status='completed',
            method='KO',
            ending_round=3,
            ending_time='4:20',
            scheduled_rounds=5
        )
        
        self.jones_gustafsson_fight = Fight.objects.create(
            event=self.ufc165,
            weight_class=self.lightweight,
            fight_order=1,
            is_main_event=True,
            is_title_fight=True,
            status='completed',
            method='Decision (unanimous)',
            scheduled_rounds=5
        )
        
        # Create fight participants
        self.jones_vs_cormier_p1 = FightParticipant.objects.create(
            fight=self.jones_cormier_fight,
            fighter=self.jones,
            corner='red',
            result='win'
        )
        self.jones_vs_cormier_p2 = FightParticipant.objects.create(
            fight=self.jones_cormier_fight,
            fighter=self.cormier,
            corner='blue',
            result='loss'
        )
        
        self.jones_vs_gustafsson_p1 = FightParticipant.objects.create(
            fight=self.jones_gustafsson_fight,
            fighter=self.jones,
            corner='red',
            result='win'
        )
        self.jones_vs_gustafsson_p2 = FightParticipant.objects.create(
            fight=self.jones_gustafsson_fight,
            fighter=self.gustafsson,
            corner='blue',
            result='loss'
        )


class FightHistoryInterconnectionTests(InterconnectedFightHistoryTestCase):
    """Test fight history interconnection functionality."""
    
    def test_fight_creates_bidirectional_history_perspectives(self):
        """Test that Fight automatically creates FightHistory perspectives for both fighters."""
        # Initially no history records exist
        self.assertEqual(FightHistory.objects.count(), 0)
        
        # Trigger history creation
        created_histories = self.jones_cormier_fight.create_history_perspectives()
        
        # Should create 2 history records
        self.assertEqual(len(created_histories), 2)
        self.assertEqual(FightHistory.objects.count(), 2)
        
        # Get each fighter's perspective
        jones_history = FightHistory.objects.get(
            authoritative_fight=self.jones_cormier_fight,
            perspective_fighter=self.jones
        )
        cormier_history = FightHistory.objects.get(
            authoritative_fight=self.jones_cormier_fight,
            perspective_fighter=self.cormier
        )
        
        # Verify Jones' perspective
        self.assertEqual(jones_history.result, 'win')
        self.assertEqual(jones_history.opponent_full_name, 'Daniel Cormier')
        self.assertEqual(jones_history.opponent_fighter, self.cormier)
        self.assertEqual(jones_history.method, 'KO')
        self.assertEqual(jones_history.data_source, 'authoritative_fight')
        self.assertTrue(jones_history.is_authoritative_derived)
        
        # Verify Cormier's perspective
        self.assertEqual(cormier_history.result, 'loss')
        self.assertEqual(cormier_history.opponent_full_name, 'Jon Jones')
        self.assertEqual(cormier_history.opponent_fighter, self.jones)
        self.assertEqual(cormier_history.method, 'KO')
        self.assertEqual(cormier_history.data_source, 'authoritative_fight')
        
        # Verify they reference the same authoritative fight
        self.assertEqual(jones_history.authoritative_fight, self.jones_cormier_fight)
        self.assertEqual(cormier_history.authoritative_fight, self.jones_cormier_fight)
    
    def test_fight_update_syncs_history_perspectives(self):
        """Test that Fight updates automatically sync to FightHistory perspectives."""
        # Create initial history
        self.jones_cormier_fight.create_history_perspectives()
        
        # Update the fight
        self.jones_cormier_fight.method = 'TKO'
        self.jones_cormier_fight.ending_round = 2
        self.jones_cormier_fight.ending_time = '3:15'
        self.jones_cormier_fight.save()
        
        # Check that history was updated
        histories = FightHistory.objects.filter(
            authoritative_fight=self.jones_cormier_fight
        )
        
        for history in histories:
            self.assertEqual(history.method, 'TKO')
            self.assertEqual(history.ending_round, 2)
            self.assertEqual(history.ending_time, '3:15')
    
    def test_history_live_data_methods(self):
        """Test that FightHistory live data methods return authoritative data."""
        # Create legacy history (string-based)
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            result='win',
            opponent_full_name='Dan Cormier',  # Different name
            event_name='UFC 214: Different Name',  # Different event name
            event_date=date(2017, 7, 29),
            method='TKO',  # Different method
            fight_order=1
        )
        
        # Create interconnected history
        interconnected_history = FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            authoritative_fight=self.jones_cormier_fight,
            result='win',
            opponent_full_name='Daniel Cormier',
            event_name='UFC 214: Cormier vs. Jones 2',
            event_date=date(2017, 7, 29),
            method='KO',
            fight_order=2
        )
        
        # Test legacy history (should return stored data)
        self.assertEqual(legacy_history.get_live_opponent_name(), 'Dan Cormier')
        self.assertEqual(legacy_history.get_live_event_name(), 'UFC 214: Different Name')
        self.assertEqual(legacy_history.get_live_method(), 'TKO')
        self.assertEqual(legacy_history.get_data_freshness(), 'historical')
        self.assertFalse(legacy_history.is_interconnected())
        
        # Test interconnected history (should return authoritative data)
        self.assertEqual(interconnected_history.get_live_opponent_name(), 'Daniel Cormier')
        self.assertEqual(interconnected_history.get_live_event_name(), 'UFC 214: Cormier vs. Jones 2')
        self.assertEqual(interconnected_history.get_live_method(), 'KO')
        self.assertEqual(interconnected_history.get_data_freshness(), 'live')
        self.assertTrue(interconnected_history.is_interconnected())
    
    def test_history_sync_from_authoritative_fight(self):
        """Test syncing history record from authoritative fight."""
        # Create history with outdated data
        history = FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            authoritative_fight=self.jones_cormier_fight,
            result='win',
            opponent_full_name='Old Name',  # Outdated
            event_name='Old Event Name',   # Outdated
            method='Old Method',           # Outdated
            fight_order=1
        )
        
        # Update the authoritative fight
        self.jones_cormier_fight.method = 'TKO'
        self.jones_cormier_fight.save()
        
        # Sync history from fight
        changed = history.sync_from_authoritative_fight()
        
        # Should detect changes
        self.assertTrue(changed)
        
        # Reload and verify updates
        history.refresh_from_db()
        self.assertEqual(history.opponent_full_name, 'Daniel Cormier')
        self.assertEqual(history.event_name, 'UFC 214: Cormier vs. Jones 2')
        self.assertEqual(history.method, 'TKO')
        self.assertEqual(history.data_source, 'reconciled')
    
    def test_data_conflict_detection(self):
        """Test detection of conflicts between stored and authoritative data."""
        # Create history with conflicting data
        history = FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            authoritative_fight=self.jones_cormier_fight,
            result='win',
            opponent_full_name='Wrong Name',
            event_date=date(2017, 7, 30),  # Wrong date
            method='Wrong Method',
            fight_order=1
        )
        
        # Check for conflicts  
        conflicts = history.has_data_conflicts()
        
        # Should detect conflicts
        self.assertIsNotNone(conflicts)
        self.assertIn('event_date', conflicts)
        self.assertIn('method', conflicts)
        self.assertIn('opponent_name', conflicts)
        
        # Verify conflict details
        self.assertEqual(conflicts['event_date']['stored'], '2017-07-30')
        self.assertEqual(conflicts['event_date']['authoritative'], '2017-07-29')


class ReconciliationServiceTests(InterconnectedFightHistoryTestCase):
    """Test the reconciliation service functionality."""
    
    def test_reconcile_exact_event_match(self):
        """Test reconciliation with exact event and fighter matches."""
        # Create legacy history
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            result='win',
            opponent_full_name='Daniel Cormier',
            opponent_first_name='Daniel',
            opponent_last_name='Cormier',
            event_name='UFC 214: Cormier vs. Jones 2',
            event_date=date(2017, 7, 29),
            event=self.ufc214,
            method='KO',
            fight_order=1
        )
        
        # Should not be linked initially
        self.assertIsNone(legacy_history.authoritative_fight)
        
        # Run reconciliation
        service = FightHistoryReconciliationService()
        result = service._reconcile_single_history(legacy_history)
        
        # Should successfully link
        self.assertTrue(result)
        
        # Reload and verify link
        legacy_history.refresh_from_db()
        self.assertEqual(legacy_history.authoritative_fight, self.jones_cormier_fight)
        self.assertEqual(legacy_history.perspective_fighter, self.jones)
        self.assertEqual(legacy_history.data_source, 'reconciled')
    
    def test_reconcile_fuzzy_name_matching(self):
        """Test reconciliation with fuzzy opponent name matching."""
        # Create history with slightly different opponent name
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            result='win',
            opponent_full_name='Dan Cormier',  # Nickname variation
            opponent_first_name='Dan',
            opponent_last_name='Cormier',
            event_name='UFC 214',
            event_date=date(2017, 7, 29),
            event=self.ufc214,
            method='KO',
            fight_order=1
        )
        
        # Run reconciliation
        service = FightHistoryReconciliationService()
        result = service._reconcile_single_history(legacy_history)
        
        # Should successfully link despite name variation
        self.assertTrue(result)
        
        legacy_history.refresh_from_db()
        self.assertEqual(legacy_history.authoritative_fight, self.jones_cormier_fight)
        # Name should be updated to authoritative version
        self.assertEqual(legacy_history.opponent_full_name, 'Daniel Cormier')
    
    def test_reconcile_date_based_matching(self):
        """Test reconciliation using date-based matching when no event reference."""
        # Create history without event reference
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            result='win',
            opponent_full_name='Daniel Cormier',
            event_name='UFC 214 Different Name',
            event_date=date(2017, 7, 29),  # Same date
            method='KO',
            fight_order=1
        )
        
        # Run reconciliation
        service = FightHistoryReconciliationService()
        result = service._reconcile_single_history(legacy_history)
        
        # Should link based on date + names
        self.assertTrue(result)
        
        legacy_history.refresh_from_db()
        self.assertEqual(legacy_history.authoritative_fight, self.jones_cormier_fight)
    
    def test_reconcile_no_match_scenario(self):
        """Test reconciliation when no suitable match exists."""
        # Create history for non-existent fight
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            result='win',
            opponent_full_name='Nonexistent Fighter',
            event_name='Fake Event',
            event_date=date(2020, 1, 1),
            method='KO',
            fight_order=1
        )
        
        # Run reconciliation
        service = FightHistoryReconciliationService()
        result = service._reconcile_single_history(legacy_history)
        
        # Should not link
        self.assertFalse(result)
        
        legacy_history.refresh_from_db()
        self.assertIsNone(legacy_history.authoritative_fight)
    
    def test_bulk_reconciliation(self):
        """Test bulk reconciliation of multiple records."""
        # Create multiple legacy history records
        histories = []
        for i, (fighter, opponent) in enumerate([
            (self.jones, self.cormier),
            (self.cormier, self.jones),
            (self.jones, self.gustafsson),
            (self.gustafsson, self.jones)
        ]):
            history = FightHistory.objects.create(
                fighter=fighter,
                result='win' if i % 2 == 0 else 'loss',
                opponent_full_name=opponent.get_full_name(),
                opponent_first_name=opponent.first_name,
                opponent_last_name=opponent.last_name,
                event_name=f'UFC Event {i}',
                event_date=date(2017, 7, 29) if i < 2 else date(2013, 9, 21),
                method='KO',
                fight_order=i + 1
            )
            histories.append(history)
        
        # Run bulk reconciliation
        service = FightHistoryReconciliationService()
        stats = service.reconcile_all_unlinked_history(dry_run=False)
        
        # Should process all records
        self.assertEqual(stats['processed'], 4)
        # Should link the ones with matching fights
        self.assertGreater(stats['linked'], 0)
        
        # Check that some were linked
        linked_count = FightHistory.objects.filter(
            authoritative_fight__isnull=False
        ).count()
        self.assertGreater(linked_count, 0)


class ConsistencyCheckTests(InterconnectedFightHistoryTestCase):
    """Test data consistency checking functionality."""
    
    def test_bidirectional_consistency_check(self):
        """Test checking for missing bidirectional perspectives."""
        # Create fight with only one perspective
        FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            authoritative_fight=self.jones_cormier_fight,
            result='win',
            opponent_full_name='Daniel Cormier',
            fight_order=1
        )
        # Missing Cormier's perspective
        
        checker = FightHistoryConsistencyChecker()
        issues = checker.check_all_consistency()
        
        # Should detect missing perspective
        missing_perspective_issues = [
            i for i in issues if i['type'] == 'missing_perspective'
        ]
        self.assertGreater(len(missing_perspective_issues), 0)
    
    def test_result_consistency_check(self):
        """Test checking for inconsistent results between perspectives."""
        # Create perspectives with same result (should be opposite)
        FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            authoritative_fight=self.jones_cormier_fight,
            result='win',
            opponent_full_name='Daniel Cormier',
            fight_order=1
        )
        FightHistory.objects.create(
            fighter=self.cormier,
            perspective_fighter=self.cormier,
            authoritative_fight=self.jones_cormier_fight,
            result='win',  # Should be 'loss'
            opponent_full_name='Jon Jones',
            fight_order=1
        )
        
        checker = FightHistoryConsistencyChecker()
        issues = checker.check_all_consistency()
        
        # Should detect result inconsistency
        result_issues = [
            i for i in issues if i['type'] == 'result_inconsistency'
        ]
        self.assertGreater(len(result_issues), 0)


class APISerializationTests(InterconnectedFightHistoryTestCase):
    """Test API serialization with interconnected data."""
    
    def test_interconnected_fight_history_serializer(self):
        """Test that serializer returns live data when available."""
        # Create legacy history
        legacy_history = FightHistory.objects.create(
            fighter=self.jones,
            perspective_fighter=self.jones,
            result='win',
            opponent_full_name='Dan Cormier',  # Different from authoritative
            event_name='UFC 214 Old Name',     # Different from authoritative
            event_date=date(2017, 7, 29),
            method='TKO',                      # Different from authoritative
            fight_order=1
        )
        
        # Create interconnected history
        interconnected_history = FightHistory.objects.create(
            fighter=self.cormier,
            perspective_fighter=self.cormier,
            authoritative_fight=self.jones_cormier_fight,
            result='loss',
            opponent_full_name='Jon Jones',
            event_name='UFC 214: Cormier vs. Jones 2',
            event_date=date(2017, 7, 29),
            method='KO',
            fight_order=1
        )
        
        # Serialize both
        legacy_data = InterconnectedFightHistorySerializer(legacy_history).data
        interconnected_data = InterconnectedFightHistorySerializer(interconnected_history).data
        
        # Legacy should use stored data
        self.assertEqual(legacy_data['opponent_name'], 'Dan Cormier')
        self.assertEqual(legacy_data['event_name'], 'UFC 214 Old Name')
        self.assertEqual(legacy_data['method'], 'TKO')
        self.assertEqual(legacy_data['data_freshness'], 'historical')
        self.assertFalse(legacy_data['is_interconnected'])
        
        # Interconnected should use live data
        self.assertEqual(interconnected_data['opponent_name'], 'Jon Jones')
        self.assertEqual(interconnected_data['event_name'], 'UFC 214: Cormier vs. Jones 2')
        self.assertEqual(interconnected_data['method'], 'KO')
        self.assertEqual(interconnected_data['data_freshness'], 'live')
        self.assertTrue(interconnected_data['is_interconnected'])
        
        # Should include authoritative fight summary
        self.assertIsNotNone(interconnected_data['authoritative_fight'])
        self.assertEqual(
            interconnected_data['authoritative_fight']['id'],
            str(self.jones_cormier_fight.id)
        )
    
    def test_fighter_interconnected_serializer(self):
        """Test fighter serializer with interconnected fight history."""
        # Create some fight history
        self.jones_cormier_fight.create_history_perspectives()
        self.jones_gustafsson_fight.create_history_perspectives()
        
        # Serialize fighter
        serializer = FighterInterconnectedSerializer(self.jones)
        data = serializer.data
        
        # Should include fight history
        self.assertIn('fight_history', data)
        self.assertGreater(len(data['fight_history']), 0)
        
        # Should include interconnection status
        self.assertIn('interconnection_status', data)
        status = data['interconnection_status']
        self.assertGreater(status['total_fights'], 0)
        self.assertGreater(status['interconnected_fights'], 0)
        self.assertGreater(status['interconnection_rate'], 0)
        
        # Should include recent fights and highlights
        self.assertIn('recent_fights', data)
        self.assertIn('career_highlights', data)


class PerformanceTests(InterconnectedFightHistoryTestCase):
    """Test performance with larger datasets."""
    
    def test_large_dataset_query_performance(self):
        """Test query performance with many interconnected records."""
        import time
        
        # Create many fights and history records
        fighters = []
        for i in range(20):  # 20 fighters
            fighter = Fighter.objects.create(
                first_name=f"Fighter{i}",
                last_name="Test",
                nationality="USA"
            )
            fighters.append(fighter)
        
        # Create events and fights
        fights = []
        for i in range(50):  # 50 fights
            event = Event.objects.create(
                name=f"UFC {200 + i}",
                organization=self.ufc,
                date=date(2020, 1, i % 28 + 1),
                location="Las Vegas, NV"
            )
            
            fight = Fight.objects.create(
                event=event,
                fight_order=1,
                status='completed',
                method='Decision'
            )
            
            # Add participants
            fighter1 = fighters[i % len(fighters)]
            fighter2 = fighters[(i + 1) % len(fighters)]
            
            FightParticipant.objects.create(
                fight=fight, fighter=fighter1, result='win'
            )
            FightParticipant.objects.create(
                fight=fight, fighter=fighter2, result='loss'
            )
            
            fights.append(fight)
        
        # Create history perspectives for all fights
        for fight in fights:
            fight.create_history_perspectives()
        
        # Test query performance
        start_time = time.time()
        
        # Query with interconnected data
        history_records = list(
            FightHistory.objects.with_live_data()
            .select_related('fighter', 'authoritative_fight__event', 'opponent_fighter')
            .prefetch_related('authoritative_fight__participants')[:100]
        )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should complete quickly (< 2 seconds for 100 records)
        self.assertLess(query_time, 2.0)
        self.assertEqual(len(history_records), 100)
    
    def test_reconciliation_performance(self):
        """Test reconciliation performance with many records."""
        import time
        
        # Create many legacy history records
        for i in range(100):
            FightHistory.objects.create(
                fighter=self.jones,
                result='win' if i % 2 == 0 else 'loss',
                opponent_full_name=f'Opponent {i}',
                opponent_first_name=f'Fighter{i}',
                opponent_last_name='Test',
                event_name=f'Event {i}',
                event_date=date(2020, 1, (i % 28) + 1),
                method='Decision',
                fight_order=i + 1
            )
        
        # Test reconciliation performance
        start_time = time.time()
        
        service = FightHistoryReconciliationService()
        stats = service.reconcile_all_unlinked_history(dry_run=True)
        
        end_time = time.time()
        reconciliation_time = end_time - start_time
        
        # Should complete in reasonable time (< 5 seconds for 100 records in dry run)
        self.assertLess(reconciliation_time, 5.0)
        self.assertEqual(stats['processed'], 100)


class IntegrationTests(InterconnectedFightHistoryTestCase):
    """Integration tests for the complete interconnected system."""
    
    def test_complete_workflow(self):
        """Test complete workflow from Fight creation to API serialization."""
        # Step 1: Create Fight with participants
        fight = Fight.objects.create(
            event=self.ufc214,
            weight_class=self.lightweight,
            fight_order=2,
            status='completed',
            method='Submission',
            ending_round=2,
            ending_time='3:47'
        )
        
        FightParticipant.objects.create(
            fight=fight, fighter=self.jones, corner='red', result='win'
        )
        FightParticipant.objects.create(
            fight=fight, fighter=self.cormier, corner='blue', result='loss'
        )
        
        # Step 2: Fight automatically creates history perspectives
        histories = fight.create_history_perspectives()
        self.assertEqual(len(histories), 2)
        
        # Step 3: Verify bidirectional consistency
        checker = FightHistoryConsistencyChecker()
        issues = checker.check_all_consistency()
        # Should have no issues for this fight
        fight_issues = [i for i in issues if 'fight_id' in i and i['fight_id'] == fight.id]
        self.assertEqual(len(fight_issues), 0)
        
        # Step 4: Update Fight and verify sync
        fight.method = 'TKO'
        fight.save()
        
        # History should auto-update
        for history in FightHistory.objects.filter(authoritative_fight=fight):
            self.assertEqual(history.method, 'TKO')
        
        # Step 5: Test API serialization
        serializer = InterconnectedFightHistorySerializer(
            FightHistory.objects.filter(authoritative_fight=fight).first()
        )
        data = serializer.data
        
        # Should return live data
        self.assertEqual(data['method'], 'TKO')
        self.assertEqual(data['data_freshness'], 'live')
        self.assertTrue(data['is_interconnected'])
        self.assertFalse(data['data_conflicts']['has_conflicts'])
        
        # Step 6: Test fighter serialization with interconnected data
        fighter_serializer = FighterInterconnectedSerializer(self.jones)
        fighter_data = fighter_serializer.data
        
        self.assertGreater(len(fighter_data['fight_history']), 0)
        self.assertGreater(fighter_data['interconnection_status']['interconnection_rate'], 0)