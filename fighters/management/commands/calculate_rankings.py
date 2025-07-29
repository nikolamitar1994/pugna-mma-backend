"""
Django management command to calculate fighter rankings.
Usage: python manage.py calculate_rankings [--weight-class] [--organization] [--p4p]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from organizations.models import WeightClass, Organization
from fighters.ranking_service import ranking_service


class Command(BaseCommand):
    help = 'Calculate and update fighter rankings'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--weight-class',
            type=str,
            help='Calculate rankings for specific weight class (e.g., "Heavyweight")'
        )
        parser.add_argument(
            '--organization',
            type=str,
            help='Calculate rankings for specific organization (e.g., "UFC")'
        )
        parser.add_argument(
            '--p4p',
            action='store_true',
            help='Calculate pound-for-pound rankings'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Calculate all rankings (divisional and P4P)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be calculated without making changes'
        )
    
    def handle(self, *args, **options):
        """Execute the ranking calculation command."""
        
        try:
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN MODE - No changes will be made')
                )
            
            # Parse weight class if provided
            weight_class = None
            if options['weight_class']:
                try:
                    weight_class = WeightClass.objects.get(
                        name__icontains=options['weight_class']
                    )
                    self.stdout.write(f"Using weight class: {weight_class}")
                except WeightClass.DoesNotExist:
                    raise CommandError(f"Weight class '{options['weight_class']}' not found")
                except WeightClass.MultipleObjectsReturned:
                    weight_classes = WeightClass.objects.filter(
                        name__icontains=options['weight_class']
                    )
                    raise CommandError(
                        f"Multiple weight classes found: {', '.join(wc.name for wc in weight_classes)}"
                    )
            
            # Parse organization if provided
            organization = None
            if options['organization']:
                try:
                    organization = Organization.objects.get(
                        Q(name__icontains=options['organization']) |
                        Q(abbreviation__icontains=options['organization'])
                    )
                    self.stdout.write(f"Using organization: {organization}")
                except Organization.DoesNotExist:
                    raise CommandError(f"Organization '{options['organization']}' not found")
                except Organization.MultipleObjectsReturned:
                    orgs = Organization.objects.filter(
                        Q(name__icontains=options['organization']) |
                        Q(abbreviation__icontains=options['organization'])
                    )
                    raise CommandError(
                        f"Multiple organizations found: {', '.join(org.name for org in orgs)}"
                    )
            
            if options['dry_run']:
                return self._dry_run(weight_class, organization, options)
            
            # Execute calculations
            results = {}
            
            if options['p4p'] or options['all']:
                self.stdout.write("Calculating pound-for-pound rankings...")
                p4p_results = ranking_service.recalculate_pound_for_pound()
                results.update(p4p_results)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ P4P rankings updated: {p4p_results['p4p_rankings_updated']} fighters"
                    )
                )
            
            if not options['p4p'] or options['all']:
                self.stdout.write("Calculating divisional rankings...")
                divisional_results = ranking_service.calculate_all_rankings(
                    weight_class=weight_class,
                    organization=organization
                )
                results.update(divisional_results)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Divisional rankings updated: {divisional_results['rankings_updated']} fighters"
                    )
                )
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🏆 Ranking calculation complete!\n"
                    f"Fighters processed: {results.get('fighters_processed', 0)}\n"
                    f"Statistics updated: {results.get('statistics_updated', 0)}\n"
                    f"Rankings updated: {results.get('rankings_updated', 0)}\n"
                    f"P4P rankings updated: {results.get('p4p_rankings_updated', 0)}"
                )
            )
            
        except Exception as e:
            raise CommandError(f"Ranking calculation failed: {str(e)}")
    
    def _dry_run(self, weight_class, organization, options):
        """Show what would be calculated without making changes."""
        
        from fighters.models import Fighter
        
        self.stdout.write("=== DRY RUN ANALYSIS ===\n")
        
        # Show eligible fighters
        if weight_class or organization:
            fighters = Fighter.objects.filter(is_active=True, total_fights__gt=0)
            
            if weight_class:
                fighters = fighters.filter(
                    fight_history__weight_class=weight_class
                ).distinct()
            
            if organization:
                fighters = fighters.filter(
                    fight_history__organization=organization
                ).distinct()
            
            self.stdout.write(f"Eligible fighters: {fighters.count()}")
            
            if fighters.count() <= 20:
                self.stdout.write("\nFighters to be ranked:")
                for i, fighter in enumerate(fighters[:20], 1):
                    self.stdout.write(f"  {i}. {fighter.get_full_name()} ({fighter.get_record_string()})")
            else:
                self.stdout.write(f"\nFirst 20 fighters to be ranked:")
                for i, fighter in enumerate(fighters[:20], 1):
                    self.stdout.write(f"  {i}. {fighter.get_full_name()} ({fighter.get_record_string()})")
                self.stdout.write(f"  ... and {fighters.count() - 20} more")
        
        if options['p4p'] or options['all']:
            self.stdout.write("\n📊 P4P calculation would include top 3 from each weight class")
            weight_classes = WeightClass.objects.filter(is_active=True)
            self.stdout.write(f"Active weight classes: {weight_classes.count()}")
        
        self.stdout.write("\n✅ Dry run complete - no changes made")
        
        from django.db.models import Q
        return