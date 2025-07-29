"""
Demonstration command for the complete pending entities and scraping workflow.
Shows how scraped event data flows through the pending entities system.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from fighters.services.scraping_integration import scraping_integration_service
from fighters.models import PendingFighter


class Command(BaseCommand):
    help = 'Demonstrate the pending entities and scraping workflow with sample data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--event-name',
            type=str,
            default='UFC 300: Pereira vs Hill',
            help='Name of the sample event to process'
        )
        
        parser.add_argument(
            '--clear-pending',
            action='store_true',
            help='Clear existing pending fighters before demo'
        )
    
    def handle(self, *args, **options):
        event_name = options['event_name']
        clear_pending = options['clear_pending']
        
        if clear_pending:
            deleted_count = PendingFighter.objects.all().delete()[0]
            self.stdout.write(f"Cleared {deleted_count} existing pending fighters")
        
        self.stdout.write("="*60)
        self.stdout.write("PENDING ENTITIES & SCRAPING WORKFLOW DEMONSTRATION")
        self.stdout.write("="*60)
        
        # Sample scraped event data
        sample_event_data = {
            'name': event_name,
            'date': '2024-04-13',
            'organization': 'UFC',
            'url': 'https://example.com/ufc-300',
            'fighters': [
                {
                    'name': 'Alex Pereira',
                    'nationality': 'Brazil',
                    'weight_class': 'Light Heavyweight',
                    'record': '9-2-0',
                    'corner': 'red'
                },
                {
                    'name': 'Jamahal Hill',
                    'nationality': 'USA',
                    'weight_class': 'Light Heavyweight', 
                    'record': '12-1-0',
                    'corner': 'blue'
                },
                {
                    'name': 'Zhang Weili',
                    'nationality': 'China',
                    'weight_class': 'Strawweight',
                    'record': '24-3-0'
                },
                {
                    'name': 'Yan Xiaonan',
                    'nationality': 'China',
                    'weight_class': 'Strawweight',
                    'record': '17-3-0'
                },
                {
                    'name': 'New Fighter',  # This will be a new pending fighter
                    'nationality': 'Unknown',
                    'weight_class': 'Welterweight',
                    'record': '5-0-0'
                },
                {
                    'name': 'Another Newbie',  # Another new fighter
                    'nationality': 'Canada',
                    'weight_class': 'Featherweight',
                    'record': '3-1-0'
                }
            ]
        }
        
        self.stdout.write(f"Processing sample event: {event_name}")
        self.stdout.write(f"Fighters to process: {len(sample_event_data['fighters'])}")
        self.stdout.write("")
        
        # Process the scraped event
        results = scraping_integration_service.process_scraped_event_fighters(sample_event_data)
        
        # Display results
        self.stdout.write("PROCESSING RESULTS:")
        self.stdout.write("-" * 40)
        
        for result in results['processed_fighters']:
            action = result['action']
            fighter_name = result['fighter_name']
            
            if action == 'created_pending':
                pending_fighter = result['pending_fighter']
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ NEW PENDING: {fighter_name} "
                        f"(confidence: {pending_fighter.confidence_level})"
                    )
                )
                
                if result['potential_matches']:
                    self.stdout.write(f"  Potential matches found: {len(result['potential_matches'])}")
                    for match in result['potential_matches']:
                        self.stdout.write(
                            f"    - {match['name']} (confidence: {match['confidence']:.2f})"
                        )
                
            elif action == 'identified_duplicate':
                existing_fighter = result['existing_fighter']
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ DUPLICATE: {fighter_name} matches existing fighter "
                        f"{existing_fighter.get_full_name()} "
                        f"(confidence: {result['confidence']:.2f})"
                    )
                )
                
            elif action == 'updated_pending':
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f"ℹ UPDATED: {fighter_name} (existing pending fighter updated)"
                    )
                )
            
            self.stdout.write("")
        
        # Show errors if any
        if results['errors']:
            self.stdout.write(self.style.ERROR("ERRORS:"))
            for error in results['errors']:
                self.stdout.write(f"  {error}")
            self.stdout.write("")
        
        # Generate comprehensive report
        report = scraping_integration_service.generate_scraping_report()
        
        self.stdout.write("COMPREHENSIVE REPORT:")
        self.stdout.write("-" * 40)
        
        stats = report['statistics']
        self.stdout.write(f"Fighters processed: {stats['fighters_processed']}")
        self.stdout.write(f"New pending created: {stats['new_pending_created']}")
        self.stdout.write(f"Existing pending updated: {stats['existing_pending_updated']}")
        self.stdout.write(f"Duplicates found: {stats['duplicates_found']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        self.stdout.write("")
        
        self.stdout.write(f"Pending review (low confidence): {report['pending_review_count']}")
        self.stdout.write(f"High confidence new fighters: {report['high_confidence_new_fighters']}")
        self.stdout.write(f"Auto-identified duplicates: {report['auto_identified_duplicates']}")
        self.stdout.write("")
        
        if report['recommendations']:
            self.stdout.write("RECOMMENDATIONS:")
            for recommendation in report['recommendations']:
                self.stdout.write(f"  • {recommendation}")
            self.stdout.write("")
        
        # Show next steps
        self.stdout.write("NEXT STEPS:")
        self.stdout.write("-" * 40)
        self.stdout.write("1. Review pending fighters in Django admin:")
        self.stdout.write("   /admin/fighters/pendingfighter/")
        self.stdout.write("")
        self.stdout.write("2. For high-confidence fighters, use admin action:")
        self.stdout.write("   'Approve selected for Fighter creation'")
        self.stdout.write("")
        self.stdout.write("3. For low-confidence fighters, review potential matches:")
        self.stdout.write("   Use 'Mark selected as duplicates' if confirmed")
        self.stdout.write("")
        self.stdout.write("4. Generate JSON templates for AI completion:")
        self.stdout.write("   Use 'Generate JSON templates for AI completion'")
        self.stdout.write("")
        self.stdout.write("5. Run AI completion (if configured):")
        self.stdout.write("   python manage.py run_ai_completion --pending-fighters")
        self.stdout.write("")
        
        # Show sample workflow commands
        self.stdout.write("SAMPLE WORKFLOW COMMANDS:")
        self.stdout.write("-" * 40)
        self.stdout.write("# Export pending fighters as JSON templates")
        self.stdout.write("python manage.py export_templates --type fighter --incomplete-only --output-dir /tmp/templates --pretty")
        self.stdout.write("")
        self.stdout.write("# Import completed templates")
        self.stdout.write("python manage.py import_from_json --file /tmp/completed_fighter.json")
        self.stdout.write("")
        self.stdout.write("# Run AI completion on pending fighters")
        self.stdout.write("python manage.py run_ai_completion --pending-fighters --confidence high --limit 10")
        self.stdout.write("")
        
        self.stdout.write("="*60)
        self.stdout.write("DEMONSTRATION COMPLETE")
        self.stdout.write("="*60)