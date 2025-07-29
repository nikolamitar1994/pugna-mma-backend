"""
Management command to run AI completion on pending fighters.
Usage: python manage.py run_ai_completion --pending-fighters --confidence high
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import models
from fighters.models import PendingFighter, Fighter
from fighters.services.ai_completion import ai_completion_service


class Command(BaseCommand):
    help = 'Run AI completion on pending fighters or existing fighter profiles'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pending-fighters',
            action='store_true',
            help='Run completion on pending fighters'
        )
        
        parser.add_argument(
            '--existing-fighters',
            action='store_true',
            help='Run completion suggestions on existing fighters'
        )
        
        parser.add_argument(
            '--fighter-ids',
            type=str,
            help='Comma-separated list of fighter IDs to process'
        )
        
        parser.add_argument(
            '--confidence',
            type=str,
            choices=['high', 'medium', 'low'],
            help='Process only pending fighters with specified confidence level'
        )
        
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'approved'],
            default='pending',
            help='Process pending fighters with specified status (default: pending)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of fighters to process (default: 50)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )
    
    def handle(self, *args, **options):
        pending_fighters = options['pending_fighters']
        existing_fighters = options['existing_fighters']
        fighter_ids_str = options.get('fighter_ids')
        confidence = options.get('confidence')
        status = options['status']
        limit = options['limit']
        dry_run = options['dry_run']
        
        if not pending_fighters and not existing_fighters:
            raise CommandError("Must specify either --pending-fighters or --existing-fighters")
        
        # Parse fighter IDs if provided
        fighter_ids = None
        if fighter_ids_str:
            try:
                fighter_ids = [id.strip() for id in fighter_ids_str.split(',')]
            except ValueError:
                raise CommandError("Invalid fighter ID format. Use comma-separated list.")
        
        if pending_fighters:
            self.process_pending_fighters(fighter_ids, confidence, status, limit, dry_run)
        
        if existing_fighters:
            self.process_existing_fighters(fighter_ids, limit, dry_run)
    
    def process_pending_fighters(self, fighter_ids, confidence, status, limit, dry_run):
        """Process pending fighters with AI completion"""
        # Build queryset
        queryset = PendingFighter.objects.filter(status=status)
        
        if fighter_ids:
            queryset = queryset.filter(id__in=fighter_ids)
        
        if confidence:
            queryset = queryset.filter(confidence_level=confidence)
        
        # Only process fighters without AI suggestions or with low completion confidence
        queryset = queryset.filter(
            models.Q(ai_suggested_data__isnull=True) |
            models.Q(ai_suggested_data={}) |
            models.Q(ai_suggested_data__completion_confidence__lt=0.5)
        )
        
        queryset = queryset[:limit]
        
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING("No pending fighters found matching criteria"))
            return
        
        self.stdout.write(f"Processing {total_count} pending fighters...")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
            for pf in queryset:
                self.stdout.write(f"  Would process: {pf.get_display_name()} (confidence: {pf.confidence_level})")
            return
        
        # Process fighters
        processed_count = 0
        successful_count = 0
        failed_count = 0
        
        for pending_fighter in queryset:
            try:
                self.stdout.write(f"Processing: {pending_fighter.get_display_name()}")
                
                with transaction.atomic():
                    result = ai_completion_service.complete_pending_fighter(pending_fighter)
                
                if result['success']:
                    successful_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Completed {result['fields_completed']} fields "
                            f"(confidence: {result['confidence_score']:.2f})"
                        )
                    )
                else:
                    failed_count += 1
                    self.stdout.write(self.style.ERROR("  ✗ Completion failed"))
                
                processed_count += 1
                
                # Progress indicator
                if processed_count % 10 == 0:
                    self.stdout.write(f"Progress: {processed_count}/{total_count}")
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error processing {pending_fighter.get_display_name()}: {e}")
                )
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Processing complete:")
        self.stdout.write(f"  Total processed: {processed_count}")
        self.stdout.write(f"  Successful: {successful_count}")
        self.stdout.write(f"  Failed: {failed_count}")
        
        if successful_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\nAI completion successful for {successful_count} pending fighters")
            )
    
    def process_existing_fighters(self, fighter_ids, limit, dry_run):
        """Generate improvement suggestions for existing fighters"""
        # Build queryset
        queryset = Fighter.objects.all()
        
        if fighter_ids:
            queryset = queryset.filter(id__in=fighter_ids)
        else:
            # Focus on fighters with low data quality scores
            queryset = queryset.filter(data_quality_score__lt=0.7)
        
        queryset = queryset[:limit]
        
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING("No fighters found matching criteria"))
            return
        
        self.stdout.write(f"Analyzing {total_count} existing fighters...")
        
        if dry_run:
            self.stdout.write("DRY RUN - No changes will be made")
        
        # Process fighters
        high_priority_count = 0
        medium_priority_count = 0
        low_priority_count = 0
        
        for fighter in queryset:
            try:
                suggestions = ai_completion_service.suggest_improvements_for_fighter(fighter)
                
                priority = suggestions['improvement_priority']
                missing_count = len(suggestions['missing_fields'])
                
                if priority == 'high':
                    high_priority_count += 1
                    color_style = self.style.ERROR
                elif priority == 'medium':
                    medium_priority_count += 1
                    color_style = self.style.WARNING
                else:
                    low_priority_count += 1
                    color_style = self.style.SUCCESS
                
                self.stdout.write(
                    color_style(
                        f"{fighter.get_full_name()}: {priority} priority "
                        f"({missing_count} missing fields, quality: {fighter.data_quality_score:.2f})"
                    )
                )
                
                if suggestions['missing_fields']:
                    self.stdout.write(f"  Missing: {', '.join(suggestions['missing_fields'])}")
                
                if suggestions['quality_issues']:
                    self.stdout.write(f"  Issues: {'; '.join(suggestions['quality_issues'])}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error analyzing {fighter.get_full_name()}: {e}")
                )
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Analysis complete:")
        self.stdout.write(f"  High priority improvements: {high_priority_count}")
        self.stdout.write(f"  Medium priority improvements: {medium_priority_count}")  
        self.stdout.write(f"  Low priority improvements: {low_priority_count}")
        
        if high_priority_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nRecommendation: Focus on {high_priority_count} high-priority fighters first"
                )
            )