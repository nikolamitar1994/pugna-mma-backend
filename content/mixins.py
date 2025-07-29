"""
ViewSet mixins for editorial workflow permissions and functionality.

This module provides reusable mixins for implementing editorial workflow
features in Django REST Framework ViewSets.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from typing import Dict, Any

from .permissions import (
    EditorialWorkflowPermission, CanPublishArticle, CanArchiveArticle,
    CanAssignEditor, CanViewWorkflowLogs, get_articles_for_user
)
from .services import EditorialWorkflowService, ContentAnalyticsService
from users.models import EditorialWorkflowLog, User


class EditorialWorkflowMixin:
    """
    Mixin that adds editorial workflow actions to ViewSets.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_service = EditorialWorkflowService()
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()
        return get_articles_for_user(self.request.user, queryset)
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, EditorialWorkflowPermission]
    )
    def submit_for_review(self, request, pk=None):
        """Submit article for editorial review."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        if article.status != 'draft':
            return Response(
                {'error': 'Only draft articles can be submitted for review.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = self.workflow_service.submit_for_review(article, request.user, notes)
        
        if success:
            return Response({
                'message': 'Article submitted for review successfully.',
                'status': article.status
            })
        else:
            return Response(
                {'error': 'Failed to submit article for review.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, CanPublishArticle]
    )
    def publish(self, request, pk=None):
        """Publish an article."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        success = self.workflow_service.approve_article(article, request.user, notes)
        
        if success:
            return Response({
                'message': 'Article published successfully.',
                'status': article.status,
                'published_at': article.published_at
            })
        else:
            return Response(
                {'error': 'Failed to publish article.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, EditorialWorkflowPermission]
    )
    def unpublish(self, request, pk=None):
        """Unpublish an article (move to draft)."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        if article.status != 'published':
            return Response(
                {'error': 'Only published articles can be unpublished.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = self.workflow_service.transition_article_status(
            article, 'draft', request.user, notes
        )
        
        if success:
            return Response({
                'message': 'Article unpublished successfully.',
                'status': article.status
            })
        else:
            return Response(
                {'error': 'Failed to unpublish article.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, CanArchiveArticle]
    )
    def archive(self, request, pk=None):
        """Archive an article."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        success = self.workflow_service.archive_article(article, request.user, notes)
        
        if success:
            return Response({
                'message': 'Article archived successfully.',
                'status': article.status
            })
        else:
            return Response(
                {'error': 'Failed to archive article.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, EditorialWorkflowPermission]
    )
    def approve(self, request, pk=None):
        """Approve article for publishing."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        if article.status != 'review':
            return Response(
                {'error': 'Only articles under review can be approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = self.workflow_service.approve_article(article, request.user, notes)
        
        if success:
            return Response({
                'message': 'Article approved and published successfully.',
                'status': article.status,
                'published_at': article.published_at
            })
        else:
            return Response(
                {'error': 'Failed to approve article.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, EditorialWorkflowPermission]
    )
    def reject(self, request, pk=None):
        """Reject article and return to draft."""
        article = self.get_object()
        notes = request.data.get('notes', '')
        
        if article.status != 'review':
            return Response(
                {'error': 'Only articles under review can be rejected.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = self.workflow_service.reject_article(article, request.user, notes)
        
        if success:
            return Response({
                'message': 'Article rejected and returned to draft.',
                'status': article.status
            })
        else:
            return Response(
                {'error': 'Failed to reject article.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, CanAssignEditor]
    )
    def assign_editor(self, request, pk=None):
        """Assign an editor to an article."""
        article = self.get_object()
        editor_id = request.data.get('editor_id')
        notes = request.data.get('notes', '')
        
        if not editor_id:
            return Response(
                {'error': 'editor_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            editor = User.objects.get(id=editor_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'Editor not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has editor role
        if not editor.groups.filter(name__in=['content_editor', 'content_publisher', 'content_admin']).exists():
            return Response(
                {'error': 'User must have editor role or higher.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = self.workflow_service.assign_editor(article, editor, request.user, notes)
        
        if success:
            return Response({
                'message': f'Editor {editor.get_full_name()} assigned successfully.',
                'editor': {
                    'id': str(editor.id),
                    'name': editor.get_full_name(),
                    'email': editor.email
                }
            })
        else:
            return Response(
                {'error': 'Failed to assign editor.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(
        detail=True, 
        methods=['get'], 
        permission_classes=[IsAuthenticated, CanViewWorkflowLogs]
    )
    def workflow_logs(self, request, pk=None):
        """Get workflow logs for an article."""
        article = self.get_object()
        logs = EditorialWorkflowLog.objects.filter(
            article=article
        ).select_related('user').order_by('-created_at')
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': str(log.id),
                'action': log.get_action_display(),
                'user': log.user.get_full_name() if log.user else 'System',
                'from_status': log.from_status,
                'to_status': log.to_status,
                'notes': log.notes,
                'created_at': log.created_at,
                'metadata': log.metadata
            })
        
        return Response({
            'article_id': str(article.id),
            'article_title': article.title,
            'logs': logs_data
        })


class BulkActionsMixin:
    """
    Mixin that adds bulk editorial actions to ViewSets.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_service = EditorialWorkflowService()
    
    @action(
        detail=False, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, CanPublishArticle]
    )
    def bulk_publish(self, request):
        """Bulk publish multiple articles."""
        article_ids = request.data.get('article_ids', [])
        notes = request.data.get('notes', '')
        
        if not article_ids:
            return Response(
                {'error': 'article_ids list is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {'successful': [], 'failed': []}
        
        for article_id in article_ids:
            try:
                article = self.get_queryset().get(id=article_id)
                success = self.workflow_service.approve_article(article, request.user, notes)
                
                if success:
                    results['successful'].append({
                        'id': str(article.id),
                        'title': article.title
                    })
                else:
                    results['failed'].append({
                        'id': str(article.id),
                        'title': article.title,
                        'error': 'Failed to publish'
                    })
                    
            except self.get_queryset().model.DoesNotExist:
                results['failed'].append({
                    'id': article_id,
                    'error': 'Article not found'
                })
        
        return Response({
            'message': f'Bulk publish completed. {len(results["successful"])} successful, {len(results["failed"])} failed.',
            'results': results
        })
    
    @action(
        detail=False, 
        methods=['post'], 
        permission_classes=[IsAuthenticated, CanArchiveArticle]
    )
    def bulk_archive(self, request):
        """Bulk archive multiple articles."""
        article_ids = request.data.get('article_ids', [])
        notes = request.data.get('notes', '')
        
        if not article_ids:
            return Response(
                {'error': 'article_ids list is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = {'successful': [], 'failed': []}
        
        for article_id in article_ids:
            try:
                article = self.get_queryset().get(id=article_id)
                success = self.workflow_service.archive_article(article, request.user, notes)
                
                if success:
                    results['successful'].append({
                        'id': str(article.id),
                        'title': article.title
                    })
                else:
                    results['failed'].append({
                        'id': str(article.id),
                        'title': article.title,
                        'error': 'Failed to archive'
                    })
                    
            except self.get_queryset().model.DoesNotExist:
                results['failed'].append({
                    'id': article_id,
                    'error': 'Article not found'
                })
        
        return Response({
            'message': f'Bulk archive completed. {len(results["successful"])} successful, {len(results["failed"])} failed.',
            'results': results
        })


class ContentAnalyticsMixin:
    """
    Mixin that adds content analytics actions to ViewSets.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analytics_service = ContentAnalyticsService()
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def my_analytics(self, request):
        """Get analytics for current user's content."""
        days = int(request.query_params.get('days', 30))
        stats = self.analytics_service.get_user_productivity_stats(request.user, days)
        
        return Response(stats)
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def content_performance(self, request):
        """Get overall content performance statistics."""
        # Only allow users with analytics permission
        if not request.user.has_perm('content.can_view_analytics'):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 30))
        stats = self.analytics_service.get_content_performance_stats(days)
        
        return Response(stats)
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def workflow_statistics(self, request):
        """Get editorial workflow statistics."""
        if not request.user.has_perm('content.can_view_workflow_logs'):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        workflow_service = EditorialWorkflowService()
        stats = workflow_service.get_workflow_statistics()
        
        return Response(stats)


class AuthorArticlesMixin:
    """
    Mixin that adds author-specific article filtering.
    """
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def my_articles(self, request):
        """Get current user's articles."""
        articles = self.get_queryset().filter(author=request.user)
        
        # Apply status filter if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            articles = articles.filter(status=status_filter)
        
        # Apply pagination
        page = self.paginate_queryset(articles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def my_drafts(self, request):
        """Get current user's draft articles."""
        drafts = self.get_queryset().filter(
            author=request.user,
            status='draft'
        )
        
        serializer = self.get_serializer(drafts, many=True)
        return Response(serializer.data)
    
    @action(
        detail=False, 
        methods=['get'], 
        permission_classes=[IsAuthenticated]
    )
    def assigned_to_me(self, request):
        """Get articles assigned to current user as editor."""
        assigned = self.get_queryset().filter(
            editor=request.user
        )
        
        # Apply status filter if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            assigned = assigned.filter(status=status_filter)
        
        # Apply pagination
        page = self.paginate_queryset(assigned)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(assigned, many=True)
        return Response(serializer.data)


class StatusFilterMixin:
    """
    Mixin that adds status-based filtering actions.
    """
    
    @action(detail=False, methods=['get'])
    def drafts(self, request):
        """Get all draft articles (permission filtered)."""
        drafts = self.get_queryset().filter(status='draft')
        
        page = self.paginate_queryset(drafts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(drafts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def under_review(self, request):
        """Get articles under review."""
        if not request.user.has_perm('content.can_view_unpublished'):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        review_articles = self.get_queryset().filter(status='review')
        
        page = self.paginate_queryset(review_articles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(review_articles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived articles."""
        if not request.user.has_perm('content.can_view_unpublished'):
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        archived_articles = self.get_queryset().filter(status='archived')
        
        page = self.paginate_queryset(archived_articles)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(archived_articles, many=True)
        return Response(serializer.data)