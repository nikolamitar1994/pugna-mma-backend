"""
Management command to reconcile fight history with authoritative Fight records.

This command can be run regularly to link new FightHistory records with
existing Fight records, maintaining the interconnected data network.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from fighters.services.reconciliation import (
    FightHistoryReconciliationService,
    FightHistoryConsistencyChecker
)
from fighters.models import Fighter, FightHistory
import json


class Command(BaseCommand):
    help = 'Reconcile fight history records with authoritative Fight records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--fighter-id',
            type=str,
            help='Reconcile only for specific fighter (UUID)',
        )
        parser.add_argument(
            '--fighter-name',
            type=str,
            help='Reconcile only for fighter by name (searches first/last/display)',
        )
        parser.add_argument(
            '--check-consistency',
            action='store_true',
            help='Run consistency checks on existing interconnected data',
        )
        parser.add_argument(
            '--fix-conflicts',
            action='store_true',
            help='Automatically fix data conflicts where possible',
        )
        parser.add_argument(
            '--report-only',
            action='store_true',
            help='Generate reconciliation report without processing',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information',
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        try:
            if options['check_consistency']:
                self.check_consistency()
            elif options['report_only']:
                self.generate_report()
            else:
                self.reconcile_records(options)
        except Exception as e:
            raise CommandError(f'Reconciliation failed: {e}')

    def reconcile_records(self, options):
        """Main reconciliation process."""
        service = FightHistoryReconciliationService()
        
        dry_run = options.get('dry_run', False)
        fighter_id = options.get('fighter_id')
        fighter_name = options.get('fighter_name')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Reconcile specific fighter or all unlinked records
        if fighter_id or fighter_name:
            fighter = self.get_fighter(fighter_id, fighter_name)
            if not fighter:
                raise CommandError('Fighter not found')
            
            self.stdout.write(f'Reconciling fight history for: {fighter.get_full_name()}')
            stats = service.reconcile_fighter_history(fighter, dry_run=dry_run)
            
        else:
            self.stdout.write('Reconciling all unlinked fight history records...')
            stats = service.reconcile_all_unlinked_history(dry_run=dry_run)
        
        # Display results
        self.display_reconciliation_stats(stats)
        
        # Fix conflicts if requested
        if options.get('fix_conflicts') and not dry_run:
            self.fix_data_conflicts()

    def check_consistency(self):
        """Run consistency checks on interconnected data."""
        self.stdout.write('Running consistency checks...')
        
        checker = FightHistoryConsistencyChecker()
        issues = checker.check_all_consistency()
        
        if not issues:
            self.stdout.write(
                self.style.SUCCESS('✓ No consistency issues found')
            )
            return
        
        # Group issues by severity
        high_severity = [i for i in issues if i['severity'] == 'high']
        medium_severity = [i for i in issues if i['severity'] == 'medium']
        low_severity = [i for i in issues if i['severity'] == 'low']
        
        if high_severity:
            self.stdout.write(
                self.style.ERROR(f'Found {len(high_severity)} HIGH SEVERITY issues:')
            )
            for issue in high_severity:
                self.stdout.write(f'  - {issue["message"]}')
        
        if medium_severity:
            self.stdout.write(
                self.style.WARNING(f'Found {len(medium_severity)} medium severity issues:')
            )
            for issue in medium_severity:
                self.stdout.write(f'  - {issue["message"]}')
        
        if low_severity:
            self.stdout.write(f'Found {len(low_severity)} low severity issues:')
            for issue in low_severity:
                self.stdout.write(f'  - {issue["message"]}')
        
        # Suggest fixes
        self.stdout.write('\nTo fix issues automatically, run:')
        self.stdout.write('  python manage.py reconcile_fight_history --fix-conflicts')

    def fix_data_conflicts(self):
        """Fix data conflicts between stored and authoritative data."""
        self.stdout.write('Fixing data conflicts...')
        
        # Find records with conflicts
        conflicted_records = FightHistory.objects.filter(
            authoritative_fight__isnull=False
        )
        
        fixed_count = 0
        for history in conflicted_records:
            conflicts = history.has_data_conflicts()
            if conflicts:
                if self.verbose:
                    self.stdout.write(f'Fixing conflicts for {history.id}: {list(conflicts.keys())}')
                
                # Sync from authoritative fight (this fixes most conflicts)
                if history.sync_from_authoritative_fight():
                    fixed_count += 1
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Fixed conflicts in {fixed_count} records')
            )
        else:
            self.stdout.write('No conflicts found to fix')

    def generate_report(self):
        """Generate comprehensive reconciliation report."""
        self.stdout.write('Generating reconciliation report...')
        
        service = FightHistoryReconciliationService()
        report = service.generate_reconciliation_report()
        
        # Display summary
        summary = report['summary']
        self.stdout.write('\n=== RECONCILIATION SUMMARY ===')
        self.stdout.write(f'Total fight history records: {summary["total_history_records"]:,}')
        self.stdout.write(f'Linked to authoritative fights: {summary["linked_records"]:,} ({summary["link_percentage"]:.1f}%)')
        self.stdout.write(f'Unlinked records: {summary["unlinked_records"]:,}')
        
        # Display by data source
        self.stdout.write('\n=== BY DATA SOURCE ===')
        for source, stats in report['by_data_source'].items():
            if stats['total'] > 0:
                self.stdout.write(
                    f'{source}: {stats["linked"]}/{stats["total"]} linked ({stats["link_rate"]:.1f}%)'
                )
        
        # Display data quality
        self.stdout.write('\n=== DATA QUALITY DISTRIBUTION ===')
        for quality, count in report['data_quality_distribution'].items():
            if count > 0:
                self.stdout.write(f'{quality}: {count:,} records')
        
        # Export detailed report to file
        report_file = 'fight_history_reconciliation_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.stdout.write(f'\nDetailed report exported to: {report_file}')

    def get_fighter(self, fighter_id, fighter_name):
        """Get fighter by ID or name."""
        if fighter_id:
            try:
                return Fighter.objects.get(id=fighter_id)
            except Fighter.DoesNotExist:
                return None
        
        if fighter_name:
            # Search by various name fields
            fighters = Fighter.objects.filter(
                models.Q(first_name__icontains=fighter_name) |
                models.Q(last_name__icontains=fighter_name) |
                models.Q(display_name__icontains=fighter_name) |
                models.Q(nickname__icontains=fighter_name)
            )
            
            if fighters.count() == 1:
                return fighters.first()
            elif fighters.count() > 1:
                self.stdout.write('Multiple fighters found:')
                for fighter in fighters:
                    self.stdout.write(f'  {fighter.id}: {fighter.get_full_name()}')
                raise CommandError('Multiple fighters matched - use --fighter-id instead')
            else:
                return None
        
        return None

    def display_reconciliation_stats(self, stats):
        """Display reconciliation statistics in a formatted way."""
        self.stdout.write('\n=== RECONCILIATION RESULTS ===')
        
        if 'processed' in stats:
            self.stdout.write(f'Records processed: {stats["processed"]:,}')
        
        if 'linked' in stats:
            linked = stats['linked']
            processed = stats.get('processed', linked)
            percentage = (linked / processed * 100) if processed > 0 else 0
            
            if linked > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully linked: {linked:,} ({percentage:.1f}%)')
                )
            else:
                self.stdout.write('No records were linked')
        
        if 'unmatched' in stats and stats['unmatched'] > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ Could not match: {stats["unmatched"]:,}')
            )
        
        if 'errors' in stats and stats['errors'] > 0:
            self.stdout.write(
                self.style.ERROR(f'✗ Errors encountered: {stats["errors"]:,}')
            )
        
        if 'success_rate' in stats:
            rate = stats['success_rate']
            if rate >= 80:
                style = self.style.SUCCESS
            elif rate >= 60:
                style = self.style.WARNING
            else:
                style = self.style.ERROR
            
            self.stdout.write(style(f'Success rate: {rate:.1f}%'))
        
        # Show next steps
        if stats.get('unmatched', 0) > 0:
            self.stdout.write('\nNext steps for unmatched records:')
            self.stdout.write('1. Check if Fight records exist for these fights')
            self.stdout.write('2. Create Fight records if missing')
            self.stdout.write('3. Re-run reconciliation')
            self.stdout.write('4. Consider manual review for complex cases')