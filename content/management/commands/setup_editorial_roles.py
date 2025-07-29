"""
Management command to set up editorial roles and permissions.

This command creates the necessary Django groups, permissions, and
sets up the editorial workflow system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from content.models import Article
from content.permissions import ContentPermissions, ROLE_PERMISSIONS
from content.services import RoleManagementService


class Command(BaseCommand):
    help = 'Set up editorial roles, groups, and permissions for content management'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of groups and permissions',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        verbosity = 2 if options['verbose'] else 1
        force = options['force']
        
        try:
            with transaction.atomic():
                self.setup_permissions(verbosity, force)
                self.setup_groups(verbosity, force)
                
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS('Successfully set up editorial roles and permissions')
                    )
                    
        except Exception as e:
            raise CommandError(f'Error setting up editorial roles: {e}')
    
    def setup_permissions(self, verbosity, force):
        """Create custom content permissions."""
        if verbosity >= 1:
            self.stdout.write('Creating custom permissions...')
        
        content_type = ContentType.objects.get_for_model(Article)
        created_count = 0
        
        for codename, name in ContentPermissions.CUSTOM_PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            
            if created:
                created_count += 1
                if verbosity >= 2:
                    self.stdout.write(f'  Created permission: {codename} - {name}')
            elif force:
                # Update name if it has changed
                if permission.name != name:
                    permission.name = name
                    permission.save()
                    if verbosity >= 2:
                        self.stdout.write(f'  Updated permission: {codename} - {name}')
        
        if verbosity >= 1:
            self.stdout.write(f'Created {created_count} new permissions')
    
    def setup_groups(self, verbosity, force):
        """Create editorial role groups with permissions."""
        if verbosity >= 1:
            self.stdout.write('Setting up editorial groups...')
        
        content_type = ContentType.objects.get_for_model(Article)
        
        for group_name, permission_codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                if verbosity >= 2:
                    self.stdout.write(f'  Created group: {group_name}')
            elif verbosity >= 2:
                self.stdout.write(f'  Group exists: {group_name}')
            
            # Clear existing permissions if force or new group
            if force or created:
                group.permissions.clear()
                
                # Add permissions to group
                added_count = 0
                for codename in permission_codenames:
                    try:
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type=content_type
                        )
                        group.permissions.add(permission)
                        added_count += 1
                        
                        if verbosity >= 2:
                            self.stdout.write(f'    Added permission: {codename}')
                            
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'    Permission not found: {codename} for group {group_name}'
                            )
                        )
                
                if verbosity >= 1:
                    self.stdout.write(f'  Added {added_count} permissions to {group_name}')
    
    def display_summary(self):
        """Display a summary of created roles and permissions."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('EDITORIAL ROLES SUMMARY')
        self.stdout.write('='*50)
        
        for group_name, permission_codenames in ROLE_PERMISSIONS.items():
            role_name = group_name.replace('content_', '').title()
            self.stdout.write(f'\n{role_name} Role ({group_name}):')
            
            for codename in permission_codenames:
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=ContentType.objects.get_for_model(Article)
                    )
                    self.stdout.write(f'  ✓ {permission.name}')
                except Permission.DoesNotExist:
                    self.stdout.write(f'  ✗ {codename} (NOT FOUND)')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('To assign roles to users, use:')
        self.stdout.write('python manage.py assign_editorial_role <username> <role>')
        self.stdout.write('Available roles: author, editor, publisher, admin')
        self.stdout.write('='*50)