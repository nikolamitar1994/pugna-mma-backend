"""
Management command to assign editorial roles to users.

This command assigns users to editorial role groups and updates their profiles.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from users.models import UserProfile
from content.services import RoleManagementService

User = get_user_model()


class Command(BaseCommand):
    help = 'Assign editorial role to a user'
    
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username or email of the user')
        parser.add_argument(
            'role', 
            type=str, 
            choices=['author', 'editor', 'publisher', 'admin'],
            help='Editorial role to assign'
        )
        
        parser.add_argument(
            '--create-profile',
            action='store_true',
            help='Create user profile if it does not exist',
        )
        
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='List all users and their current roles',
        )
    
    def handle(self, *args, **options):
        if options['list_users']:
            self.list_users()
            return
        
        username = options['username']
        role = options['role']
        create_profile = options['create_profile']
        
        try:
            with transaction.atomic():
                success = self.assign_role(username, role, create_profile)
                
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully assigned {role} role to {username}'
                        )
                    )
                else:
                    raise CommandError(f'Failed to assign role to {username}')
                    
        except Exception as e:
            raise CommandError(f'Error assigning role: {e}')
    
    def assign_role(self, username, role, create_profile=False):
        """Assign editorial role to user."""
        # Find user by username or email
        try:
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User not found: {username}')
        
        # Check if user is active
        if not user.is_active:
            raise CommandError(f'User {username} is not active')
        
        # Use role management service
        service = RoleManagementService()
        success = service.assign_user_role(user, role)
        
        if not success:
            return False
        
        # Create or update user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'editorial_role': role}
        )
        
        if not created:
            profile.editorial_role = role
            profile.save()
        
        # Update activity stats
        profile.update_activity_stats()
        
        self.stdout.write(f'User: {user.get_full_name()} ({user.username})')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'Role: {role.title()}')
        self.stdout.write(f'Profile: {"Created" if created else "Updated"}')
        
        # Show user's permissions
        self.show_user_permissions(user, role)
        
        return True
    
    def show_user_permissions(self, user, role):
        """Display user's editorial permissions."""
        self.stdout.write('\nAssigned Permissions:')
        
        service = RoleManagementService()
        permissions = service.get_role_permissions(role)
        
        for permission in permissions:
            try:
                # Convert permission codename to readable name
                from django.contrib.auth.models import Permission
                from django.contrib.contenttypes.models import ContentType
                from content.models import Article
                
                perm_obj = Permission.objects.get(
                    codename=permission,
                    content_type=ContentType.objects.get_for_model(Article)
                )
                self.stdout.write(f'  ✓ {perm_obj.name}')
            except Permission.DoesNotExist:
                self.stdout.write(f'  ? {permission}')
    
    def list_users(self):
        """List all users and their editorial roles."""
        self.stdout.write('Current Editorial Users:')
        self.stdout.write('='*60)
        
        # Get all users with editorial roles
        editorial_groups = Group.objects.filter(name__startswith='content_')
        users_with_roles = User.objects.filter(
            groups__in=editorial_groups,
            is_active=True
        ).distinct().order_by('last_name', 'first_name')
        
        if not users_with_roles.exists():
            self.stdout.write('No users with editorial roles found.')
            return
        
        service = RoleManagementService()
        
        for user in users_with_roles:
            role = service.get_user_role(user)
            
            # Get profile info
            profile_info = ''
            try:
                profile = user.profile
                profile_info = f' | Articles: {profile.articles_authored}'
            except UserProfile.DoesNotExist:
                profile_info = ' | No profile'
            
            self.stdout.write(
                f'{user.get_full_name():<25} | {user.username:<15} | '
                f'{role.title() if role else "None":<10}{profile_info}'
            )
        
        self.stdout.write('='*60)
        self.stdout.write(f'Total users with editorial roles: {users_with_roles.count()}')
        
        # Show role statistics
        self.stdout.write('\nRole Distribution:')
        stats = service.get_role_statistics()
        for role, count in stats.items():
            self.stdout.write(f'  {role.title()}: {count} users')
    
    def handle_user_not_found(self, username):
        """Handle case when user is not found."""
        self.stdout.write(
            self.style.WARNING(f'User not found: {username}')
        )
        
        # Suggest similar usernames
        similar_users = User.objects.filter(
            username__icontains=username
        )[:5]
        
        if similar_users.exists():
            self.stdout.write('Did you mean one of these users?')
            for user in similar_users:
                self.stdout.write(f'  - {user.username} ({user.get_full_name()})')
        
        # Show command to create user
        self.stdout.write('\nTo create a new user, use:')
        self.stdout.write('python manage.py createsuperuser')
        self.stdout.write('or')
        self.stdout.write('python manage.py create_editorial_user')