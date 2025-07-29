"""
Management command to create interconnected network from existing fight history data
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from fighters.models import Fighter, FightHistory
from fighters.services import FighterMatcher, NetworkConsistencyValidator
from organizations.models import Organization
from events.models import Event
from datetime import datetime


class Command(BaseCommand):
    help = 'Link existing fight history data to create interconnected network'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fighter-id',
            type=str,
            help='Process only specific fighter ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be linked without making changes'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.8,
            help='Minimum confidence score for automatic linking (0.0-1.0, default 0.8)'
        )
        parser.add_argument(
            '--create-missing-fighters',
            action='store_true',
            help='Create Fighter records for unmatched opponents'
        )
        parser.add_argument(
            '--link-events',
            action='store_true',
            help='Also attempt to link events and organizations'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information'
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.min_confidence = options['min_confidence']
        self.create_missing = options['create_missing_fighters']
        self.link_events = options['link_events']
        self.verbose = options['verbose']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        # Get fight histories to process
        fight_histories = self.get_fight_histories_to_process(options.get('fighter_id'))
        
        if not fight_histories.exists():
            self.stdout.write(
                self.style.WARNING('No fight histories found to process')
            )
            return
        
        self.stdout.write(
            f'Processing {fight_histories.count()} fight history records...'
        )
        
        # Initialize statistics
        stats = {
            'total_processed': 0,
            'opponents_linked': 0,
            'high_confidence_links': 0,
            'fighters_created': 0,
            'events_linked': 0,
            'organizations_linked': 0,
            'skipped_low_confidence': 0,
            'errors': 0
        }
        
        # Process in batches for better performance
        batch_size = 100
        total_count = fight_histories.count()
        
        for i in range(0, total_count, batch_size):
            batch = fight_histories[i:i + batch_size]
            batch_stats = self.process_batch(batch)
            
            # Update total statistics
            for key, value in batch_stats.items():
                stats[key] += value
            
            if self.verbose:
                progress = min(i + batch_size, total_count)
                self.stdout.write(f'Processed {progress}/{total_count} records...')
        
        # Process events and organizations if requested
        if self.link_events:
            self.stdout.write('\\nLinking events and organizations...')
            event_stats = self.link_events_and_organizations(fight_histories)
            stats.update(event_stats)
        
        # Final statistics and validation
        self.print_final_statistics(stats)
        
        if not self.dry_run:
            self.run_validation_checks()
    
    def get_fight_histories_to_process(self, fighter_id=None):
        """Get fight histories that need processing"""
        queryset = FightHistory.objects.select_related('fighter', 'opponent_fighter')
        
        if fighter_id:
            try:
                fighter = Fighter.objects.get(id=fighter_id)
                queryset = queryset.filter(fighter=fighter)
                self.stdout.write(f'Processing fight histories for: {fighter.get_full_name()}')
            except Fighter.DoesNotExist:
                raise CommandError(f'Fighter with ID {fighter_id} not found')
        
        # Focus on records that need linking
        queryset = queryset.filter(
            # Either no opponent fighter linked
            opponent_fighter__isnull=True
        ).order_by('event_date')
        
        return queryset
    
    def process_batch(self, fight_histories):
        """Process a batch of fight histories"""
        batch_stats = {
            'total_processed': 0,
            'opponents_linked': 0,
            'high_confidence_links': 0,
            'fighters_created': 0,
            'skipped_low_confidence': 0,
            'errors': 0
        }
        
        for fh in fight_histories:
            try:
                batch_stats['total_processed'] += 1
                
                # Skip if already linked
                if fh.opponent_fighter:
                    continue
                
                # Try to find opponent fighter
                opponent_fighter, confidence = FighterMatcher.find_fighter_by_name(
                    fh.opponent_first_name,
                    fh.opponent_last_name,
                    event_date=fh.event_date,
                    context_data={
                        'event_date': fh.event_date,
                        'nationality': None  # Could be enhanced with more context
                    }
                )
                
                if self.verbose:
                    opponent_name = fh.get_opponent_display_name()
                    if opponent_fighter:
                        self.stdout.write(
                            f'  Match: {opponent_name} -> {opponent_fighter.get_full_name()} (confidence: {confidence:.2f})'
                        )
                    else:
                        self.stdout.write(f'  No match: {opponent_name}')
                
                # Link if confidence is high enough
                if opponent_fighter and confidence >= self.min_confidence:
                    if not self.dry_run:
                        with transaction.atomic():
                            fh.opponent_fighter = opponent_fighter
                            fh.save()
                    
                    batch_stats['opponents_linked'] += 1
                    if confidence >= 0.9:
                        batch_stats['high_confidence_links'] += 1
                
                # Create missing fighter if requested and no match found
                elif not opponent_fighter and self.create_missing:
                    if not self.dry_run:
                        new_fighter = self.create_opponent_fighter(fh)
                        if new_fighter:
                            fh.opponent_fighter = new_fighter
                            fh.save()
                            batch_stats['fighters_created'] += 1
                    else:
                        batch_stats['fighters_created'] += 1
                        if self.verbose:
                            self.stdout.write(
                                f'  Would create: {fh.get_opponent_display_name()}'
                            )
                
                else:
                    batch_stats['skipped_low_confidence'] += 1
                
            except Exception as e:
                batch_stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing {fh}: {e}')
                )
        
        return batch_stats
    
    def create_opponent_fighter(self, fight_history):
        """Create a new Fighter record for an unmatched opponent"""
        try:
            fighter_data = {
                'first_name': fight_history.opponent_first_name,
                'last_name': fight_history.opponent_last_name or '',
                'data_source': 'fight_history_import',
                'data_quality_score': 0.3,  # Low score for minimal data
            }
            
            # Try to infer additional data from fight context
            if fight_history.event_date:
                fighter_data['last_data_update'] = datetime.now()
            
            fighter = Fighter.objects.create(**fighter_data)
            
            if self.verbose:
                self.stdout.write(
                    f'  Created fighter: {fighter.get_full_name()}'
                )
            
            return fighter
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create fighter for {fight_history.get_opponent_display_name()}: {e}')
            )
            return None
    
    def link_events_and_organizations(self, fight_histories):
        """Link fight histories to events and organizations where possible"""
        stats = {
            'events_linked': 0,
            'organizations_linked': 0
        }
        
        for fh in fight_histories:
            # Try to link to existing events
            if fh.event_name and fh.event_date and not fh.event:
                event = Event.objects.filter(
                    name__icontains=fh.event_name,
                    date=fh.event_date
                ).first()
                
                if event:
                    if not self.dry_run:
                        fh.event = event
                        fh.save()
                    stats['events_linked'] += 1
                    
                    if self.verbose:
                        self.stdout.write(f'  Linked event: {fh.event_name} -> {event.name}')
            
            # Try to link to organizations
            if fh.organization_name and not fh.organization:
                org = Organization.objects.filter(
                    name__icontains=fh.organization_name
                ).first()
                
                if org:
                    if not self.dry_run:
                        fh.organization = org
                        fh.save()
                    stats['organizations_linked'] += 1
                    
                    if self.verbose:
                        self.stdout.write(f'  Linked org: {fh.organization_name} -> {org.name}')
        
        return stats
    
    def print_final_statistics(self, stats):
        """Print comprehensive statistics"""
        self.stdout.write('\\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 LINKING STATISTICS'))
        self.stdout.write('='*50)
        
        self.stdout.write(f"Total Records Processed: {stats['total_processed']}")
        self.stdout.write(f"Opponents Linked: {stats['opponents_linked']}")
        self.stdout.write(f"High Confidence Links (≥90%): {stats['high_confidence_links']}")
        
        if self.create_missing:
            self.stdout.write(f"New Fighters Created: {stats['fighters_created']}")
        
        if self.link_events:
            self.stdout.write(f"Events Linked: {stats['events_linked']}")
            self.stdout.write(f"Organizations Linked: {stats['organizations_linked']}")
        
        self.stdout.write(f"Skipped (Low Confidence): {stats['skipped_low_confidence']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        # Calculate success rate
        if stats['total_processed'] > 0:
            success_rate = (stats['opponents_linked'] / stats['total_processed'] * 100)
            self.stdout.write(f"\\nSuccess Rate: {success_rate:.1f}%")
    
    def run_validation_checks(self):
        """Run network consistency validation"""
        self.stdout.write('\\n' + '='*50)
        self.stdout.write('🔍 NETWORK VALIDATION')
        self.stdout.write('='*50)
        
        # Get network statistics
        network_stats = NetworkConsistencyValidator.get_network_statistics()
        
        self.stdout.write(f"Total Fight Histories: {network_stats['total_fight_histories']}")
        self.stdout.write(f"Opponent Links: {network_stats['linked_opponents']} ({network_stats['opponent_link_percentage']:.1f}%)")
        self.stdout.write(f"Fight Links: {network_stats['linked_fights']} ({network_stats['fight_link_percentage']:.1f}%)")
        
        # Check for issues
        issues = NetworkConsistencyValidator.validate_fight_network()
        
        if issues:
            self.stdout.write('\\n⚠️  Issues Found:')
            for issue in issues:
                severity_style = {
                    'low': self.style.SUCCESS,
                    'medium': self.style.WARNING,
                    'high': self.style.ERROR,
                    'critical': self.style.ERROR
                }.get(issue['severity'], self.style.WARNING)
                
                self.stdout.write(
                    severity_style(f"  {issue['type']}: {issue['description']}")
                )
        else:
            self.stdout.write(self.style.SUCCESS('\\n✅ No network consistency issues found'))
        
        self.stdout.write('\\n' + '='*50)
        self.stdout.write('Network linking complete! 🎉')
        self.stdout.write('='*50)