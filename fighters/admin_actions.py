"""
Custom Django admin actions for JSON import and export functionality.
"""

import json
import tempfile
import zipfile
from io import BytesIO
from django.contrib import admin
from django.contrib.admin import helpers
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.db import transaction

from .models import Fighter, PendingFighter
from .templates import JSONTemplateGenerator, JSONImportProcessor


class JSONImportExportMixin:
    """Mixin to add JSON import/export functionality to admin classes"""
    
    def get_urls(self):
        """Add custom URLs for import/export"""
        urls = super().get_urls()
        custom_urls = [
            path('import-json/', self.admin_site.admin_view(self.import_json_view), name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_import_json'),
            path('export-json/', self.admin_site.admin_view(self.export_json_view), name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_export_json'),
            path('bulk-import/', self.admin_site.admin_view(self.bulk_import_view), name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_bulk_import'),
        ]
        return custom_urls + urls
    
    def import_json_view(self, request):
        """View for importing single JSON template"""
        if request.method == 'POST':
            return self.process_json_import(request)
        
        # Render import form
        context = {
            'title': f'Import {self.model._meta.verbose_name} from JSON',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'original': None,
        }
        
        return TemplateResponse(
            request, 
            'admin/fighters/import_json_form.html', 
            context
        )
    
    def export_json_view(self, request):
        """View for exporting selected objects as JSON templates"""
        if request.method == 'POST':
            return self.process_json_export(request)
        
        # Get selected objects from changelist
        selected_ids = request.GET.getlist('ids')
        if not selected_ids:
            messages.error(request, "No objects selected for export")
            return HttpResponseRedirect(reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'))
        
        queryset = self.model.objects.filter(id__in=selected_ids)
        
        context = {
            'title': f'Export {queryset.count()} {self.model._meta.verbose_name_plural} as JSON',
            'queryset': queryset,
            'opts': self.model._meta,
            'selected_ids': selected_ids,
        }
        
        return TemplateResponse(
            request,
            'admin/fighters/export_json_form.html',
            context
        )
    
    def bulk_import_view(self, request):
        """View for bulk importing multiple JSON files"""
        if request.method == 'POST':
            return self.process_bulk_import(request)
        
        context = {
            'title': f'Bulk Import {self.model._meta.verbose_name_plural} from JSON',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(
            request,
            'admin/fighters/bulk_import_form.html',
            context
        )
    
    def process_json_import(self, request):
        """Process single JSON file import"""
        try:
            uploaded_file = request.FILES.get('json_file')
            if not uploaded_file:
                messages.error(request, "No file uploaded")
                return HttpResponseRedirect(request.path)
            
            # Read and parse JSON
            content = uploaded_file.read().decode('utf-8')
            template_data = json.loads(content)
            
            # Validate entity type
            entity_type = template_data.get('entity_type')
            expected_type = self.model._meta.model_name.lower()
            
            if entity_type != expected_type:
                messages.error(
                    request, 
                    f"JSON template is for {entity_type}, but you're importing into {expected_type}"
                )
                return HttpResponseRedirect(request.path)
            
            # Import based on model type
            if self.model == Fighter:
                return self.import_fighter_json(request, template_data)
            elif self.model == PendingFighter:
                return self.import_pending_fighter_json(request, template_data)
            else:
                messages.error(request, f"Import not supported for {self.model._meta.verbose_name}")
                return HttpResponseRedirect(request.path)
                
        except json.JSONDecodeError as e:
            messages.error(request, f"Invalid JSON file: {e}")
            return HttpResponseRedirect(request.path)
        except Exception as e:
            messages.error(request, f"Import error: {e}")
            return HttpResponseRedirect(request.path)
    
    def import_fighter_json(self, request, template_data):
        """Import Fighter from JSON template"""
        # Validate template
        validation = JSONImportProcessor.validate_fighter_template(template_data)
        
        if not validation['is_valid']:
            messages.error(request, f"Template validation failed: {'; '.join(validation['errors'])}")
            return HttpResponseRedirect(request.path)
        
        if validation['warnings']:
            for warning in validation['warnings']:
                messages.warning(request, f"Warning: {warning}")
        
        # Process template
        fighter_data = JSONImportProcessor.process_fighter_template(template_data)
        
        # Check for existing fighter
        existing_fighter = Fighter.objects.filter(
            first_name__iexact=fighter_data['first_name'],
            last_name__iexact=fighter_data.get('last_name', '')
        ).first()
        
        if existing_fighter:
            messages.warning(
                request, 
                f"Fighter {existing_fighter.get_full_name()} already exists. "
                f"Use update action to modify existing fighters."
            )
            return HttpResponseRedirect(request.path)
        
        try:
            with transaction.atomic():
                fighter = Fighter.objects.create(**fighter_data)
                
            messages.success(
                request, 
                f"Successfully imported fighter: {fighter.get_full_name()} "
                f"(Data quality: {validation['completeness_score']:.1%})"
            )
            
            # Redirect to the created fighter
            return HttpResponseRedirect(
                reverse('admin:fighters_fighter_change', args=[fighter.pk])
            )
            
        except Exception as e:
            messages.error(request, f"Error creating fighter: {e}")
            return HttpResponseRedirect(request.path)
    
    def import_pending_fighter_json(self, request, template_data):
        """Import PendingFighter from JSON template"""
        # Extract basic info from template
        fighter_data = template_data.get('fighter_data', {})
        personal_info = fighter_data.get('personal_info', {})
        source_context = template_data.get('source_context', {})
        
        try:
            with transaction.atomic():
                pending_fighter = PendingFighter.objects.create(
                    first_name=personal_info.get('first_name', ''),
                    last_name=personal_info.get('last_name', ''),
                    full_name_raw=f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}".strip(),
                    nickname=personal_info.get('nickname', ''),
                    nationality=personal_info.get('nationality', ''),
                    source='manual',
                    ai_suggested_data=fighter_data,
                    confidence_level='high'  # Manual import assumed high confidence
                )
                
                # Run fuzzy matching
                pending_fighter.run_fuzzy_matching()
            
            messages.success(
                request,
                f"Successfully imported pending fighter: {pending_fighter.get_display_name()}"
            )
            
            return HttpResponseRedirect(
                reverse('admin:fighters_pendingfighter_change', args=[pending_fighter.pk])
            )
            
        except Exception as e:
            messages.error(request, f"Error creating pending fighter: {e}")
            return HttpResponseRedirect(request.path)
    
    def process_json_export(self, request):
        """Process JSON export of selected objects"""
        selected_ids = request.POST.getlist('selected_ids')
        export_format = request.POST.get('export_format', 'individual')
        
        if not selected_ids:
            messages.error(request, "No objects selected for export")
            return HttpResponseRedirect(request.path)
        
        queryset = self.model.objects.filter(id__in=selected_ids)
        
        if export_format == 'zip':
            return self.export_as_zip(queryset)
        else:
            return self.export_as_individual_files(queryset)
    
    def export_as_zip(self, queryset):
        """Export multiple objects as a ZIP file"""
        # Create in-memory ZIP file
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for obj in queryset:
                if isinstance(obj, Fighter):
                    template = JSONTemplateGenerator.export_fighter_to_template(obj)
                    filename = f"fighter_{obj.get_full_name().replace(' ', '_')}_{obj.id}.json"
                else:
                    # Handle other model types
                    continue
                
                json_content = json.dumps(template, indent=2, ensure_ascii=False)
                zip_file.writestr(filename, json_content)
        
        zip_buffer.seek(0)
        
        # Create response
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{self.model._meta.verbose_name_plural}_export.zip"'
        
        return response
    
    def export_as_individual_files(self, queryset):
        """Export first object as individual JSON file"""
        obj = queryset.first()
        
        if isinstance(obj, Fighter):
            template = JSONTemplateGenerator.export_fighter_to_template(obj)
            filename = f"fighter_{obj.get_full_name().replace(' ', '_')}_{obj.id}.json"
        else:
            messages.error(request, f"Export not supported for {type(obj)}")
            return HttpResponseRedirect(request.path)
        
        json_content = json.dumps(template, indent=2, ensure_ascii=False)
        
        response = HttpResponse(json_content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def process_bulk_import(self, request):
        """Process bulk import from ZIP file or multiple JSON files"""
        uploaded_files = request.FILES.getlist('json_files')
        zip_file = request.FILES.get('zip_file')
        
        if not uploaded_files and not zip_file:
            messages.error(request, "No files uploaded")
            return HttpResponseRedirect(request.path)
        
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            if zip_file:
                # Process ZIP file
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    for file_name in zip_ref.namelist():
                        if file_name.endswith('.json'):
                            try:
                                with zip_ref.open(file_name) as json_file:
                                    content = json_file.read().decode('utf-8')
                                    template_data = json.loads(content)
                                    
                                    success = self.import_single_template(template_data, file_name)
                                    results['processed'] += 1
                                    
                                    if success:
                                        results['successful'] += 1
                                    else:
                                        results['failed'] += 1
                                        
                            except Exception as e:
                                results['failed'] += 1
                                results['errors'].append(f"{file_name}: {e}")
            else:
                # Process individual files
                for uploaded_file in uploaded_files:
                    try:
                        content = uploaded_file.read().decode('utf-8')
                        template_data = json.loads(content)
                        
                        success = self.import_single_template(template_data, uploaded_file.name)
                        results['processed'] += 1
                        
                        if success:
                            results['successful'] += 1
                        else:
                            results['failed'] += 1
                            
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append(f"{uploaded_file.name}: {e}")
            
            # Show results
            if results['successful'] > 0:
                messages.success(
                    request, 
                    f"Bulk import completed: {results['successful']} successful, "
                    f"{results['failed']} failed out of {results['processed']} processed"
                )
            
            if results['errors']:
                for error in results['errors'][:5]:  # Show first 5 errors
                    messages.error(request, error)
                
                if len(results['errors']) > 5:
                    messages.warning(request, f"... and {len(results['errors']) - 5} more errors")
            
            return HttpResponseRedirect(
                reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist')
            )
            
        except Exception as e:
            messages.error(request, f"Bulk import error: {e}")
            return HttpResponseRedirect(request.path)
    
    def import_single_template(self, template_data, filename):
        """Import a single JSON template (returns True if successful)"""
        try:
            entity_type = template_data.get('entity_type')
            expected_type = self.model._meta.model_name.lower()
            
            if entity_type != expected_type:
                return False
            
            if self.model == Fighter:
                validation = JSONImportProcessor.validate_fighter_template(template_data)
                if not validation['is_valid']:
                    return False
                
                fighter_data = JSONImportProcessor.process_fighter_template(template_data)
                
                # Check for existing
                existing = Fighter.objects.filter(
                    first_name__iexact=fighter_data['first_name'],
                    last_name__iexact=fighter_data.get('last_name', '')
                ).exists()
                
                if existing:
                    return False  # Skip existing
                
                Fighter.objects.create(**fighter_data)
                return True
            
            return False
            
        except Exception:
            return False


def export_selected_as_json_templates(modeladmin, request, queryset):
    """Admin action to export selected objects as JSON templates"""
    selected_ids = [str(obj.pk) for obj in queryset]
    
    # Redirect to export view with selected IDs
    url = reverse(f'admin:{modeladmin.model._meta.app_label}_{modeladmin.model._meta.model_name}_export_json')
    return HttpResponseRedirect(f"{url}?ids={'&ids='.join(selected_ids)}")

export_selected_as_json_templates.short_description = "Export selected as JSON templates"


def create_fighter_from_pending(modeladmin, request, queryset):
    """Admin action to create Fighter records from approved PendingFighter records"""
    if modeladmin.model != PendingFighter:
        messages.error(request, "This action is only available for Pending Fighters")
        return
    
    approved_fighters = queryset.filter(status='approved')
    created_count = 0
    error_count = 0
    
    for pending_fighter in approved_fighters:
        try:
            with transaction.atomic():
                fighter = pending_fighter.create_fighter_from_pending(request.user)
                created_count += 1
        except Exception as e:
            error_count += 1
            messages.error(request, f"Error creating fighter from {pending_fighter.get_display_name()}: {e}")
    
    if created_count > 0:
        messages.success(request, f"Successfully created {created_count} fighters from pending records")
    
    if error_count > 0:
        messages.warning(request, f"Failed to create {error_count} fighters")

create_fighter_from_pending.short_description = "Create fighters from approved pending records"