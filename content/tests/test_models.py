"""
Comprehensive tests for content management system models.

Tests cover:
- Model creation and validation
- Model methods and properties
- Editorial workflow state transitions
- Relationship models
- SEO functionality
"""

import uuid
from datetime import datetime, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.utils import IntegrityError

from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization
from content.models import (
    Category, Tag, Article, ArticleFighter, ArticleEvent, 
    ArticleOrganization, ArticleView
)

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test Category model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.parent_category = Category.objects.create(
            name="News",
            description="News category"
        )
        
    def test_category_creation(self):
        """Test basic category creation"""
        category = Category.objects.create(
            name="UFC News",
            description="UFC related news"
        )
        
        self.assertEqual(category.name, "UFC News")
        self.assertEqual(category.slug, "ufc-news")  # Auto-generated
        self.assertTrue(category.is_active)
        self.assertEqual(category.order, 0)
        
    def test_hierarchical_structure(self):
        """Test parent-child category relationships"""
        child_category = Category.objects.create(
            name="Fight Results",
            parent=self.parent_category
        )
        
        self.assertEqual(child_category.parent, self.parent_category)
        self.assertIn(child_category, self.parent_category.children.all())
        
    def test_slug_auto_generation(self):
        """Test automatic slug generation"""
        category = Category.objects.create(name="Test Category with Spaces")
        self.assertEqual(category.slug, "test-category-with-spaces")
        
    def test_unique_slug_constraint(self):
        """Test that slugs must be unique"""
        Category.objects.create(name="Test Category")
        
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Test Category")  # Same slug
            
    def test_str_representation(self):
        """Test string representation of categories"""
        child = Category.objects.create(
            name="Fight Results",
            parent=self.parent_category
        )
        
        self.assertEqual(str(self.parent_category), "News")
        self.assertEqual(str(child), "News → Fight Results")
        
    def test_get_full_path(self):
        """Test full hierarchical path method"""
        child = Category.objects.create(
            name="UFC Results",
            parent=self.parent_category
        )
        grandchild = Category.objects.create(
            name="Main Events",
            parent=child
        )
        
        expected_path = ["News", "UFC Results", "Main Events"]
        self.assertEqual(grandchild.get_full_path(), expected_path)
        
    def test_get_article_count(self):
        """Test article count method including descendants"""
        # Create test user and articles
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        child_category = Category.objects.create(
            name="UFC News",
            parent=self.parent_category
        )
        
        # Create articles in parent and child categories
        Article.objects.create(
            title="Parent Article",
            content="Content",
            category=self.parent_category,
            status='published',
            author=user,
            published_at=timezone.now()
        )
        
        Article.objects.create(
            title="Child Article",
            content="Content",
            category=child_category,
            status='published',
            author=user,
            published_at=timezone.now()
        )
        
        # Draft article should not be counted
        Article.objects.create(
            title="Draft Article",
            content="Content",
            category=child_category,
            status='draft',
            author=user
        )
        
        # Parent category should count its own + child articles
        self.assertEqual(self.parent_category.get_article_count(), 2)
        # Child category should count only its own
        self.assertEqual(child_category.get_article_count(), 1)


class TagModelTest(TestCase):
    """Test Tag model functionality"""
    
    def test_tag_creation(self):
        """Test basic tag creation"""
        tag = Tag.objects.create(
            name="UFC",
            description="Ultimate Fighting Championship",
            color="#dc3545"
        )
        
        self.assertEqual(tag.name, "UFC")
        self.assertEqual(tag.slug, "ufc")
        self.assertEqual(tag.color, "#dc3545")
        self.assertEqual(tag.usage_count, 0)
        
    def test_tag_slug_generation(self):
        """Test automatic slug generation for tags"""
        tag = Tag.objects.create(name="Mixed Martial Arts")
        self.assertEqual(tag.slug, "mixed-martial-arts")
        
    def test_tag_unique_name(self):
        """Test that tag names must be unique"""
        Tag.objects.create(name="UFC")
        
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="UFC")
            
    def test_tag_color_choices(self):
        """Test that color choices work correctly"""
        valid_colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', 
                       '#6f42c1', '#fd7e14', '#20c997', '#6c757d']
        
        for color in valid_colors:
            tag = Tag.objects.create(
                name=f"Test Tag {color}",
                color=color
            )
            self.assertEqual(tag.color, color)


class ArticleModelTest(TestCase):
    """Test Article model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testauthor',
            email='author@example.com',
            password='testpass123'
        )
        
        self.editor = User.objects.create_user(
            username='testeditor',
            email='editor@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name="Test Category"
        )
        
        self.tag = Tag.objects.create(
            name="Test Tag"
        )
        
    def test_article_creation(self):
        """Test basic article creation"""
        article = Article.objects.create(
            title="Test Article",
            content="<p>This is test content with HTML.</p>",
            category=self.category,
            author=self.user,
            status='draft'
        )
        
        self.assertEqual(article.title, "Test Article")
        self.assertEqual(article.slug, "test-article")
        self.assertEqual(article.status, 'draft')
        self.assertEqual(article.article_type, 'news')  # Default
        self.assertFalse(article.is_featured)
        self.assertFalse(article.is_breaking)
        
    def test_slug_auto_generation_and_uniqueness(self):
        """Test automatic slug generation and uniqueness handling"""
        article1 = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user
        )
        
        article2 = Article.objects.create(
            title="Test Article",  # Same title
            content="Different content",
            author=self.user
        )
        
        self.assertEqual(article1.slug, "test-article")
        self.assertEqual(article2.slug, "test-article-1")
        
    def test_excerpt_auto_generation(self):
        """Test automatic excerpt generation from content"""
        long_content = "<p>" + "This is a long article. " * 50 + "</p>"
        
        article = Article.objects.create(
            title="Long Article",
            content=long_content,
            author=self.user
        )
        
        # Should auto-generate excerpt from content
        self.assertTrue(len(article.excerpt) > 0)
        self.assertTrue(len(article.excerpt) <= 303)  # 300 + "..."
        self.assertNotIn("<p>", article.excerpt)  # HTML should be stripped
        
    def test_reading_time_calculation(self):
        """Test automatic reading time calculation"""
        # Create content with approximately 400 words (should be 2 minutes)
        words = ["word"] * 400
        content = "<p>" + " ".join(words) + "</p>"
        
        article = Article.objects.create(
            title="Long Article",
            content=content,
            author=self.user
        )
        
        self.assertEqual(article.reading_time, 2)  # 400 words / 200 wpm = 2 minutes
        
    def test_published_at_auto_setting(self):
        """Test automatic published_at setting when status changes"""
        article = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user,
            status='draft'
        )
        
        self.assertIsNone(article.published_at)
        
        # Change to published
        article.status = 'published'
        article.save()
        
        self.assertIsNotNone(article.published_at)
        self.assertTrue(article.published_at <= timezone.now())
        
    def test_published_at_clearing_on_unpublish(self):
        """Test that published_at is cleared when unpublishing"""
        article = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user,
            status='published'
        )
        
        self.assertIsNotNone(article.published_at)
        
        # Change back to draft
        article.status = 'draft'
        article.save()
        
        self.assertIsNone(article.published_at)
        
    def test_is_published_property(self):
        """Test is_published property logic"""
        # Draft article
        draft_article = Article.objects.create(
            title="Draft Article",
            content="Content",
            author=self.user,
            status='draft'
        )
        self.assertFalse(draft_article.is_published)
        
        # Published article
        published_article = Article.objects.create(
            title="Published Article",
            content="Content",
            author=self.user,
            status='published'
        )
        self.assertTrue(published_article.is_published)
        
        # Future published article
        future_article = Article.objects.create(
            title="Future Article",
            content="Content",
            author=self.user,
            status='published',
            published_at=timezone.now() + timedelta(days=1)
        )
        self.assertFalse(future_article.is_published)
        
    def test_seo_methods(self):
        """Test SEO-related methods"""
        article = Article.objects.create(
            title="Test Article",
            content="Content",
            excerpt="Test excerpt",
            meta_title="Custom SEO Title",
            meta_description="Custom SEO Description",
            author=self.user
        )
        
        self.assertEqual(article.get_seo_title(), "Custom SEO Title")
        self.assertEqual(article.get_seo_description(), "Custom SEO Description")
        
        # Test fallback to defaults
        article_no_meta = Article.objects.create(
            title="No Meta Article",
            content="Content",
            excerpt="Test excerpt",
            author=self.user
        )
        
        self.assertEqual(article_no_meta.get_seo_title(), "No Meta Article")
        self.assertEqual(article_no_meta.get_seo_description(), "Test excerpt")
        
    def test_increment_view_count(self):
        """Test view count increment method"""
        article = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user
        )
        
        initial_count = article.view_count
        article.increment_view_count()
        article.refresh_from_db()
        
        self.assertEqual(article.view_count, initial_count + 1)
        
    def test_get_related_articles(self):
        """Test related articles functionality"""
        # Create articles with shared category and tags
        article1 = Article.objects.create(
            title="Main Article",
            content="Content",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        article1.tags.add(self.tag)
        
        article2 = Article.objects.create(
            title="Related Article 1",
            content="Content",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        article3 = Article.objects.create(
            title="Related Article 2",
            content="Content",
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        article3.tags.add(self.tag)
        
        # Draft article should not appear in related
        Article.objects.create(
            title="Draft Article",
            content="Content",
            category=self.category,
            author=self.user,
            status='draft'
        )
        
        related = article1.get_related_articles()
        related_titles = [a.title for a in related]
        
        self.assertIn("Related Article 1", related_titles)  # Same category
        self.assertIn("Related Article 2", related_titles)  # Same tag
        self.assertNotIn("Draft Article", related_titles)  # Not published
        self.assertNotIn("Main Article", related_titles)  # Exclude self
        
    def test_tag_relationship(self):
        """Test many-to-many relationship with tags"""
        article = Article.objects.create(
            title="Tagged Article",
            content="Content",
            author=self.user
        )
        
        tag2 = Tag.objects.create(name="Second Tag")
        
        article.tags.add(self.tag, tag2)
        
        self.assertEqual(article.tags.count(), 2)
        self.assertIn(self.tag, article.tags.all())
        self.assertIn(tag2, article.tags.all())


class ArticleRelationshipModelTest(TestCase):
    """Test article relationship models"""
    
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
            author=self.user
        )
        
        # Create related objects
        self.fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter",
            nickname="The Tester"
        )
        
        self.organization = Organization.objects.create(
            name="Test Organization",
            abbreviation="TEST",
            description="Test organization"
        )
        
        self.event = Event.objects.create(
            name="Test Event 1",
            date=timezone.now().date(),
            location="Test Location",
            organization=self.organization,
            status='scheduled'
        )
        
    def test_article_fighter_relationship(self):
        """Test ArticleFighter relationship model"""
        relationship = ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter,
            relationship_type='about',
            display_order=1
        )
        
        self.assertEqual(relationship.article, self.article)
        self.assertEqual(relationship.fighter, self.fighter)
        self.assertEqual(relationship.relationship_type, 'about')
        self.assertEqual(relationship.display_order, 1)
        
        # Test string representation
        expected_str = f"{self.article.title} → {self.fighter.get_full_name()} (about)"
        self.assertEqual(str(relationship), expected_str)
        
    def test_article_event_relationship(self):
        """Test ArticleEvent relationship model"""
        relationship = ArticleEvent.objects.create(
            article=self.article,
            event=self.event,
            relationship_type='preview',
            display_order=1
        )
        
        self.assertEqual(relationship.article, self.article)
        self.assertEqual(relationship.event, self.event)
        self.assertEqual(relationship.relationship_type, 'preview')
        
    def test_article_organization_relationship(self):
        """Test ArticleOrganization relationship model"""
        relationship = ArticleOrganization.objects.create(
            article=self.article,
            organization=self.organization,
            relationship_type='news',
            display_order=1
        )
        
        self.assertEqual(relationship.article, self.article)
        self.assertEqual(relationship.organization, self.organization)
        self.assertEqual(relationship.relationship_type, 'news')
        
    def test_unique_constraints(self):
        """Test unique constraints on relationship models"""
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter,
            relationship_type='about'
        )
        
        # Should not allow duplicate article-fighter pairs
        with self.assertRaises(IntegrityError):
            ArticleFighter.objects.create(
                article=self.article,
                fighter=self.fighter,
                relationship_type='mentions'  # Different type, but same pair
            )


class ArticleViewModelTest(TestCase):
    """Test ArticleView tracking model"""
    
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
            author=self.user
        )
        
    def test_article_view_creation(self):
        """Test ArticleView creation and tracking"""
        view = ArticleView.objects.create(
            article=self.article,
            user=self.user,
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            referrer='https://example.com'
        )
        
        self.assertEqual(view.article, self.article)
        self.assertEqual(view.user, self.user)
        self.assertEqual(view.ip_address, '127.0.0.1')
        self.assertEqual(view.user_agent, 'Test Agent')
        self.assertEqual(view.referrer, 'https://example.com')
        
    def test_anonymous_view_tracking(self):
        """Test tracking views from anonymous users"""
        view = ArticleView.objects.create(
            article=self.article,
            ip_address='192.168.1.1',
            user_agent='Anonymous Agent'
        )
        
        self.assertEqual(view.article, self.article)
        self.assertIsNone(view.user)
        self.assertEqual(view.ip_address, '192.168.1.1')
        
    def test_view_string_representation(self):
        """Test ArticleView string representation"""
        view = ArticleView.objects.create(
            article=self.article,
            ip_address='127.0.0.1'
        )
        
        expected_str = f"View of '{self.article.title}' at {view.viewed_at}"
        self.assertEqual(str(view), expected_str)


class ModelValidationTest(TestCase):
    """Test model validation and constraints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_article_status_choices(self):
        """Test that article status is constrained to valid choices"""
        # Valid status should work
        article = Article.objects.create(
            title="Test Article",
            content="Content",
            author=self.user,
            status='published'
        )
        self.assertEqual(article.status, 'published')
        
        # Test all valid statuses
        valid_statuses = ['draft', 'review', 'published', 'archived']
        for status in valid_statuses:
            article = Article.objects.create(
                title=f"Test Article {status}",
                content="Content",
                author=self.user,
                status=status
            )
            self.assertEqual(article.status, status)
            
    def test_article_type_choices(self):
        """Test that article type is constrained to valid choices"""
        valid_types = ['news', 'analysis', 'interview', 'preview', 
                      'recap', 'profile', 'ranking', 'technical']
        
        for article_type in valid_types:
            article = Article.objects.create(
                title=f"Test {article_type} Article",
                content="Content",
                author=self.user,
                article_type=article_type
            )
            self.assertEqual(article.article_type, article_type)
            
    def test_tag_color_choices(self):
        """Test that tag colors are constrained to valid choices"""
        valid_colors = ['#007bff', '#28a745', '#dc3545', '#ffc107',
                       '#6f42c1', '#fd7e14', '#20c997', '#6c757d']
        
        for color in valid_colors:
            tag = Tag.objects.create(
                name=f"Test Tag {color}",
                color=color
            )
            self.assertEqual(tag.color, color)