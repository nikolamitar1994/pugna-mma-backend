"""
Editorial Workflow Services for Content Management.

This module provides services for managing editorial workflow,
status transitions, notifications, and role management.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from typing import List, Optional, Dict, Any
import logging

from .models import Article
from .permissions import ContentPermissions, ROLE_PERMISSIONS
from users.models import User, UserProfile, EditorialWorkflowLog, AssignmentNotification

logger = logging.getLogger(__name__)


class EditorialWorkflowService:
    """
    Service for managing editorial workflow state transitions and business logic.
    """
    
    # Valid status transitions
    STATUS_TRANSITIONS = {
        'draft': ['review', 'published', 'archived'],
        'review': ['draft', 'published', 'archived'],
        'published': ['archived'],
        'archived': ['draft', 'review'],
    }
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def can_transition_status(self, article: Article, from_status: str, to_status: str, user: User) -> bool:
        """
        Check if a status transition is valid and user has permission.
        """
        # Check if transition is valid
        if to_status not in self.STATUS_TRANSITIONS.get(from_status, []):
            return False
        
        # Check user permissions for specific transitions
        if to_status == 'published':
            return user.can_publish_article(article)
        elif to_status == 'archived':
            return user.can_archive_article(article)
        elif to_status == 'review':
            return user.can_edit_article(article)
        elif to_status == 'draft':
            return user.can_edit_article(article)
        
        return False
    
    @transaction.atomic
    def transition_article_status(
        self, 
        article: Article, 
        new_status: str, 
        user: User, 
        notes: str = '',
        **metadata
    ) -> bool:
        """
        Transition article to new status with proper validation and logging.
        """
        old_status = article.status
        
        # Validate transition
        if not self.can_transition_status(article, old_status, new_status, user):
            logger.warning(
                f"Invalid status transition attempt: {old_status} -> {new_status} "
                f"by user {user.id} for article {article.id}"
            )
            return False
        
        # Update article status
        article.status = new_status
        
        # Handle status-specific logic
        if new_status == 'published':
            if not article.published_at:
                article.published_at = timezone.now()
        elif new_status == 'review':
            # Auto-assign editor if none assigned
            if not article.editor:
                article.editor = self._auto_assign_editor(article)
        
        article.save()
        
        # Log the transition
        EditorialWorkflowLog.log_action(
            article=article,
            user=user,
            action=self._get_action_for_transition(old_status, new_status),
            from_status=old_status,
            to_status=new_status,
            notes=notes,
            **metadata
        )
        
        # Send notifications
        self._send_status_change_notifications(article, old_status, new_status, user)
        
        # Update user activity stats
        if hasattr(user, 'profile'):
            user.profile.update_activity_stats()
        
        logger.info(
            f"Article {article.id} status changed from {old_status} to {new_status} "
            f"by user {user.id}"
        )
        
        return True
    
    def submit_for_review(self, article: Article, user: User, notes: str = '') -> bool:
        """Submit article for editorial review."""
        return self.transition_article_status(
            article, 'review', user, notes, action_type='submit'
        )
    
    def approve_article(self, article: Article, user: User, notes: str = '') -> bool:
        """Approve article for publishing."""
        return self.transition_article_status(
            article, 'published', user, notes, action_type='approve'
        )
    
    def reject_article(self, article: Article, user: User, notes: str = '') -> bool:
        """Reject article and send back to draft."""
        success = self.transition_article_status(
            article, 'draft', user, notes, action_type='reject'
        )
        
        if success:
            # Log specific rejection action
            EditorialWorkflowLog.log_action(
                article=article,
                user=user,
                action='reject',
                from_status='review',
                to_status='draft',
                notes=notes
            )
        
        return success
    
    def archive_article(self, article: Article, user: User, notes: str = '') -> bool:
        """Archive article."""
        return self.transition_article_status(
            article, 'archived', user, notes, action_type='archive'
        )
    
    def assign_editor(self, article: Article, editor: User, assigner: User, notes: str = '') -> bool:
        """Assign an editor to an article."""
        if not assigner.has_perm('content.can_assign_editor'):
            return False
        
        old_editor = article.editor
        article.editor = editor
        article.save()
        
        # Log the assignment
        EditorialWorkflowLog.log_action(
            article=article,
            user=assigner,
            action='assign_editor',
            notes=notes,
            old_editor_id=old_editor.id if old_editor else None,
            new_editor_id=editor.id
        )
        
        # Notify the new editor
        self.notification_service.send_assignment_notification(article, editor, assigner)
        
        return True
    
    def _get_action_for_transition(self, from_status: str, to_status: str) -> str:
        """Get appropriate action name for status transition."""
        transition_actions = {
            ('draft', 'review'): 'submit',
            ('review', 'published'): 'approve',
            ('review', 'draft'): 'reject',
            ('draft', 'published'): 'publish',
            ('published', 'archived'): 'archive',
            ('archived', 'draft'): 'reactivate',
        }
        
        return transition_actions.get((from_status, to_status), 'edit')
    
    def _auto_assign_editor(self, article: Article) -> Optional[User]:
        """Auto-assign an available editor to an article."""
        # Get editors with capacity (simplified logic)
        editors = User.objects.filter(
            groups__name='content_editor',
            is_active=True
        ).order_by('?')  # Random order for load balancing
        
        # Could implement more sophisticated logic here
        # like checking workload, category expertise, etc.
        
        return editors.first()
    
    def _send_status_change_notifications(
        self, 
        article: Article, 
        old_status: str, 
        new_status: str, 
        user: User
    ):
        """Send notifications for status changes."""
        # Notify author if someone else made the change
        if article.author != user and article.author.email_notifications:
            self.notification_service.send_status_change_notification(
                article, article.author, old_status, new_status, user
            )
        
        # Notify editor if assigned and different from user
        if (article.editor and 
            article.editor != user and 
            article.editor != article.author and 
            article.editor.email_notifications):
            self.notification_service.send_status_change_notification(
                article, article.editor, old_status, new_status, user
            )
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        from django.db.models import Count
        
        # Article status distribution
        status_stats = Article.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Recent activity
        recent_logs = EditorialWorkflowLog.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # User activity
        active_authors = User.objects.filter(
            articles__created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).distinct().count()
        
        return {
            'status_distribution': list(status_stats),
            'recent_activity': list(recent_logs),
            'active_authors_last_30_days': active_authors,
            'total_articles': Article.objects.count(),
            'published_articles': Article.objects.filter(status='published').count(),
            'articles_in_review': Article.objects.filter(status='review').count(),
        }


class NotificationService:
    """
    Service for handling editorial notifications and emails.
    """
    
    def send_assignment_notification(
        self, 
        article: Article, 
        editor: User, 
        assigner: User
    ) -> bool:
        """Send notification when editor is assigned to article."""
        notification = AssignmentNotification.objects.create(
            recipient=editor,
            article=article,
            notification_type='assignment',
            title=f'Article assigned: {article.title}',
            message=f'{assigner.get_full_name()} has assigned you to review "{article.title}".'
        )
        
        return notification.send_email()
    
    def send_status_change_notification(
        self, 
        article: Article, 
        recipient: User, 
        old_status: str, 
        new_status: str, 
        changed_by: User
    ) -> bool:
        """Send notification for article status changes."""
        status_messages = {
            'published': f'Your article "{article.title}" has been published by {changed_by.get_full_name()}.',
            'archived': f'Your article "{article.title}" has been archived by {changed_by.get_full_name()}.',
            'review': f'Your article "{article.title}" has been submitted for review.',
            'draft': f'Your article "{article.title}" has been returned to draft status by {changed_by.get_full_name()}.',
        }
        
        notification = AssignmentNotification.objects.create(
            recipient=recipient,
            article=article,
            notification_type='status_change',
            title=f'Status changed: {article.title}',
            message=status_messages.get(new_status, f'Article status changed from {old_status} to {new_status}.')
        )
        
        return notification.send_email()
    
    def send_notification_email(self, notification: AssignmentNotification) -> bool:
        """Send email for notification."""
        try:
            subject = f'[MMA CMS] {notification.title}'
            message = f"""
{notification.message}

Article: {notification.article.title}
Status: {notification.article.get_status_display()}
Author: {notification.article.author.get_full_name()}

View article: {settings.SITE_URL}/admin/content/article/{notification.article.id}/change/

---
MMA Content Management System
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                fail_silently=False,
            )
            
            logger.info(f"Notification email sent to {notification.recipient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            return False


class RoleManagementService:
    """
    Service for managing editorial roles and permissions.
    """
    
    def __init__(self):
        self.ensure_permissions_exist()
        self.ensure_groups_exist()
    
    def ensure_permissions_exist(self):
        """Ensure all custom permissions exist."""
        ContentPermissions.create_permissions()
    
    def ensure_groups_exist(self):
        """Ensure all editorial role groups exist with correct permissions."""
        for group_name, permission_codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                logger.info(f"Created editorial group: {group_name}")
            
            # Clear existing permissions and add current ones
            group.permissions.clear()
            
            for codename in permission_codenames:
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=ContentType.objects.get_for_model(Article)
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    logger.warning(f"Permission {codename} not found for group {group_name}")
            
            logger.info(f"Updated permissions for group {group_name}")
    
    def assign_user_role(self, user: User, role: str) -> bool:
        """Assign editorial role to user."""
        if role not in ['author', 'editor', 'publisher', 'admin']:
            return False
        
        group_name = f'content_{role}'
        
        try:
            # Remove user from all editorial groups first
            editorial_groups = Group.objects.filter(name__startswith='content_')
            user.groups.remove(*editorial_groups)
            
            # Add to new group
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            
            # Update or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.editorial_role = role
            profile.save()
            
            logger.info(f"Assigned role {role} to user {user.id}")
            return True
            
        except Group.DoesNotExist:
            logger.error(f"Editorial group {group_name} not found")
            return False
    
    def get_users_by_role(self, role: str) -> List[User]:
        """Get all users with specific editorial role."""
        group_name = f'content_{role}'
        return User.objects.filter(groups__name=group_name, is_active=True)
    
    def get_user_role(self, user: User) -> Optional[str]:
        """Get user's editorial role."""
        editorial_groups = user.groups.filter(name__startswith='content_').values_list('name', flat=True)
        
        if 'content_admin' in editorial_groups:
            return 'admin'
        elif 'content_publisher' in editorial_groups:
            return 'publisher'
        elif 'content_editor' in editorial_groups:
            return 'editor'
        elif 'content_author' in editorial_groups:
            return 'author'
        
        return None
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a specific role."""
        return ROLE_PERMISSIONS.get(f'content_{role}', [])
    
    def get_role_statistics(self) -> Dict[str, int]:
        """Get statistics about editorial roles."""
        stats = {}
        
        for role in ['author', 'editor', 'publisher', 'admin']:
            group_name = f'content_{role}'
            count = User.objects.filter(
                groups__name=group_name, 
                is_active=True
            ).count()
            stats[role] = count
        
        return stats


class ContentAnalyticsService:
    """
    Service for content analytics and reporting.
    """
    
    def get_user_productivity_stats(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Get productivity statistics for a user."""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Articles created
        articles_created = Article.objects.filter(
            author=user,
            created_at__gte=start_date
        ).count()
        
        # Articles published
        articles_published = Article.objects.filter(
            author=user,
            status='published',
            published_at__gte=start_date
        ).count()
        
        # Articles edited (as editor)
        articles_edited = Article.objects.filter(
            editor=user,
            updated_at__gte=start_date
        ).count()
        
        # Workflow actions
        workflow_actions = EditorialWorkflowLog.objects.filter(
            user=user,
            created_at__gte=start_date
        ).count()
        
        return {
            'period_days': days,
            'articles_created': articles_created,
            'articles_published': articles_published,
            'articles_edited': articles_edited,
            'workflow_actions': workflow_actions,
            'avg_articles_per_day': round(articles_created / days, 2),
        }
    
    def get_content_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get overall content performance statistics."""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Avg, Sum
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Article metrics
        recent_articles = Article.objects.filter(published_at__gte=start_date)
        
        total_views = recent_articles.aggregate(
            total=Sum('view_count')
        )['total'] or 0
        
        avg_views = recent_articles.aggregate(
            avg=Avg('view_count')
        )['avg'] or 0
        
        # Top performing articles
        top_articles = recent_articles.order_by('-view_count')[:10]
        
        return {
            'period_days': days,
            'articles_published': recent_articles.count(),
            'total_views': total_views,
            'average_views_per_article': round(avg_views, 1),
            'top_performing_articles': [
                {
                    'id': str(article.id),
                    'title': article.title,
                    'view_count': article.view_count,
                    'author': article.author.get_full_name(),
                }
                for article in top_articles
            ]
        }