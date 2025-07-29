"""
User Management Models for MMA Backend

This module defines the user profile model with editorial roles and permissions
for the content management system workflow.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.core.validators import EmailValidator


class User(AbstractUser):
    """
    Extended User model with additional fields for editorial workflow.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    
    # Profile fields
    bio = models.TextField(blank=True, help_text="Brief biography")
    avatar = models.URLField(blank=True, help_text="Profile picture URL")
    website = models.URLField(blank=True, help_text="Personal website")
    
    # Editorial settings
    email_notifications = models.BooleanField(
        default=True, 
        help_text="Receive email notifications for workflow changes"
    )
    
    # Timestamps
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use email as username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['last_name', 'first_name']
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_short_name(self):
        """Return first name or username"""
        return self.first_name or self.username
    
    def get_editorial_role(self):
        """Get the highest editorial role for this user"""
        role_hierarchy = ['admin', 'publisher', 'editor', 'author']
        
        user_groups = self.groups.values_list('name', flat=True)
        
        for role in role_hierarchy:
            if f'content_{role}' in user_groups:
                return role
        
        return None
    
    def has_editorial_permission(self, permission_codename):
        """Check if user has specific editorial permission"""
        return self.has_perm(f'content.{permission_codename}')
    
    def can_edit_article(self, article):
        """Check if user can edit a specific article"""
        # Admin and Publisher can edit any article
        if self.has_editorial_permission('can_edit_any_article'):
            return True
        
        # Editor can edit articles in review or published status
        if (self.has_editorial_permission('can_edit_articles') and 
            article.status in ['review', 'published']):
            return True
        
        # Author can edit their own draft articles
        if (self.has_editorial_permission('can_edit_own_articles') and 
            article.author == self and article.status == 'draft'):
            return True
        
        return False
    
    def can_publish_article(self, article):
        """Check if user can publish a specific article"""
        return self.has_editorial_permission('can_publish_article')
    
    def can_archive_article(self, article):
        """Check if user can archive a specific article"""
        return self.has_editorial_permission('can_archive_article')


class UserProfile(models.Model):
    """
    Extended user profile with editorial workflow specific fields.
    """
    
    EDITORIAL_ROLES = [
        ('author', 'Author'),
        ('editor', 'Editor'),
        ('publisher', 'Publisher'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Editorial role (primary role for this user)
    editorial_role = models.CharField(
        max_length=20, 
        choices=EDITORIAL_ROLES, 
        default='author',
        help_text="Primary editorial role for this user"
    )
    
    # Editorial preferences
    default_category = models.ForeignKey(
        'content.Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Default category for new articles"
    )
    
    # Activity tracking
    articles_authored = models.PositiveIntegerField(default=0)
    articles_edited = models.PositiveIntegerField(default=0)
    articles_published = models.PositiveIntegerField(default=0)
    last_article_date = models.DateTimeField(null=True, blank=True)
    
    # Notification preferences
    notify_on_article_assignment = models.BooleanField(default=True)
    notify_on_status_change = models.BooleanField(default=True)
    notify_on_comment = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_editorial_role_display()})"
    
    def update_activity_stats(self):
        """Update user activity statistics"""
        from content.models import Article
        
        # Count articles by this user
        authored = Article.objects.filter(author=self.user).count()
        edited = Article.objects.filter(editor=self.user).count()
        published = Article.objects.filter(
            author=self.user, 
            status='published'
        ).count()
        
        # Get last article date
        last_article = Article.objects.filter(
            author=self.user
        ).order_by('-created_at').first()
        
        self.articles_authored = authored
        self.articles_edited = edited
        self.articles_published = published
        self.last_article_date = last_article.created_at if last_article else None
        self.save()
    
    def get_permission_summary(self):
        """Get summary of user's editorial permissions"""
        permissions = []
        user = self.user
        
        if user.has_editorial_permission('can_create_article'):
            permissions.append('Create Articles')
        if user.has_editorial_permission('can_edit_own_articles'):
            permissions.append('Edit Own Articles')
        if user.has_editorial_permission('can_edit_any_article'):
            permissions.append('Edit Any Article')
        if user.has_editorial_permission('can_publish_article'):
            permissions.append('Publish Articles')
        if user.has_editorial_permission('can_archive_article'):
            permissions.append('Archive Articles')
        if user.has_editorial_permission('can_manage_categories'):
            permissions.append('Manage Categories')
        if user.has_editorial_permission('can_manage_tags'):
            permissions.append('Manage Tags')
        
        return permissions


class EditorialWorkflowLog(models.Model):
    """
    Track editorial workflow status changes and actions.
    """
    
    ACTION_TYPES = [
        ('create', 'Article Created'),
        ('edit', 'Article Edited'),
        ('submit', 'Submitted for Review'),
        ('approve', 'Approved for Publishing'),
        ('publish', 'Published'),
        ('unpublish', 'Unpublished'),
        ('archive', 'Archived'),
        ('reject', 'Rejected'),
        ('assign_editor', 'Editor Assigned'),
        ('request_changes', 'Changes Requested'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Article and user involved
    article = models.ForeignKey(
        'content.Article', 
        on_delete=models.CASCADE, 
        related_name='workflow_logs'
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Action details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    
    # Additional context
    notes = models.TextField(blank=True, help_text="Optional notes about this action")
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'editorial_workflow_logs'
        verbose_name = 'Workflow Log'
        verbose_name_plural = 'Workflow Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['article', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        user_name = self.user.get_full_name() if self.user else 'System'
        return f"{user_name} {self.get_action_display()} - {self.article.title}"
    
    @classmethod
    def log_action(cls, article, user, action, from_status=None, to_status=None, notes='', **metadata):
        """Convenience method to log workflow actions"""
        return cls.objects.create(
            article=article,
            user=user,
            action=action,
            from_status=from_status or '',
            to_status=to_status or '',
            notes=notes,
            metadata=metadata
        )


class AssignmentNotification(models.Model):
    """
    Track editorial assignments and notifications.
    """
    
    NOTIFICATION_TYPES = [
        ('assignment', 'Editor Assignment'),
        ('status_change', 'Status Change'),
        ('comment', 'New Comment'),
        ('deadline', 'Deadline Reminder'),
        ('approval', 'Approval Required'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('dismissed', 'Dismissed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipients and article
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    article = models.ForeignKey('content.Article', on_delete=models.CASCADE, related_name='notifications')
    
    # Notification details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Email details
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'editorial_notifications'
        verbose_name = 'Editorial Notification'
        verbose_name_plural = 'Editorial Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status', '-created_at']),
            models.Index(fields=['article', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if self.status == 'pending' or self.status == 'sent':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()
    
    def send_email(self):
        """Send email notification"""
        if not self.email_sent and self.recipient.email_notifications:
            from .services import NotificationService
            
            service = NotificationService()
            success = service.send_notification_email(self)
            
            if success:
                self.email_sent = True
                self.email_sent_at = timezone.now()
                self.status = 'sent'
                self.save()
            
            return success
        return False