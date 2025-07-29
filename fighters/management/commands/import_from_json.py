"""
Management command to import entities from JSON templates.
Usage: python manage.py import_from_json --file /path/to/template.json --dry-run
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from fighters.templates import JSONImportProcessor
from fighters.models import Fighter, PendingFighter
from events.models import Event
from content.models import Article
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Import entities from JSON templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to JSON template file'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and preview import without creating entities'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip validation warnings and proceed with import'
        )
        
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing entities if found (instead of creating duplicates)'
        )
    
    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        force = options['force']
        update_existing = options['update_existing']
        
        # Load JSON template
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in file: {e}")
        
        # Determine entity type
        entity_type = template_data.get('entity_type')
        if not entity_type:
            raise CommandError("Template missing 'entity_type' field")
        
        if entity_type not in ['fighter', 'event', 'article']:
            raise CommandError(f"Unknown entity type: {entity_type}")
        
        # Process import
        try:
            if entity_type == 'fighter':
                self.import_fighter(template_data, dry_run, force, update_existing)
            elif entity_type == 'event':
                self.import_event(template_data, dry_run, force, update_existing)
            elif entity_type == 'article':
                self.import_article(template_data, dry_run, force, update_existing)
                
        except Exception as e:
            raise CommandError(f"Import failed: {e}")
    
    def import_fighter(self, template_data, dry_run, force, update_existing):
        """Import fighter from JSON template"""
        # Validate template
        validation = JSONImportProcessor.validate_fighter_template(template_data)
        
        self.stdout.write(f"Validation results:")
        self.stdout.write(f"  Valid: {validation['is_valid']}")
        self.stdout.write(f"  Completeness: {validation['completeness_score']:.1%}")
        
        if validation['errors']:
            self.stdout.write(self.style.ERROR("Errors:"))
            for error in validation['errors']:
                self.stdout.write(f"  - {error}")
        
        if validation['warnings']:
            self.stdout.write(self.style.WARNING("Warnings:"))
            for warning in validation['warnings']:
                self.stdout.write(f"  - {warning}")
        
        if not validation['is_valid']:
            raise CommandError("Template validation failed")
        
        if validation['warnings'] and not force:
            raise CommandError("Template has warnings. Use --force to proceed anyway.")
        
        # Process template data
        fighter_data = JSONImportProcessor.process_fighter_template(template_data)
        
        self.stdout.write(f"\\nProcessed fighter data:")
        self.stdout.write(f"  Name: {fighter_data.get('first_name', '')} {fighter_data.get('last_name', '')}")
        self.stdout.write(f"  Nationality: {fighter_data.get('nationality', 'Unknown')}")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS("\\nDry run complete - no changes made"))
            return
        
        # Check for existing fighter
        existing_fighter = None
        if update_existing:
            existing_fighter = Fighter.objects.filter(
                first_name__iexact=fighter_data['first_name'],
                last_name__iexact=fighter_data.get('last_name', '')
            ).first()
        
        with transaction.atomic():
            if existing_fighter and update_existing:
                # Update existing fighter
                for field, value in fighter_data.items():
                    setattr(existing_fighter, field, value)
                existing_fighter.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"Updated fighter: {existing_fighter.get_full_name()}")
                )
            else:
                # Create new fighter
                fighter = Fighter.objects.create(**fighter_data)
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created fighter: {fighter.get_full_name()}")
                )
    
    def import_event(self, template_data, dry_run, force, update_existing):
        """Import event from JSON template"""
        # TODO: Implement event import logic
        self.stdout.write(self.style.WARNING("Event import not yet implemented"))
    
    def import_article(self, template_data, dry_run, force, update_existing):
        """Import article from JSON template"""
        # TODO: Implement article import logic
        self.stdout.write(self.style.WARNING("Article import not yet implemented"))