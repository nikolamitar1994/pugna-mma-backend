"""
Management command to generate JSON import templates.
Usage: python manage.py generate_json_templates --type fighter --output /path/to/template.json
"""

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from fighters.templates import JSONTemplateGenerator
from fighters.models import Fighter
from events.models import Event
from content.models import Article


class Command(BaseCommand):
    help = 'Generate JSON import templates for fighters, events, or articles'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['fighter', 'event', 'article'],
            required=True,
            help='Type of template to generate'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (defaults to stdout)'
        )
        
        parser.add_argument(
            '--from-existing',
            type=str,
            help='Generate template from existing entity (provide ID)'
        )
        
        parser.add_argument(
            '--partial-data',
            type=str,
            help='JSON string with partial data to pre-populate template'
        )
        
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty-print JSON output'
        )
    
    def handle(self, *args, **options):
        template_type = options['type']
        output_file = options.get('output')
        from_existing = options.get('from_existing')
        partial_data_str = options.get('partial_data')
        pretty = options.get('pretty', False)
        
        # Parse partial data if provided
        partial_data = None
        if partial_data_str:
            try:
                partial_data = json.loads(partial_data_str)
            except json.JSONDecodeError as e:
                raise CommandError(f"Invalid JSON in partial-data: {e}")
        
        # Generate template
        try:
            if from_existing:
                template = self.generate_from_existing(template_type, from_existing)
            else:
                template = self.generate_new_template(template_type, partial_data)
                
        except Exception as e:
            raise CommandError(f"Error generating template: {e}")
        
        # Format output
        indent = 2 if pretty else None
        json_output = json.dumps(template, indent=indent, ensure_ascii=False)
        
        # Write output
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            self.stdout.write(
                self.style.SUCCESS(f"Template written to {output_file}")
            )
        else:
            self.stdout.write(json_output)
    
    def generate_new_template(self, template_type, partial_data):
        """Generate new template with optional partial data"""
        if template_type == 'fighter':
            return JSONTemplateGenerator.generate_fighter_template(partial_data)
        elif template_type == 'event':
            return JSONTemplateGenerator.generate_event_template(partial_data)
        elif template_type == 'article':
            return JSONTemplateGenerator.generate_article_template(partial_data)
        else:
            raise CommandError(f"Unknown template type: {template_type}")
    
    def generate_from_existing(self, template_type, entity_id):
        """Generate template from existing entity"""
        try:
            if template_type == 'fighter':
                fighter = Fighter.objects.get(id=entity_id)
                return JSONTemplateGenerator.export_fighter_to_template(fighter)
            elif template_type == 'event':
                event = Event.objects.get(id=entity_id)
                return JSONTemplateGenerator.export_event_to_template(event)
            elif template_type == 'article':
                article = Article.objects.get(id=entity_id)
                # Add export method for articles
                raise CommandError("Article export not yet implemented")
            else:
                raise CommandError(f"Unknown template type: {template_type}")
                
        except Fighter.DoesNotExist:
            raise CommandError(f"Fighter with ID {entity_id} not found")
        except Event.DoesNotExist:
            raise CommandError(f"Event with ID {entity_id} not found")
        except Article.DoesNotExist:
            raise CommandError(f"Article with ID {entity_id} not found")