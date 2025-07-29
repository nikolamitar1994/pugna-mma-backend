"""
Comprehensive API tests for content management system.

Tests cover:
- REST API endpoints for CRUD operations
- Permission-based access control
- Search, filtering, and advanced features
- Editorial workflow API endpoints
- Content analytics endpoints
"""

import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization
from content.models import (
    Category, Tag, Article, ArticleFighter, ArticleEvent, 
    ArticleOrganization, ArticleView
)

User = get_user_model()


class ContentAPIPermissionTest(APITestCase):
    """Test permission-based access control for content APIs"""
    
    def setUp(self):
        """Set up test users with different roles"""
        # Create user groups
        self.admin_group = Group.objects.create(name='Editorial Admin')
        self.editor_group = Group.objects.create(name='Editorial Editor')
        self.author_group = Group.objects.create(name='Editorial Author')
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='editorpass123'
        )
        self.editor_user.groups.add(self.editor_group)
        
        self.author_user = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        self.author_user.groups.add(self.author_group)
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
        # Create test content
        self.category = Category.objects.create(name="Test Category")
        self.tag = Tag.objects.create(name="Test Tag")
        
        self.article = Article.objects.create(
            title="Test Article",
            content="Test content",
            category=self.category,
            author=self.author_user,
            status='published',
            published_at=timezone.now()
        )
        
    def test_article_list_public_access(self):
        """Test that published articles are publicly accessible"""
        url = reverse('api:article-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_article_create_requires_authentication(self):
        """Test that creating articles requires authentication"""
        url = reverse('api:article-list')
        data = {
            'title': 'New Article',
            'content': 'New content',
            'status': 'draft'
        }
        
        # Unauthenticated request should fail
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_author_can_create_articles(self):
        """Test that authors can create articles"""
        self.client.force_authenticate(user=self.author_user)
        
        url = reverse('api:article-list')
        data = {
            'title': 'Author Article',
            'content': 'Author content',
            'category': self.category.id,
            'status': 'draft'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that author is automatically set
        article = Article.objects.get(id=response.data['id'])
        self.assertEqual(article.author, self.author_user)
        
    def test_author_can_edit_own_articles(self):
        """Test that authors can edit their own articles"""
        self.client.force_authenticate(user=self.author_user)
        
        url = reverse('api:article-detail', kwargs={'pk': self.article.id})
        data = {
            'title': 'Updated Title',
            'content': 'Updated content',
            'status': 'draft'
        }
        
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        
    def test_author_cannot_edit_others_articles(self):
        """Test that authors cannot edit other authors' articles"""
        other_author = User.objects.create_user(
            username='other_author',
            email='other@example.com',
            password='otherpass123'
        )
        other_author.groups.add(self.author_group)
        
        other_article = Article.objects.create(
            title="Other Article",
            content="Other content",
            author=other_author,
            status='draft'
        )
        
        self.client.force_authenticate(user=self.author_user)
        
        url = reverse('api:article-detail', kwargs={'pk': other_article.id})
        data = {'title': 'Trying to update'}
        
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_editor_can_edit_any_article(self):
        """Test that editors can edit any article"""
        self.client.force_authenticate(user=self.editor_user)
        
        url = reverse('api:article-detail', kwargs={'pk': self.article.id})
        data = {
            'title': 'Editor Updated Title',
            'status': 'review'
        }
        
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Editor Updated Title')
        
    def test_category_management_permissions(self):
        """Test category management permissions"""
        # Regular users cannot create categories
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('api:category-list')
        data = {'name': 'New Category'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admins can create categories
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ArticleAPITest(APITestCase):
    """Test Article API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(name="Test Category")
        self.tag1 = Tag.objects.create(name="Tag1")
        self.tag2 = Tag.objects.create(name="Tag2")
        
        # Create test articles
        self.published_article = Article.objects.create(
            title="Published Article",
            content="Published content",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now(),
            is_featured=True
        )
        self.published_article.tags.add(self.tag1)
        
        self.draft_article = Article.objects.create(
            title="Draft Article",
            content="Draft content",
            category=self.category,
            author=self.user,
            status='draft'
        )
        
        # Create fighter and event for relationship testing
        self.fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter"
        )
        
        self.organization = Organization.objects.create(
            name="Test Org",
            abbreviation="TEST",
            description="Test organization"
        )
        
        self.event = Event.objects.create(
            name="Test Event",
            date=timezone.now().date(),
            location="Test Location",
            organization=self.organization,
            status='scheduled'
        )
        
    def test_article_list(self):
        """Test article list endpoint"""
        url = reverse('api:article-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return published articles for unauthenticated users
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], "Published Article")
        
    def test_article_detail(self):
        """Test article detail endpoint"""
        url = reverse('api:article-detail', kwargs={'pk': self.published_article.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Published Article")
        self.assertIn('category', response.data)
        self.assertIn('tags', response.data)
        
    def test_article_create(self):
        """Test article creation"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-list')
        data = {
            'title': 'New Test Article',
            'content': 'New test content',
            'category': self.category.id,
            'tags': [self.tag1.id, self.tag2.id],
            'status': 'draft',
            'article_type': 'news'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify article was created correctly
        article = Article.objects.get(id=response.data['id'])
        self.assertEqual(article.title, 'New Test Article')
        self.assertEqual(article.author, self.user)
        self.assertEqual(article.tags.count(), 2)
        
    def test_article_update(self):
        """Test article update"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-detail', kwargs={'pk': self.draft_article.id})
        data = {
            'title': 'Updated Title',
            'content': 'Updated content',
            'status': 'published'
        }
        
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify update
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.title, 'Updated Title')
        self.assertEqual(self.draft_article.status, 'published')
        self.assertIsNotNone(self.draft_article.published_at)
        
    def test_article_delete(self):
        """Test article deletion"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-detail', kwargs={'pk': self.draft_article.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Article.objects.filter(id=self.draft_article.id).exists())
        
    def test_article_filtering(self):
        """Test article filtering options"""
        # Test status filtering
        url = reverse('api:article-list')
        response = self.client.get(url, {'status': 'published'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Test category filtering
        response = self.client.get(url, {'category': self.category.id})
        self.assertEqual(len(response.data['results']), 1)
        
        # Test is_featured filtering
        response = self.client.get(url, {'is_featured': 'true'})
        self.assertEqual(len(response.data['results']), 1)
        
    def test_article_search(self):
        """Test article search functionality"""
        url = reverse('api:article-search')
        
        # Search by title
        response = self.client.get(url, {'q': 'Published'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Search by content
        response = self.client.get(url, {'q': 'Published content'})
        self.assertEqual(len(response.data['results']), 1)
        
        # Search with no results
        response = self.client.get(url, {'q': 'nonexistent'})
        self.assertEqual(len(response.data['results']), 0)
        
    def test_featured_articles_endpoint(self):
        """Test featured articles endpoint"""
        url = reverse('api:article-featured')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_featured'])
        
    def test_breaking_articles_endpoint(self):
        """Test breaking news articles endpoint"""
        # Create breaking news article
        breaking_article = Article.objects.create(
            title="Breaking News",
            content="Breaking content",
            author=self.user,
            status='published',
            published_at=timezone.now(),
            is_breaking=True
        )
        
        url = reverse('api:article-breaking')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['is_breaking'])
        
    def test_trending_articles_endpoint(self):
        """Test trending articles endpoint"""
        # Increase view count for the published article
        self.published_article.view_count = 100
        self.published_article.save()
        
        url = reverse('api:article-trending')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
        
    def test_related_articles_endpoint(self):
        """Test related articles endpoint"""
        # Create another article with same tags
        related_article = Article.objects.create(
            title="Related Article",
            content="Related content",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        related_article.tags.add(self.tag1)
        
        url = reverse('api:article-related', kwargs={'pk': self.published_article.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "Related Article")
        
    def test_articles_by_fighter_endpoint(self):
        """Test articles by fighter endpoint"""
        # Create article-fighter relationship
        ArticleFighter.objects.create(
            article=self.published_article,
            fighter=self.fighter,
            relationship_type='about'
        )
        
        url = reverse('api:article-by-fighter')
        response = self.client.get(url, {'fighter': self.fighter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_articles_by_event_endpoint(self):
        """Test articles by event endpoint"""
        # Create article-event relationship
        ArticleEvent.objects.create(
            article=self.published_article,
            event=self.event,
            relationship_type='preview'
        )
        
        url = reverse('api:article-by-event')
        response = self.client.get(url, {'event': self.event.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class CategoryAPITest(APITestCase):
    """Test Category API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        self.parent_category = Category.objects.create(
            name="Parent Category",
            description="Parent description"
        )
        
        self.child_category = Category.objects.create(
            name="Child Category",
            parent=self.parent_category
        )
        
    def test_category_list(self):
        """Test category list endpoint"""
        url = reverse('api:category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_category_tree_endpoint(self):
        """Test category tree structure endpoint"""
        url = reverse('api:category-tree')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return root categories
        self.assertEqual(len(response.data), 1)
        # Root category should have children
        self.assertIn('children', response.data[0])
        
    def test_category_articles_endpoint(self):
        """Test category articles endpoint"""
        # Create test article in category
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        Article.objects.create(
            title="Category Article",
            content="Content",
            category=self.parent_category,
            author=user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('api:category-articles', kwargs={'pk': self.parent_category.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_category_create_requires_permission(self):
        """Test that category creation requires proper permissions"""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
        self.client.force_authenticate(user=regular_user)
        
        url = reverse('api:category-list')
        data = {'name': 'New Category'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TagAPITest(APITestCase):
    """Test Tag API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        self.tag1 = Tag.objects.create(
            name="Popular Tag",
            usage_count=10
        )
        
        self.tag2 = Tag.objects.create(
            name="Less Popular Tag",
            usage_count=5
        )
        
    def test_tag_list(self):
        """Test tag list endpoint"""
        url = reverse('api:tag-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_popular_tags_endpoint(self):
        """Test popular tags endpoint"""
        url = reverse('api:tag-popular')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be ordered by usage count
        self.assertEqual(response.data[0]['name'], "Popular Tag")
        
    def test_tag_articles_endpoint(self):
        """Test tag articles endpoint"""
        # Create test article with tag
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        article = Article.objects.create(
            title="Tagged Article",
            content="Content",
            author=user,
            status='published',
            published_at=timezone.now()
        )
        article.tags.add(self.tag1)
        
        url = reverse('api:tag-articles', kwargs={'pk': self.tag1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class EditorialWorkflowAPITest(APITestCase):
    """Test editorial workflow API features"""
    
    def setUp(self):
        """Set up test data"""
        # Create users with different roles
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.editor = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='editorpass123',
            is_staff=True
        )
        
        # Create test article
        self.article = Article.objects.create(
            title="Workflow Test Article",
            content="Test content",
            author=self.author,
            status='draft'
        )
        
    def test_submit_for_review_action(self):
        """Test submit for review workflow action"""
        self.client.force_authenticate(user=self.author)
        
        url = reverse('api:article-submit-for-review', kwargs={'pk': self.article.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'review')
        
    def test_approve_article_action(self):
        """Test approve article workflow action"""
        self.article.status = 'review'
        self.article.save()
        
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-approve', kwargs={'pk': self.article.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'published')
        self.assertIsNotNone(self.article.published_at)
        
    def test_reject_article_action(self):
        """Test reject article workflow action"""
        self.article.status = 'review'
        self.article.save()
        
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-reject', kwargs={'pk': self.article.id})
        data = {'notes': 'Needs more work on the introduction'}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'draft')
        
    def test_archive_article_action(self):
        """Test archive article workflow action"""
        self.article.status = 'published'
        self.article.published_at = timezone.now()
        self.article.save()
        
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-archive', kwargs={'pk': self.article.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, 'archived')
        
    def test_bulk_publish_action(self):
        """Test bulk publish workflow action"""
        # Create additional articles for bulk action
        article2 = Article.objects.create(
            title="Bulk Test Article 2",
            content="Content 2",
            author=self.author,
            status='review'
        )
        
        article3 = Article.objects.create(
            title="Bulk Test Article 3",
            content="Content 3",
            author=self.author,
            status='review'
        )
        
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-bulk-publish')
        data = {'article_ids': [article2.id, article3.id]}
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that articles were published
        article2.refresh_from_db()
        article3.refresh_from_db()
        
        self.assertEqual(article2.status, 'published')
        self.assertEqual(article3.status, 'published')
        self.assertIsNotNone(article2.published_at)
        self.assertIsNotNone(article3.published_at)
        
    def test_my_articles_endpoint(self):
        """Test endpoint for getting current user's articles"""
        self.client.force_authenticate(user=self.author)
        
        url = reverse('api:article-my-articles')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], "Workflow Test Article")
        
    def test_pending_review_endpoint(self):
        """Test endpoint for getting articles pending review"""
        self.article.status = 'review'
        self.article.save()
        
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-pending-review')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class ContentAnalyticsAPITest(APITestCase):
    """Test content analytics API features"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create articles with different view counts
        self.article1 = Article.objects.create(
            title="Popular Article",
            content="Content",
            author=self.user,
            status='published',
            published_at=timezone.now(),
            view_count=100
        )
        
        self.article2 = Article.objects.create(
            title="Less Popular Article",
            content="Content",
            author=self.user,
            status='published',
            published_at=timezone.now(),
            view_count=50
        )
        
    def test_content_analytics_endpoint(self):
        """Test content analytics summary endpoint"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check analytics data structure
        self.assertIn('total_articles', response.data)
        self.assertIn('published_articles', response.data)
        self.assertIn('draft_articles', response.data)
        self.assertIn('total_views', response.data)
        self.assertIn('avg_views_per_article', response.data)
        
    def test_popular_content_endpoint(self):
        """Test popular content endpoint"""
        url = reverse('api:article-popular')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be ordered by view count
        self.assertEqual(response.data[0]['title'], "Popular Article")
        
    def test_content_performance_endpoint(self):
        """Test content performance over time endpoint"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-performance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('daily_stats', response.data)
        self.assertIn('weekly_stats', response.data)


class RelationshipAPITest(APITestCase):
    """Test article relationship API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.article = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        self.fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter"
        )
        
        self.organization = Organization.objects.create(
            name="Test Org",
            abbreviation="TEST",
            description="Test organization"
        )
        
        self.event = Event.objects.create(
            name="Test Event",
            date=timezone.now().date(),
            location="Test Location",
            organization=self.organization,
            status='scheduled'
        )
        
    def test_article_fighter_relationship_crud(self):
        """Test ArticleFighter relationship CRUD operations"""
        self.client.force_authenticate(user=self.user)
        
        # Create relationship
        url = reverse('api:article-fighter-list')
        data = {
            'article': self.article.id,
            'fighter': self.fighter.id,
            'relationship_type': 'about',
            'display_order': 1
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        relationship_id = response.data['id']
        
        # Read relationship
        url = reverse('api:article-fighter-detail', kwargs={'pk': relationship_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Update relationship
        data = {'relationship_type': 'features'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['relationship_type'], 'features')
        
        # Delete relationship
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
    def test_article_event_relationship_crud(self):
        """Test ArticleEvent relationship CRUD operations"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-event-list')
        data = {
            'article': self.article.id,
            'event': self.event.id,
            'relationship_type': 'preview'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    def test_article_organization_relationship_crud(self):
        """Test ArticleOrganization relationship CRUD operations"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('api:article-organization-list')
        data = {
            'article': self.article.id,
            'organization': self.organization.id,
            'relationship_type': 'news'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    def test_relationship_filtering(self):
        """Test filtering relationships by article and type"""
        # Create test relationships
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter,
            relationship_type='about'
        )
        
        # Test filtering by article
        url = reverse('api:article-fighter-list')
        response = self.client.get(url, {'article': self.article.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Test filtering by relationship type
        response = self.client.get(url, {'relationship_type': 'about'})
        self.assertEqual(len(response.data['results']), 1)
        
        response = self.client.get(url, {'relationship_type': 'mentions'})
        self.assertEqual(len(response.data['results']), 0)


class APIOrderingAndPaginationTest(APITestCase):
    """Test API ordering and pagination features"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create multiple articles for testing
        for i in range(15):
            Article.objects.create(
                title=f"Article {i:02d}",
                content=f"Content {i}",
                author=self.user,
                status='published',
                published_at=timezone.now() - timedelta(days=i),
                view_count=i * 10
            )
            
    def test_article_pagination(self):
        """Test article list pagination"""
        url = reverse('api:article-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # Check pagination works
        if response.data['next']:
            next_response = self.client.get(response.data['next'])
            self.assertEqual(next_response.status_code, status.HTTP_200_OK)
            
    def test_article_ordering(self):
        """Test article ordering options"""
        url = reverse('api:article-list')
        
        # Test ordering by published date (default)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test ordering by view count
        response = self.client.get(url, {'ordering': '-view_count'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # First article should have highest view count
        if response.data['results']:
            first_article = response.data['results'][0]
            self.assertTrue(first_article['view_count'] >= 0)
            
    def test_search_pagination(self):
        """Test that search results are properly paginated"""
        url = reverse('api:article-search')
        response = self.client.get(url, {'q': 'Article'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)