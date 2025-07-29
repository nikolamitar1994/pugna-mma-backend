"""
Editorial workflow serializers with role-based field permissions.

This module provides serializers that show different fields based on
user roles and permissions in the editorial workflow.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Article, Category, Tag
from users.models import UserProfile, EditorialWorkflowLog, AssignmentNotification

User = get_user_model()


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed based on user permissions.
    """
    
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        user = kwargs.pop('user', None)
        
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)
        
        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)
        
        # Apply role-based field filtering
        if user and hasattr(self, 'get_fields_for_user'):
            allowed_fields = self.get_fields_for_user(user)
            existing = set(self.fields)
            for field_name in existing - allowed_fields:
                self.fields.pop(field_name)


class EditorialUserSerializer(serializers.ModelSerializer):
    """Serializer for users in editorial context."""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    editorial_role = serializers.CharField(source='get_editorial_role', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'editorial_role', 'is_active'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profiles with editorial information."""
    
    user = EditorialUserSerializer(read_only=True)
    permission_summary = serializers.ListField(
        source='get_permission_summary', 
        read_only=True
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'editorial_role', 'default_category',
            'articles_authored', 'articles_edited', 'articles_published',
            'last_article_date', 'permission_summary',
            'notify_on_article_assignment', 'notify_on_status_change',
            'notify_on_comment', 'created_at', 'updated_at'
        ]


class EditorialArticleListSerializer(DynamicFieldsModelSerializer):
    """
    Article list serializer with role-based field visibility.
    """
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    editor_name = serializers.CharField(source='editor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_article_type_display', read_only=True)
    
    # Editorial workflow fields
    can_edit = serializers.SerializerMethodField()
    can_publish = serializers.SerializerMethodField()
    can_archive = serializers.SerializerMethodField()
    workflow_actions = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'category_name', 'author_name',
            'editor_name', 'article_type', 'type_display', 'status', 'status_display',
            'is_featured', 'is_breaking', 'view_count', 'reading_time',
            'published_at', 'created_at', 'updated_at',
            'can_edit', 'can_publish', 'can_archive', 'workflow_actions'
        ]
    
    def get_fields_for_user(self, user):
        """Return fields based on user permissions."""
        base_fields = {
            'id', 'title', 'slug', 'excerpt', 'category_name', 'author_name',
            'article_type', 'type_display', 'status', 'status_display',
            'is_featured', 'view_count', 'reading_time', 'published_at', 'created_at'
        }
        
        # Add editorial fields for authenticated users
        if user.is_authenticated:
            base_fields.update({
                'can_edit', 'editor_name', 'updated_at'
            })
        
        # Add advanced fields for editors and above
        if user.has_perm('content.can_view_unpublished'):
            base_fields.update({
                'can_publish', 'can_archive', 'workflow_actions', 'is_breaking'
            })
        
        return base_fields
    
    def get_can_edit(self, obj):
        """Check if current user can edit this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_edit_article(obj)
        return False
    
    def get_can_publish(self, obj):
        """Check if current user can publish this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_publish_article(obj)
        return False
    
    def get_can_archive(self, obj):
        """Check if current user can archive this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_archive_article(obj)
        return False
    
    def get_workflow_actions(self, obj):
        """Get available workflow actions for current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        actions = []
        user = request.user
        
        if obj.status == 'draft' and user.can_edit_article(obj):
            actions.append('submit_for_review')
        
        if obj.status == 'review':
            if user.has_perm('content.can_approve_articles'):
                actions.extend(['approve', 'reject'])
        
        if obj.status == 'published':
            if user.has_perm('content.can_unpublish_article'):
                actions.append('unpublish')
            if user.can_archive_article(obj):
                actions.append('archive')
        
        if user.has_perm('content.can_assign_editor'):
            actions.append('assign_editor')
        
        return actions


class EditorialArticleDetailSerializer(DynamicFieldsModelSerializer):
    """
    Article detail serializer with comprehensive editorial information.
    """
    
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    author = EditorialUserSerializer(read_only=True)
    editor = EditorialUserSerializer(read_only=True)
    
    # Editorial workflow information
    workflow_logs = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_publish = serializers.SerializerMethodField()
    can_archive = serializers.SerializerMethodField()
    workflow_actions = serializers.SerializerMethodField()
    
    # SEO fields (only for editors and above)
    seo_title = serializers.CharField(source='get_seo_title', read_only=True)
    seo_description = serializers.CharField(source='get_seo_description', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'category', 'tags',
            'article_type', 'status', 'author', 'editor',
            'featured_image', 'featured_image_alt', 'featured_image_caption',
            'meta_title', 'meta_description', 'seo_title', 'seo_description',
            'is_featured', 'is_breaking', 'allow_comments',
            'view_count', 'reading_time', 'published_at', 'created_at', 'updated_at',
            'workflow_logs', 'can_edit', 'can_publish', 'can_archive', 'workflow_actions'
        ]
    
    def get_fields_for_user(self, user):
        """Return fields based on user permissions."""
        # Public fields
        base_fields = {
            'id', 'title', 'slug', 'excerpt', 'content', 'category', 'tags',
            'article_type', 'status', 'author', 'featured_image', 
            'featured_image_alt', 'featured_image_caption', 'is_featured',
            'allow_comments', 'view_count', 'reading_time', 'published_at', 'created_at'
        }
        
        # Author and editor fields
        if user.is_authenticated:
            base_fields.update({
                'editor', 'updated_at', 'can_edit', 'workflow_actions'
            })
        
        # Editorial fields
        if user.has_perm('content.can_view_unpublished'):
            base_fields.update({
                'is_breaking', 'can_publish', 'can_archive'
            })
        
        # Advanced editorial fields
        if user.has_perm('content.can_view_workflow_logs'):
            base_fields.add('workflow_logs')
        
        # SEO fields for editors
        if user.has_perm('content.can_edit_any_article'):
            base_fields.update({
                'meta_title', 'meta_description', 'seo_title', 'seo_description'
            })
        
        return base_fields
    
    def get_category(self, obj):
        """Get category with minimal info."""
        if obj.category:
            return {
                'id': str(obj.category.id),
                'name': obj.category.name,
                'slug': obj.category.slug
            }
        return None
    
    def get_tags(self, obj):
        """Get tags with minimal info."""
        return [
            {
                'id': str(tag.id),
                'name': tag.name,
                'slug': tag.slug,
                'color': tag.color
            }
            for tag in obj.tags.all()
        ]
    
    def get_workflow_logs(self, obj):
        """Get workflow logs if user has permission."""
        request = self.context.get('request')
        if not request or not request.user.has_perm('content.can_view_workflow_logs'):
            return []
        
        logs = obj.workflow_logs.select_related('user').order_by('-created_at')[:10]
        return [
            {
                'id': str(log.id),
                'action': log.get_action_display(),
                'user': log.user.get_full_name() if log.user else 'System',
                'from_status': log.from_status,
                'to_status': log.to_status,
                'notes': log.notes,
                'created_at': log.created_at
            }
            for log in logs
        ]
    
    def get_can_edit(self, obj):
        """Check if current user can edit this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_edit_article(obj)
        return False
    
    def get_can_publish(self, obj):
        """Check if current user can publish this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_publish_article(obj)
        return False
    
    def get_can_archive(self, obj):
        """Check if current user can archive this article."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.can_archive_article(obj)
        return False
    
    def get_workflow_actions(self, obj):
        """Get available workflow actions for current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []
        
        actions = []
        user = request.user
        
        if obj.status == 'draft' and user.can_edit_article(obj):
            actions.append({
                'action': 'submit_for_review',
                'label': 'Submit for Review',
                'method': 'POST'
            })
        
        if obj.status == 'review':
            if user.has_perm('content.can_approve_articles'):
                actions.extend([
                    {
                        'action': 'approve',
                        'label': 'Approve & Publish',
                        'method': 'POST'
                    },
                    {
                        'action': 'reject',
                        'label': 'Reject',
                        'method': 'POST'
                    }
                ])
        
        if obj.status == 'published':
            if user.has_perm('content.can_unpublish_article'):
                actions.append({
                    'action': 'unpublish',
                    'label': 'Unpublish',
                    'method': 'POST'
                })
            if user.can_archive_article(obj):
                actions.append({
                    'action': 'archive',
                    'label': 'Archive',
                    'method': 'POST'
                })
        
        if user.has_perm('content.can_assign_editor'):
            actions.append({
                'action': 'assign_editor',
                'label': 'Assign Editor',
                'method': 'POST',
                'requires_editor_id': True
            })
        
        return actions


class EditorialArticleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating articles with role-based validation.
    """
    
    class Meta:
        model = Article
        fields = [
            'title', 'slug', 'excerpt', 'content', 'category', 'tags',
            'article_type', 'status', 'featured_image', 'featured_image_alt',
            'featured_image_caption', 'meta_title', 'meta_description',
            'is_featured', 'is_breaking', 'allow_comments', 'published_at'
        ]
        extra_kwargs = {
            'slug': {'required': False},
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove fields based on user permissions
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            
            # Only publishers can set featured and breaking
            if not user.has_perm('content.can_feature_article'):
                self.fields.pop('is_featured', None)
            
            if not user.has_perm('content.can_set_breaking_news'):
                self.fields.pop('is_breaking', None)
            
            # Only editors and above can edit SEO fields
            if not user.has_perm('content.can_edit_any_article'):
                self.fields.pop('meta_title', None)
                self.fields.pop('meta_description', None)
            
            # Authors can only set status to draft or review
            if not user.has_perm('content.can_publish_article'):
                if 'status' in self.fields:
                    self.fields['status'].choices = [
                        ('draft', 'Draft'),
                        ('review', 'Under Review')
                    ]
    
    def validate_status(self, value):
        """Validate status changes based on user permissions."""
        request = self.context.get('request')
        user = request.user if request else None
        
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        
        # Check if user can set this status
        if value == 'published' and not user.has_perm('content.can_publish_article'):
            raise serializers.ValidationError("You don't have permission to publish articles.")
        
        if value == 'archived' and not user.has_perm('content.can_archive_article'):
            raise serializers.ValidationError("You don't have permission to archive articles.")
        
        return value
    
    def create(self, validated_data):
        """Create article with current user as author."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        return super().create(validated_data)


class WorkflowLogSerializer(serializers.ModelSerializer):
    """Serializer for editorial workflow logs."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    article_title = serializers.CharField(source='article.title', read_only=True)
    
    class Meta:
        model = EditorialWorkflowLog
        fields = [
            'id', 'article', 'article_title', 'user', 'user_name',
            'action', 'action_display', 'from_status', 'to_status',
            'notes', 'metadata', 'created_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for editorial notifications."""
    
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    article_title = serializers.CharField(source='article.title', read_only=True)
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AssignmentNotification
        fields = [
            'id', 'recipient', 'recipient_name', 'article', 'article_title',
            'notification_type', 'type_display', 'title', 'message',
            'status', 'status_display', 'email_sent', 'email_sent_at',
            'created_at', 'read_at'
        ]
        read_only_fields = ['email_sent', 'email_sent_at', 'created_at', 'read_at']