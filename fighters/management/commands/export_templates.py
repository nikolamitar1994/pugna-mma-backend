"""
Management command to export existing entities as JSON templates.
Usage: python manage.py export_templates --type fighter --ids 1,2,3 --output /path/to/templates/
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
    help = 'Export existing entities as JSON templates for AI completion or reference'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['fighter', 'event', 'article'],
            required=True,
            help='Type of entities to export'
        )
        
        parser.add_argument(
            '--ids',
            type=str,
            help='Comma-separated list of entity IDs to export (exports all if not specified)'
        )
        
        parser.add_argument(
            '--output-dir',
            type=str,
            required=True,
            help='Output directory for template files'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of entities to export (default: 100)'
        )
        
        parser.add_argument(
            '--incomplete-only',
            action='store_true',
            help='Export only entities with low data quality scores'
        )
        
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty-print JSON output'
        )
    
    def handle(self, *args, **options):
        entity_type = options['type']
        ids_str = options.get('ids')
        output_dir = options['output_dir']
        limit = options['limit']
        incomplete_only = options['incomplete_only']
        pretty = options['pretty']
        
        # Parse entity IDs if provided
        entity_ids = None
        if ids_str:
            try:
                entity_ids = [id.strip() for id in ids_str.split(',')]
            except ValueError:
                raise CommandError("Invalid ID format. Use comma-separated list.")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export entities
        try:
            if entity_type == 'fighter':
                self.export_fighters(entity_ids, output_dir, limit, incomplete_only, pretty)
            elif entity_type == 'event':
                self.export_events(entity_ids, output_dir, limit, incomplete_only, pretty)
            elif entity_type == 'article':
                self.export_articles(entity_ids, output_dir, limit, incomplete_only, pretty)
                
        except Exception as e:
            raise CommandError(f"Export failed: {e}")
    
    def export_fighters(self, entity_ids, output_dir, limit, incomplete_only, pretty):
        """Export fighters as JSON templates"""
        # Build queryset
        queryset = Fighter.objects.all()
        
        if entity_ids:
            queryset = queryset.filter(id__in=entity_ids)
        
        if incomplete_only:
            queryset = queryset.filter(data_quality_score__lt=0.7)
        
        queryset = queryset[:limit]
        
        self.stdout.write(f"Exporting {queryset.count()} fighters...")
        
        exported_count = 0
        for fighter in queryset:
            template = JSONTemplateGenerator.export_fighter_to_template(fighter)
            
            # Generate filename
            safe_name = "".join(c for c in fighter.get_full_name() if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"fighter_{safe_name}_{fighter.id}.json"
            
            # Write template
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2 if pretty else None, ensure_ascii=False)
            
            exported_count += 1
            
            if exported_count % 10 == 0:
                self.stdout.write(f"Exported {exported_count} fighters...")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully exported {exported_count} fighter templates to {output_dir}")
        )
    
    def export_events(self, entity_ids, output_dir, limit, incomplete_only, pretty):
        """Export events as JSON templates"""
        # Build queryset
        queryset = Event.objects.select_related('organization')
        
        if entity_ids:
            queryset = queryset.filter(id__in=entity_ids)
        
        # For events, incomplete_only could filter by missing data
        if incomplete_only:
            queryset = queryset.filter(
                models.Q(venue='') | models.Q(city='') | models.Q(attendance__isnull=True)
            )
        
        queryset = queryset[:limit]
        
        self.stdout.write(f"Exporting {queryset.count()} events...")
        
        exported_count = 0
        for event in queryset:
            template = JSONTemplateGenerator.export_event_to_template(event)
            
            # Generate filename
            safe_name = "".join(c for c in event.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"event_{safe_name}_{event.id}.json"
            
            # Write template
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2 if pretty else None, ensure_ascii=False)
            
            exported_count += 1
            
            if exported_count % 10 == 0:
                self.stdout.write(f"Exported {exported_count} events...")
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully exported {exported_count} event templates to {output_dir}")
        )
    
    def export_articles(self, entity_ids, output_dir, limit, incomplete_only, pretty):
        """Export articles as JSON templates"""
        try:
            # Build queryset
            queryset = Article.objects.select_related('category', 'author')
            
            if entity_ids:
                queryset = queryset.filter(id__in=entity_ids)
            
            # For articles, incomplete_only could filter by missing SEO data or content
            if incomplete_only:
                queryset = queryset.filter(
                    models.Q(meta_description='') | models.Q(featured_image='') | 
                    models.Q(summary='')
                )
            
            queryset = queryset[:limit]
            
            self.stdout.write(f"Exporting {queryset.count()} articles...")
            
            exported_count = 0
            for article in queryset:
                # Create article template (would need to implement export method)
                template = self.create_article_template(article)
                
                # Generate filename
                safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')
                filename = f"article_{safe_title[:50]}_{article.id}.json"
                
                # Write template
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2 if pretty else None, ensure_ascii=False)
                
                exported_count += 1
                
                if exported_count % 10 == 0:
                    self.stdout.write(f"Exported {exported_count} articles...")
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully exported {exported_count} article templates to {output_dir}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Article export not fully implemented: {e}")
            )
    
    def create_article_template(self, article):
        """Create article template (placeholder implementation)"""
        # This would use JSONTemplateGenerator.export_article_to_template(article)
        # when that method is implemented
        return {
            "entity_type": "article",
            "template_version": "1.0",
            "generation_date": timezone.now().isoformat(),
            "article_data": {
                "content": {
                    "title": article.title,
                    "slug": article.slug,
                    "summary": getattr(article, 'summary', ''),
                    "content": article.content,
                },
                "categorization": {
                    "category": article.category.name if article.category else '',
                    "content_type": getattr(article, 'content_type', 'article')
                },
                "publishing": {
                    "status": article.status,
                    "author": article.author.email if article.author else '',
                    "publish_date": article.publish_date.isoformat() if article.publish_date else '',
                },
                "seo_data": {
                    "meta_title": getattr(article, 'meta_title', ''),
                    "meta_description": getattr(article, 'meta_description', ''),
                }
            }
        }