"""
Management command to create a new user with editorial role.

This command creates a new user and assigns them an editorial role.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
import getpass

from users.models import UserProfile
from content.services import RoleManagementService

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a new user with editorial role'
    
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the new user')
        parser.add_argument('--email', type=str, help='Email address for the new user')
        parser.add_argument('--first-name', type=str, help='First name')
        parser.add_argument('--last-name', type=str, help='Last name')
        parser.add_argument(
            '--role', 
            type=str, 
            choices=['author', 'editor', 'publisher', 'admin'],
            help='Editorial role to assign'
        )
        parser.add_argument('--password', type=str, help='Password (will prompt if not provided)')
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Don\'t prompt for input, use provided arguments',
        )
    
    def handle(self, *args, **options):
        # Get user input
        user_data = self.get_user_data(options)
        
        try:
            with transaction.atomic():
                user = self.create_user(user_data)
                
                if user_data['role']:
                    self.assign_role(user, user_data['role'])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created user: {user.username} ({user.email})'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error creating user: {e}')
    
    def get_user_data(self, options):
        """Get user data from options or prompts."""
        user_data = {}
        
        # Username
        user_data['username'] = options['username']
        if not user_data['username'] and not options['no_input']:
            user_data['username'] = input('Username: ')
        
        if not user_data['username']:
            raise CommandError('Username is required')
        
        # Email
        user_data['email'] = options['email']
        if not user_data['email'] and not options['no_input']:
            user_data['email'] = input('Email address: ')
        
        if not user_data['email']:
            raise CommandError('Email is required')
        
        # First name
        user_data['first_name'] = options['first_name']
        if not user_data['first_name'] and not options['no_input']:
            user_data['first_name'] = input('First name: ')
        
        # Last name
        user_data['last_name'] = options['last_name']
        if not user_data['last_name'] and not options['no_input']:
            user_data['last_name'] = input('Last name: ')
        
        # Role
        user_data['role'] = options['role']
        if not user_data['role'] and not options['no_input']:
            self.stdout.write('Available roles:')
            roles = ['author', 'editor', 'publisher', 'admin']
            for i, role in enumerate(roles, 1):
                self.stdout.write(f'  {i}. {role.title()}')
            
            role_choice = input('Enter role number or name: ').strip().lower()
            
            if role_choice.isdigit():
                role_idx = int(role_choice) - 1
                if 0 <= role_idx < len(roles):
                    user_data['role'] = roles[role_idx]
            elif role_choice in roles:
                user_data['role'] = role_choice
        
        # Password
        user_data['password'] = options['password']
        if not user_data['password'] and not options['no_input']:
            user_data['password'] = getpass.getpass('Password: ')
            password_confirm = getpass.getpass('Password (again): ')
            
            if user_data['password'] != password_confirm:
                raise CommandError('Passwords do not match')
        
        if not user_data['password']:
            raise CommandError('Password is required')
        
        return user_data
    
    def create_user(self, user_data):
        """Create the user."""
        # Check if username already exists
        if User.objects.filter(username=user_data['username']).exists():
            raise CommandError(f'Username "{user_data["username"]}" already exists')
        
        # Check if email already exists
        if User.objects.filter(email=user_data['email']).exists():
            raise CommandError(f'Email "{user_data["email"]}" already exists')
        
        # Create user
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'] or '',
            last_name=user_data['last_name'] or ''
        )
        
        self.stdout.write(f'Created user: {user.username}')
        
        return user
    
    def assign_role(self, user, role):
        """Assign editorial role to user."""
        service = RoleManagementService()
        success = service.assign_user_role(user, role)
        
        if not success:
            raise CommandError(f'Failed to assign role: {role}')
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'editorial_role': role}
        )
        
        self.stdout.write(f'Assigned role: {role.title()}')
        
        # Show permissions
        permissions = service.get_role_permissions(role)
        self.stdout.write(f'Permissions: {len(permissions)} assigned')
        
        if self.verbosity >= 2:
            self.stdout.write('Assigned permissions:')
            for permission in permissions:
                self.stdout.write(f'  - {permission}')
    
    def validate_email(self, email):
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None