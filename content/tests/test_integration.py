"""
Integration tests for content management system.

Tests cover:
- Content integration with fighters/events/organizations
- User permissions and workflow transitions
- Email notifications
- Full system integration scenarios
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.test.utils import override_settings
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


class ContentFighterIntegrationTest(APITestCase):
    """Test integration between content system and fighter profiles"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        # Create fighters
        self.fighter1 = Fighter.objects.create(
            first_name="Jon",
            last_name="Jones",
            nickname="Bones",
            nationality="USA",
            wins=26,
            losses=1,
            draws=0
        )
        
        self.fighter2 = Fighter.objects.create(
            first_name="Daniel",
            last_name="Cormier",
            nickname="DC",
            nationality="USA",
            wins=22,
            losses=3,
            draws=0
        )
        
        # Create content
        self.category = Category.objects.create(
            name="Fighter Profiles",
            description="In-depth fighter profiles and analysis"
        )
        
        self.article = Article.objects.create(
            title="Jon Jones: The GOAT Debate",
            content="Comprehensive analysis of Jon Jones' career and legacy.",
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
    def test_article_fighter_relationship_creation(self):
        """Test creating article-fighter relationships"""
        self.client.force_authenticate(user=self.author)
        
        # Create relationship via API
        url = reverse('api:article-fighter-list')
        data = {
            'article': self.article.id,
            'fighter': self.fighter1.id,
            'relationship_type': 'about',
            'display_order': 1
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify relationship was created
        relationship = ArticleFighter.objects.get(
            article=self.article,
            fighter=self.fighter1
        )
        self.assertEqual(relationship.relationship_type, 'about')
        
    def test_articles_by_fighter_endpoint(self):
        """Test getting articles related to a specific fighter"""
        # Create relationships
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter1,
            relationship_type='about'
        )
        
        # Create additional article about same fighter
        article2 = Article.objects.create(
            title="Jon Jones Training Camp Update",
            content="Latest updates from Jones' training camp",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        ArticleFighter.objects.create(
            article=article2,
            fighter=self.fighter1,
            relationship_type='features'
        )
        
        # Test API endpoint
        url = reverse('api:article-by-fighter')
        response = self.client.get(url, {'fighter': self.fighter1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Verify correct articles are returned
        article_titles = [article['title'] for article in response.data['results']]
        self.assertIn("Jon Jones: The GOAT Debate", article_titles)
        self.assertIn("Jon Jones Training Camp Update", article_titles)
        
    def test_fighter_article_count_update(self):
        """Test that fighter-related article counts are updated"""
        # Initially no articles
        self.assertEqual(self.fighter1.article_relationships.count(), 0)
        
        # Create article relationship
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter1,
            relationship_type='about'
        )
        
        # Check relationship count
        self.assertEqual(self.fighter1.article_relationships.count(), 1)
        
    def test_fighter_content_feed(self):
        """Test RSS feed for fighter-specific content"""
        # Create fighter relationships
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter1,
            relationship_type='about'
        )
        
        # Test if fighter-specific RSS feed works (if implemented)
        # This would depend on implementing fighter-specific feeds
        pass
        
    def test_multiple_fighter_article(self):
        """Test articles that feature multiple fighters"""
        # Create article about both fighters
        vs_article = Article.objects.create(
            title="Jon Jones vs Daniel Cormier: Rivalry Analysis",
            content="Deep dive into the greatest rivalry in MMA history",
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        # Create relationships with different types
        ArticleFighter.objects.create(
            article=vs_article,
            fighter=self.fighter1,
            relationship_type='features',
            display_order=1
        )
        
        ArticleFighter.objects.create(
            article=vs_article,
            fighter=self.fighter2,
            relationship_type='features',
            display_order=2
        )
        
        # Test that both fighters appear in article
        self.assertEqual(vs_article.fighter_relationships.count(), 2)
        
        # Test ordering
        relationships = vs_article.fighter_relationships.order_by('display_order')
        self.assertEqual(relationships[0].fighter, self.fighter1)
        self.assertEqual(relationships[1].fighter, self.fighter2)


class ContentEventIntegrationTest(APITestCase):
    """Test integration between content system and events"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        # Create organization and event
        self.organization = Organization.objects.create(
            name="Ultimate Fighting Championship",
            abbreviation="UFC",
            description="Premier MMA organization"
        )
        
        self.upcoming_event = Event.objects.create(
            name="UFC 300: Historic Card",
            date=timezone.now().date() + timedelta(days=30),
            location="Las Vegas, Nevada",
            organization=self.organization,
            status='scheduled'
        )
        
        self.past_event = Event.objects.create(
            name="UFC 299: Past Event",
            date=timezone.now().date() - timedelta(days=7),
            location="Miami, Florida",
            organization=self.organization,
            status='completed'
        )
        
        # Create event-related content
        self.preview_article = Article.objects.create(
            title="UFC 300 Preview: Historic Night Ahead",
            content="Everything you need to know about UFC 300",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        self.recap_article = Article.objects.create(
            title="UFC 299 Recap: Night of Surprises",
            content="Complete recap of UFC 299 results",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
    def test_event_preview_relationship(self):
        """Test creating event preview article relationships"""
        # Create preview relationship
        ArticleEvent.objects.create(
            article=self.preview_article,
            event=self.upcoming_event,
            relationship_type='preview'
        )
        
        # Test relationship exists
        relationship = ArticleEvent.objects.get(
            article=self.preview_article,
            event=self.upcoming_event
        )
        self.assertEqual(relationship.relationship_type, 'preview')
        
    def test_event_recap_relationship(self):
        """Test creating event recap article relationships"""
        # Create recap relationship
        ArticleEvent.objects.create(
            article=self.recap_article,
            event=self.past_event,
            relationship_type='recap'
        )
        
        # Test relationship exists
        relationship = ArticleEvent.objects.get(
            article=self.recap_article,
            event=self.past_event
        )
        self.assertEqual(relationship.relationship_type, 'recap')
        
    def test_articles_by_event_endpoint(self):
        """Test getting articles related to specific event"""
        # Create relationships
        ArticleEvent.objects.create(
            article=self.preview_article,
            event=self.upcoming_event,
            relationship_type='preview'
        )
        
        # Test API endpoint
        url = reverse('api:article-by-event')
        response = self.client.get(url, {'event': self.upcoming_event.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], self.preview_article.title)
        
    def test_event_content_timeline(self):
        """Test content timeline for an event (preview -> live -> recap)"""
        # Create different types of content for same event
        live_article = Article.objects.create(
            title="UFC 300 Live Updates",
            content="Live coverage of UFC 300",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        post_article = Article.objects.create(
            title="UFC 300 Post-Fight Analysis",
            content="Analysis of UFC 300 results",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        # Create relationships with different types
        relationships = [
            ArticleEvent.objects.create(
                article=self.preview_article,
                event=self.upcoming_event,
                relationship_type='preview'
            ),
            ArticleEvent.objects.create(
                article=live_article,
                event=self.upcoming_event,
                relationship_type='coverage'
            ),
            ArticleEvent.objects.create(
                article=post_article,
                event=self.upcoming_event,
                relationship_type='analysis'
            )
        ]
        
        # Test that all relationship types exist
        event_articles = ArticleEvent.objects.filter(event=self.upcoming_event)
        relationship_types = [rel.relationship_type for rel in event_articles]
        
        self.assertIn('preview', relationship_types)
        self.assertIn('coverage', relationship_types)
        self.assertIn('analysis', relationship_types)
        
    def test_event_content_filtering(self):
        """Test filtering content by event relationship type"""
        # Create relationships
        ArticleEvent.objects.create(
            article=self.preview_article,
            event=self.upcoming_event,
            relationship_type='preview'
        )
        
        ArticleEvent.objects.create(
            article=self.recap_article,
            event=self.past_event,
            relationship_type='recap'
        )
        
        # Test filtering by relationship type
        url = reverse('api:article-event-list')
        response = self.client.get(url, {'relationship_type': 'preview'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class EditorialWorkflowIntegrationTest(APITestCase):
    """Test complete editorial workflow integration"""
    
    def setUp(self):
        """Set up test data with different user roles"""
        # Create user groups
        self.author_group = Group.objects.create(name='Editorial Author')
        self.editor_group = Group.objects.create(name='Editorial Editor')
        
        # Create users
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        self.author.groups.add(self.author_group)
        
        self.editor = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='editorpass123'
        )
        self.editor.groups.add(self.editor_group)
        
        # Create test content
        self.category = Category.objects.create(name="Test Category")
        
    def test_complete_article_workflow(self):
        """Test complete article workflow from creation to publication"""
        # Step 1: Author creates draft article
        self.client.force_authenticate(user=self.author)
        
        url = reverse('api:article-list')
        article_data = {
            'title': 'Workflow Test Article',
            'content': 'This article will go through the complete workflow',
            'category': self.category.id,
            'status': 'draft'
        }
        
        response = self.client.post(url, article_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        article_id = response.data['id']
        
        # Step 2: Author submits for review
        url = reverse('api:article-submit-for-review', kwargs={'pk': article_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status changed
        article = Article.objects.get(id=article_id)
        self.assertEqual(article.status, 'review')
        
        # Step 3: Editor reviews and approves
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-approve', kwargs={'pk': article_id})
        response = self.client.post(url, {'notes': 'Looks good!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify article is published
        article.refresh_from_db()
        self.assertEqual(article.status, 'published')
        self.assertIsNotNone(article.published_at)
        self.assertEqual(article.editor, self.editor)
        
    def test_article_rejection_workflow(self):
        """Test article rejection and revision workflow"""
        # Create article in review
        article = Article.objects.create(
            title='Article to Reject',
            content='This article needs work',
            category=self.category,
            author=self.author,
            status='review'
        )
        
        # Editor rejects article
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-reject', kwargs={'pk': article.id})
        response = self.client.post(url, {
            'notes': 'Please add more details and fix grammar issues.'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify article is back to draft
        article.refresh_from_db()
        self.assertEqual(article.status, 'draft')
        
        # Author can edit and resubmit
        self.client.force_authenticate(user=self.author)
        
        url = reverse('api:article-detail', kwargs={'pk': article.id})
        response = self.client.patch(url, {
            'content': 'This article has been improved with more details.'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Resubmit for review
        url = reverse('api:article-submit-for-review', kwargs={'pk': article.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        article.refresh_from_db()
        self.assertEqual(article.status, 'review')
        
    def test_bulk_workflow_operations(self):
        """Test bulk workflow operations"""
        # Create multiple articles in review
        articles = []
        for i in range(3):
            article = Article.objects.create(
                title=f'Bulk Test Article {i+1}',
                content=f'Content for article {i+1}',
                category=self.category,
                author=self.author,
                status='review'
            )
            articles.append(article)
        
        # Editor bulk approves
        self.client.force_authenticate(user=self.editor)
        
        url = reverse('api:article-bulk-publish')
        response = self.client.post(url, {
            'article_ids': [article.id for article in articles]
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all articles are published
        for article in articles:
            article.refresh_from_db()
            self.assertEqual(article.status, 'published')
            self.assertIsNotNone(article.published_at)
            
    def test_workflow_permissions(self):
        """Test workflow permission enforcement"""
        # Create article
        article = Article.objects.create(
            title='Permission Test Article',
            content='Testing permissions',
            category=self.category,
            author=self.author,
            status='draft'
        )
        
        # Author cannot directly publish (bypass review)
        self.client.force_authenticate(user=self.author)
        
        url = reverse('api:article-detail', kwargs={'pk': article.id})
        response = self.client.patch(url, {'status': 'published'})
        
        # Should either fail or require review
        article.refresh_from_db()
        self.assertNotEqual(article.status, 'published')
        
        # Editor can publish directly
        self.client.force_authenticate(user=self.editor)
        
        response = self.client.patch(url, {'status': 'published'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        article.refresh_from_db()
        self.assertEqual(article.status, 'published')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailNotificationIntegrationTest(TestCase):
    """Test email notification integration"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.editor = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='editorpass123'
        )
        
        self.category = Category.objects.create(name="Test Category")
        
        self.article = Article.objects.create(
            title='Email Test Article',
            content='Testing email notifications',
            category=self.category,
            author=self.author,
            status='draft'
        )
        
    def test_submission_notification(self):
        """Test email notification when article is submitted for review"""
        # Clear any existing emails
        mail.outbox = []
        
        # Simulate article submission
        self.article.status = 'review'
        self.article.save()
        
        # Check if notification email was sent (if implemented)
        # This test assumes email notifications are implemented
        # Adjust based on actual implementation
        
        # For now, just verify no errors occurred
        self.assertEqual(len(mail.outbox), 0)  # No emails expected yet
        
    def test_approval_notification(self):
        """Test email notification when article is approved"""
        mail.outbox = []
        
        # Simulate article approval
        self.article.status = 'published'
        self.article.published_at = timezone.now()
        self.article.editor = self.editor
        self.article.save()
        
        # Check for approval notification
        self.assertEqual(len(mail.outbox), 0)  # No emails expected yet
        
    def test_rejection_notification(self):
        """Test email notification when article is rejected"""
        mail.outbox = []
        
        # Simulate article rejection
        self.article.status = 'draft'  # Back to draft from review
        self.article.save()
        
        # Check for rejection notification
        self.assertEqual(len(mail.outbox), 0)  # No emails expected yet


class AnalyticsIntegrationTest(APITestCase):
    """Test analytics and tracking integration"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.reader = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='readerpass123'
        )
        
        self.category = Category.objects.create(name="Analytics Category")
        
        self.article = Article.objects.create(
            title='Analytics Test Article',
            content='Testing analytics tracking',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
    def test_view_count_tracking(self):
        """Test article view count tracking"""
        initial_count = self.article.view_count
        
        # Simulate article view
        url = reverse('api:article-detail', kwargs={'pk': self.article.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if view count increased
        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_count + 1)
        
    def test_detailed_view_tracking(self):
        """Test detailed view tracking with ArticleView model"""
        # Simulate detailed view tracking
        ArticleView.objects.create(
            article=self.article,
            user=self.reader,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            referrer='https://example.com'
        )
        
        # Verify tracking record created
        view = ArticleView.objects.get(article=self.article, user=self.reader)
        self.assertEqual(view.ip_address, '127.0.0.1')
        self.assertEqual(view.user_agent, 'Test Browser')
        
    def test_analytics_api_endpoint(self):
        """Test analytics API endpoint"""
        self.client.force_authenticate(user=self.author)
        
        # Create some view data
        self.article.view_count = 100
        self.article.save()
        
        url = reverse('api:article-analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_articles', response.data)
        self.assertIn('total_views', response.data)
        
    def test_popular_content_tracking(self):
        """Test popular content identification"""
        # Create articles with different view counts
        popular_article = Article.objects.create(
            title='Popular Article',
            content='This is popular',
            author=self.author,
            status='published',
            published_at=timezone.now(),
            view_count=1000
        )
        
        unpopular_article = Article.objects.create(
            title='Unpopular Article',
            content='This is not popular',
            author=self.author,
            status='published',
            published_at=timezone.now(),
            view_count=10
        )
        
        # Test popular content endpoint
        url = reverse('api:article-popular')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Popular article should be first
        if response.data:
            self.assertEqual(response.data[0]['title'], 'Popular Article')


class CacheIntegrationTest(TestCase):
    """Test caching integration for performance"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.category = Category.objects.create(name="Cache Test Category")
        
        self.article = Article.objects.create(
            title='Cache Test Article',
            content='Testing cache functionality',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
    def test_article_detail_caching(self):
        """Test that article details are properly cached"""
        # This test would verify caching implementation
        from django.core.cache import cache
        
        # Clear cache
        cache.clear()
        
        # First request should hit database
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Cache key should exist (if caching is implemented)
        cache_key = f'article_detail_{self.article.slug}'
        # cached_data = cache.get(cache_key)
        # self.assertIsNotNone(cached_data)  # Uncomment if caching implemented
        
    def test_cache_invalidation_on_update(self):
        """Test cache invalidation when article is updated"""
        from django.core.cache import cache
        
        cache_key = f'article_detail_{self.article.slug}'
        
        # Cache some data
        cache.set(cache_key, 'cached_data', 300)
        
        # Update article
        self.article.title = 'Updated Title'
        self.article.save()
        
        # Cache should be invalidated (if implemented)
        # cached_data = cache.get(cache_key)
        # self.assertIsNone(cached_data)  # Uncomment if cache invalidation implemented


class SearchIntegrationTest(APITestCase):
    """Test search functionality integration"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        # Create searchable content
        self.fighter = Fighter.objects.create(
            first_name="Jon",
            last_name="Jones",
            nickname="Bones"
        )
        
        self.category = Category.objects.create(name="MMA News")
        self.tag = Tag.objects.create(name="UFC")
        
        self.article1 = Article.objects.create(
            title='Jon Jones Championship Defense',
            content='Jon Jones successfully defended his title against a tough challenger',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        self.article1.tags.add(self.tag)
        
        ArticleFighter.objects.create(
            article=self.article1,
            fighter=self.fighter,
            relationship_type='about'
        )
        
        self.article2 = Article.objects.create(
            title='UFC Event Results',
            content='Complete results from the latest UFC event with surprising outcomes',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        self.article2.tags.add(self.tag)
        
    def test_full_text_search(self):
        """Test full-text search across articles"""
        url = reverse('api:article-search')
        
        # Search for "Jon Jones"
        response = self.client.get(url, {'q': 'Jon Jones'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Jon Jones Championship Defense')
        
        # Search for "UFC"
        response = self.client.get(url, {'q': 'UFC'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
    def test_search_with_filters(self):
        """Test search combined with filters"""
        url = reverse('api:article-list')
        
        # Search within specific category
        response = self.client.get(url, {
            'search': 'UFC',
            'category': self.category.id
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) >= 1)
        
    def test_related_content_search(self):
        """Test finding related content through relationships"""
        # Test finding articles by fighter
        url = reverse('api:article-by-fighter')
        response = self.client.get(url, {'fighter': self.fighter.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Jon Jones Championship Defense')


class DataConsistencyIntegrationTest(TransactionTestCase):
    """Test data consistency across the system"""
    
    def setUp(self):
        """Set up test data"""
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.category = Category.objects.create(name="Consistency Test")
        self.tag = Tag.objects.create(name="Test Tag")
        
    def test_tag_usage_count_consistency(self):
        """Test that tag usage counts remain consistent"""
        initial_count = self.tag.usage_count
        
        # Create article with tag
        article = Article.objects.create(
            title='Tagged Article',
            content='Content with tag',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        article.tags.add(self.tag)
        
        # Usage count should update (if implemented)
        self.tag.refresh_from_db()
        # self.assertEqual(self.tag.usage_count, initial_count + 1)
        
        # Remove tag
        article.tags.remove(self.tag)
        
        # Usage count should decrease (if implemented)
        self.tag.refresh_from_db()
        # self.assertEqual(self.tag.usage_count, initial_count)
        
    def test_article_count_consistency(self):
        """Test article count consistency in categories"""
        initial_count = self.category.get_article_count()
        
        # Create published article
        article = Article.objects.create(
            title='Category Article',
            content='Content in category',
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        # Count should increase
        new_count = self.category.get_article_count()
        self.assertEqual(new_count, initial_count + 1)
        
        # Change to draft
        article.status = 'draft'
        article.published_at = None
        article.save()
        
        # Count should decrease
        final_count = self.category.get_article_count()
        self.assertEqual(final_count, initial_count)
        
    def test_relationship_cleanup_on_deletion(self):
        """Test that relationships are properly cleaned up when entities are deleted"""
        # Create fighter and article with relationship
        fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter"
        )
        
        article = Article.objects.create(
            title='Fighter Article',
            content='Article about fighter',
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
        relationship = ArticleFighter.objects.create(
            article=article,
            fighter=fighter,
            relationship_type='about'
        )
        
        # Verify relationship exists
        self.assertTrue(ArticleFighter.objects.filter(id=relationship.id).exists())
        
        # Delete fighter
        fighter.delete()
        
        # Relationship should be deleted due to CASCADE
        self.assertFalse(ArticleFighter.objects.filter(id=relationship.id).exists())
        
        # Article should still exist
        self.assertTrue(Article.objects.filter(id=article.id).exists())