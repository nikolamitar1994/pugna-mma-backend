"""
Custom permissions for content management editorial workflow.

This module defines custom permissions and permission classes for the
content management system's editorial workflow.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from .models import Article


class ContentPermissions:
    """
    Define custom content management permissions.
    """
    
    CUSTOM_PERMISSIONS = [
        # Article permissions
        ('can_create_article', 'Can create articles'),
        ('can_edit_own_articles', 'Can edit own articles'),
        ('can_edit_any_article', 'Can edit any article'),
        ('can_publish_article', 'Can publish articles'),
        ('can_unpublish_article', 'Can unpublish articles'),
        ('can_archive_article', 'Can archive articles'),
        ('can_feature_article', 'Can feature articles'),
        ('can_set_breaking_news', 'Can set articles as breaking news'),
        ('can_assign_editor', 'Can assign editors to articles'),
        ('can_view_unpublished', 'Can view unpublished articles'),
        ('can_view_analytics', 'Can view article analytics'),
        
        # Category and Tag permissions
        ('can_manage_categories', 'Can manage categories'),
        ('can_manage_tags', 'Can manage tags'),
        
        # Workflow permissions
        ('can_approve_articles', 'Can approve articles for publishing'),
        ('can_reject_articles', 'Can reject articles'),
        ('can_request_changes', 'Can request changes to articles'),
        ('can_override_workflow', 'Can override workflow restrictions'),
        
        # Administrative permissions
        ('can_manage_editorial_roles', 'Can manage editorial roles'),
        ('can_view_workflow_logs', 'Can view workflow logs'),
        ('can_bulk_publish', 'Can bulk publish articles'),
        ('can_bulk_archive', 'Can bulk archive articles'),
    ]
    
    @classmethod
    def create_permissions(cls):
        """Create custom permissions for the Article model."""
        content_type = ContentType.objects.get_for_model(Article)
        
        created_permissions = []
        for codename, name in cls.CUSTOM_PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            if created:
                created_permissions.append(permission)
        
        return created_permissions


# Role-based permission definitions
ROLE_PERMISSIONS = {
    'content_author': [
        'can_create_article',
        'can_edit_own_articles',
        'can_view_unpublished',  # Only own articles
    ],
    
    'content_editor': [
        'can_create_article',
        'can_edit_own_articles',
        'can_edit_any_article',
        'can_view_unpublished',
        'can_approve_articles',
        'can_reject_articles',
        'can_request_changes',
        'can_assign_editor',
        'can_view_analytics',
        'can_manage_tags',
    ],
    
    'content_publisher': [
        'can_create_article',
        'can_edit_own_articles',
        'can_edit_any_article',
        'can_publish_article',
        'can_unpublish_article',
        'can_archive_article',
        'can_feature_article',
        'can_set_breaking_news',
        'can_view_unpublished',
        'can_approve_articles',
        'can_reject_articles',
        'can_request_changes',
        'can_assign_editor',
        'can_view_analytics',
        'can_manage_categories',
        'can_manage_tags',
        'can_bulk_publish',
        'can_view_workflow_logs',
    ],
    
    'content_admin': [
        # All permissions
        'can_create_article',
        'can_edit_own_articles',
        'can_edit_any_article',
        'can_publish_article',
        'can_unpublish_article',
        'can_archive_article',
        'can_feature_article',
        'can_set_breaking_news',
        'can_assign_editor',
        'can_view_unpublished',
        'can_approve_articles',
        'can_reject_articles',
        'can_request_changes',
        'can_override_workflow',
        'can_view_analytics',
        'can_manage_categories',
        'can_manage_tags',
        'can_manage_editorial_roles',
        'can_view_workflow_logs',
        'can_bulk_publish',
        'can_bulk_archive',
    ],
}


# DRF Permission Classes

class IsAuthorOrReadOnly(BasePermission):
    """
    Permission class that allows authors to edit their own articles,
    but only read access for others.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the author
        return obj.author == request.user


class CanEditArticle(BasePermission):
    """
    Permission class that checks if user can edit a specific article
    based on their role and the article's status.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # For read operations, check if user can view unpublished content
            if obj.status != 'published':
                return (request.user.has_perm('content.can_view_unpublished') or 
                       obj.author == request.user)
            return True
        
        # For write operations, use the user's can_edit_article method
        return request.user.can_edit_article(obj)


class CanPublishArticle(BasePermission):
    """
    Permission class for publishing articles.
    """
    
    def has_permission(self, request, view):
        return request.user.has_perm('content.can_publish_article')
    
    def has_object_permission(self, request, view, obj):
        return request.user.can_publish_article(obj)


class CanArchiveArticle(BasePermission):
    """
    Permission class for archiving articles.
    """
    
    def has_permission(self, request, view):
        return request.user.has_perm('content.can_archive_article')
    
    def has_object_permission(self, request, view, obj):
        return request.user.can_archive_article(obj)


class CanManageCategories(BasePermission):
    """
    Permission class for managing categories.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.has_perm('content.can_manage_categories')


class CanManageTags(BasePermission):
    """
    Permission class for managing tags.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.has_perm('content.can_manage_tags')


class CanViewWorkflowLogs(BasePermission):
    """
    Permission class for viewing workflow logs.
    """
    
    def has_permission(self, request, view):
        return request.user.has_perm('content.can_view_workflow_logs')


class CanAssignEditor(BasePermission):
    """
    Permission class for assigning editors to articles.
    """
    
    def has_permission(self, request, view):
        return request.user.has_perm('content.can_assign_editor')


class EditorialWorkflowPermission(BasePermission):
    """
    Comprehensive permission class for editorial workflow.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check action-specific permissions
        action = getattr(view, 'action', None)
        
        if action == 'create':
            return request.user.has_perm('content.can_create_article')
        elif action in ['publish', 'bulk_publish']:
            return request.user.has_perm('content.can_publish_article')
        elif action in ['archive', 'bulk_archive']:
            return request.user.has_perm('content.can_archive_article')
        elif action == 'assign_editor':
            return request.user.has_perm('content.can_assign_editor')
        elif action in ['approve', 'reject']:
            return request.user.has_perm('content.can_approve_articles')
        elif action == 'feature':
            return request.user.has_perm('content.can_feature_article')
        elif action == 'set_breaking':
            return request.user.has_perm('content.can_set_breaking_news')
        elif action == 'workflow_logs':
            return request.user.has_perm('content.can_view_workflow_logs')
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Read permissions
            if obj.status != 'published':
                return (request.user.has_perm('content.can_view_unpublished') or 
                       obj.author == request.user)
            return True
        
        # Write permissions based on action
        action = getattr(view, 'action', None)
        
        if action in ['update', 'partial_update']:
            return request.user.can_edit_article(obj)
        elif action == 'publish':
            return request.user.can_publish_article(obj)
        elif action == 'archive':
            return request.user.can_archive_article(obj)
        elif action == 'destroy':
            # Only admin or author can delete
            return (request.user.has_perm('content.can_edit_any_article') or 
                   (obj.author == request.user and obj.status == 'draft'))
        
        return False


# Utility functions for permission checking

def user_can_access_article(user, article):
    """Check if user can access (view) an article."""
    if article.status == 'published':
        return True
    
    if not user.is_authenticated:
        return False
    
    # Author can always see their own articles
    if article.author == user:
        return True
    
    # Users with unpublished permission can see all
    return user.has_perm('content.can_view_unpublished')


def user_can_edit_article(user, article):
    """Check if user can edit an article."""
    if not user.is_authenticated:
        return False
    
    return user.can_edit_article(article)


def get_articles_for_user(user, queryset=None):
    """
    Filter articles queryset based on user permissions.
    """
    if queryset is None:
        queryset = Article.objects.all()
    
    if not user.is_authenticated:
        return queryset.filter(status='published')
    
    # Staff can see everything
    if user.is_staff or user.has_perm('content.can_view_unpublished'):
        return queryset
    
    # Regular users see published articles and their own
    from django.db.models import Q
    return queryset.filter(
        Q(status='published') | Q(author=user)
    )


def get_user_editorial_permissions(user):
    """Get a summary of user's editorial permissions."""
    if not user.is_authenticated:
        return []
    
    permissions = []
    for codename, name in ContentPermissions.CUSTOM_PERMISSIONS:
        if user.has_perm(f'content.{codename}'):
            permissions.append({
                'codename': codename,
                'name': name,
                'has_permission': True
            })
    
    return permissions