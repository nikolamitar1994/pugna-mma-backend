"""
Comprehensive tests for Django admin interface for content management.

Tests cover:
- Django admin functionality for all models
- Editorial workflow actions in admin
- Permission-based admin access
- Custom admin features and actions
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Group, Permission

from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization
from content.models import Category, Tag, Article, ArticleFighter, ArticleEvent, ArticleOrganization
from content.admin import (
    CategoryAdmin, TagAdmin, ArticleAdmin, ArticleFighterAdmin,
    ArticleEventAdmin, ArticleOrganizationAdmin
)

User = get_user_model()


class AdminSiteAccessTest(TestCase):
    """Test admin site access and authentication"""
    
    def setUp(self):
        """Set up test users"""
        self.client = Client()
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regularpass123'
        )
        
    def test_admin_site_requires_staff_access(self):
        """Test that admin site requires staff privileges"""
        # Regular user should be redirected to login
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        
        # Regular user login should not allow admin access
        self.client.login(username='regular', password='regularpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Still redirected
        
    def test_staff_user_can_access_admin(self):
        """Test that staff users can access admin"""
        self.client.login(username='staff', password='staffpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        
    def test_superuser_can_access_admin(self):
        """Test that superusers can access admin"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)


class CategoryAdminTest(TestCase):
    """Test Category admin functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = CategoryAdmin(Category, self.site)
        
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        # Create test categories
        self.parent_category = Category.objects.create(
            name="News",
            description="News category"
        )
        
        self.child_category = Category.objects.create(
            name="UFC News",
            parent=self.parent_category,
            description="UFC specific news"
        )
        
    def test_category_list_view(self):
        """Test category list view in admin"""
        url = reverse('admin:content_category_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "News")
        self.assertContains(response, "UFC News")
        
    def test_category_add_view(self):
        """Test category add view in admin"""
        url = reverse('admin:content_category_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="parent"')
        
    def test_category_change_view(self):
        """Test category change view in admin"""
        url = reverse('admin:content_category_change', args=[self.parent_category.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.parent_category.name)
        
    def test_category_creation_through_admin(self):
        """Test creating category through admin interface"""
        url = reverse('admin:content_category_add')
        data = {
            'name': 'Test Category',
            'description': 'Test description',
            'order': 0,
            'is_active': True,
            'meta_title': 'Test Meta Title',
            'meta_description': 'Test meta description'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Verify category was created
        category = Category.objects.get(name='Test Category')
        self.assertEqual(category.description, 'Test description')
        self.assertEqual(category.slug, 'test-category')  # Should be auto-generated
        
    def test_category_hierarchical_display(self):
        """Test hierarchical display in admin list"""
        # Check that admin shows hierarchical structure
        response = self.client.get(reverse('admin:content_category_changelist'))
        self.assertContains(response, "News → UFC News")
        
    def test_category_filtering(self):
        """Test category filtering in admin"""
        url = reverse('admin:content_category_changelist')
        
        # Test filtering by is_active
        response = self.client.get(url, {'is_active__exact': '1'})
        self.assertEqual(response.status_code, 200)
        
        # Test filtering by parent
        response = self.client.get(url, {'parent__id__exact': self.parent_category.id})
        self.assertEqual(response.status_code, 200)
        
    def test_category_search(self):
        """Test category search functionality"""
        url = reverse('admin:content_category_changelist')
        response = self.client.get(url, {'q': 'UFC'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UFC News")
        self.assertNotContains(response, "News →")  # Should not show parent


class TagAdminTest(TestCase):
    """Test Tag admin functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = TagAdmin(Tag, self.site)
        
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        # Create test tags
        self.tag1 = Tag.objects.create(
            name="UFC",
            description="Ultimate Fighting Championship",
            color="#dc3545",
            usage_count=10
        )
        
        self.tag2 = Tag.objects.create(
            name="Boxing",
            description="Boxing related content",
            color="#007bff",
            usage_count=5
        )
        
    def test_tag_list_view(self):
        """Test tag list view in admin"""
        url = reverse('admin:content_tag_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UFC")
        self.assertContains(response, "Boxing")
        
    def test_tag_color_display(self):
        """Test that tag colors are displayed in admin"""
        url = reverse('admin:content_tag_changelist')
        response = self.client.get(url)
        
        # Should show color values
        self.assertContains(response, "#dc3545")
        self.assertContains(response, "#007bff")
        
    def test_tag_usage_count_display(self):
        """Test that usage counts are displayed"""
        url = reverse('admin:content_tag_changelist')
        response = self.client.get(url)
        
        # Should show usage counts
        self.assertContains(response, "10")  # UFC usage count
        self.assertContains(response, "5")   # Boxing usage count
        
    def test_tag_creation_through_admin(self):
        """Test creating tag through admin interface"""
        url = reverse('admin:content_tag_add')
        data = {
            'name': 'New Tag',
            'description': 'New tag description',
            'color': '#28a745',
            'usage_count': 0
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify tag was created
        tag = Tag.objects.get(name='New Tag')
        self.assertEqual(tag.color, '#28a745')
        self.assertEqual(tag.slug, 'new-tag')
        
    def test_tag_search(self):
        """Test tag search functionality"""
        url = reverse('admin:content_tag_changelist')
        response = self.client.get(url, {'q': 'UFC'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UFC")
        self.assertNotContains(response, "Boxing")


class ArticleAdminTest(TestCase):
    """Test Article admin functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.site = AdminSite()
        self.admin = ArticleAdmin(Article, self.site)
        
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        # Create test data
        self.category = Category.objects.create(name="Test Category")
        self.tag = Tag.objects.create(name="Test Tag")
        
        self.draft_article = Article.objects.create(
            title="Draft Article",
            content="Draft content",
            category=self.category,
            author=self.author,
            status='draft'
        )
        
        self.published_article = Article.objects.create(
            title="Published Article",
            content="Published content",
            category=self.category,
            author=self.author,
            status='published',
            published_at=timezone.now(),
            is_featured=True
        )
        self.published_article.tags.add(self.tag)
        
    def test_article_list_view(self):
        """Test article list view in admin"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertContains(response, "Published Article")
        
    def test_article_status_display(self):
        """Test that article status is displayed correctly"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        self.assertContains(response, "draft")
        self.assertContains(response, "published")
        
    def test_article_featured_display(self):
        """Test that featured articles are marked"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        # Should show featured indicator
        self.assertContains(response, "✓")  # Checkmark for featured
        
    def test_article_add_view(self):
        """Test article add view in admin"""
        url = reverse('admin:content_article_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="title"')
        self.assertContains(response, 'name="content"')
        self.assertContains(response, 'name="status"')
        
    def test_article_change_view(self):
        """Test article change view in admin"""
        url = reverse('admin:content_article_change', args=[self.draft_article.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.draft_article.title)
        
    def test_article_creation_through_admin(self):
        """Test creating article through admin interface"""
        url = reverse('admin:content_article_add')
        data = {
            'title': 'Admin Test Article',
            'content': 'Admin test content',
            'category': self.category.id,
            'tags': [self.tag.id],
            'author': self.author.id,
            'status': 'draft',
            'article_type': 'news',
            'is_featured': False,
            'is_breaking': False,
            'allow_comments': True,
            'view_count': 0,
            'reading_time': 1
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify article was created
        article = Article.objects.get(title='Admin Test Article')
        self.assertEqual(article.content, 'Admin test content')
        self.assertEqual(article.status, 'draft')
        self.assertEqual(article.slug, 'admin-test-article')
        
    def test_article_filtering_by_status(self):
        """Test filtering articles by status"""
        url = reverse('admin:content_article_changelist')
        
        # Filter by draft status
        response = self.client.get(url, {'status__exact': 'draft'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertNotContains(response, "Published Article")
        
        # Filter by published status
        response = self.client.get(url, {'status__exact': 'published'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Article")
        self.assertNotContains(response, "Draft Article")
        
    def test_article_filtering_by_category(self):
        """Test filtering articles by category"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url, {'category__id__exact': self.category.id})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertContains(response, "Published Article")
        
    def test_article_filtering_by_author(self):
        """Test filtering articles by author"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url, {'author__id__exact': self.author.id})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertContains(response, "Published Article")
        
    def test_article_search(self):
        """Test article search functionality"""
        url = reverse('admin:content_article_changelist')
        
        # Search by title
        response = self.client.get(url, {'q': 'Draft'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft Article")
        self.assertNotContains(response, "Published Article")
        
        # Search by content
        response = self.client.get(url, {'q': 'Published content'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Article")
        
    def test_article_bulk_actions(self):
        """Test bulk actions in article admin"""
        url = reverse('admin:content_article_changelist')
        
        # Test bulk publish action
        data = {
            'action': 'make_published',
            '_selected_action': [str(self.draft_article.id)],
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        # Verify article was published
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.status, 'published')
        self.assertIsNotNone(self.draft_article.published_at)
        
    def test_article_reading_time_display(self):
        """Test that reading time is calculated and displayed"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        # Should show reading time in minutes
        self.assertContains(response, "1 min")  # Default reading time
        
    def test_article_view_count_display(self):
        """Test that view count is displayed"""
        self.published_article.view_count = 50
        self.published_article.save()
        
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        self.assertContains(response, "50")


class ArticleRelationshipAdminTest(TestCase):
    """Test article relationship admin interfaces"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        # Create test objects
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.article = Article.objects.create(
            title="Test Article",
            content="Test content",
            author=self.author,
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
        
    def test_article_fighter_admin(self):
        """Test ArticleFighter admin functionality"""
        # Create relationship
        relationship = ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter,
            relationship_type='about',
            display_order=1
        )
        
        # Test list view
        url = reverse('admin:content_articlefighter_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.fighter.get_full_name())
        
        # Test change view
        url = reverse('admin:content_articlefighter_change', args=[relationship.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="relationship_type"')
        
    def test_article_event_admin(self):
        """Test ArticleEvent admin functionality"""
        # Create relationship
        relationship = ArticleEvent.objects.create(
            article=self.article,
            event=self.event,
            relationship_type='preview'
        )
        
        # Test list view
        url = reverse('admin:content_articleevent_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.event.name)
        
    def test_article_organization_admin(self):
        """Test ArticleOrganization admin functionality"""
        # Create relationship
        relationship = ArticleOrganization.objects.create(
            article=self.article,
            organization=self.organization,
            relationship_type='news'
        )
        
        # Test list view
        url = reverse('admin:content_articleorganization_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.organization.name)


class AdminWorkflowActionsTest(TestCase):
    """Test editorial workflow actions in admin"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        # Create test articles
        self.draft_article = Article.objects.create(
            title="Draft Article",
            content="Draft content",
            author=self.author,
            status='draft'
        )
        
        self.review_article = Article.objects.create(
            title="Review Article",
            content="Review content",
            author=self.author,
            status='review'
        )
        
        self.published_article = Article.objects.create(
            title="Published Article",
            content="Published content",
            author=self.author,
            status='published',
            published_at=timezone.now()
        )
        
    def test_bulk_publish_action(self):
        """Test bulk publish action"""
        url = reverse('admin:content_article_changelist')
        data = {
            'action': 'make_published',
            '_selected_action': [str(self.draft_article.id), str(self.review_article.id)],
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify articles were published
        self.draft_article.refresh_from_db()
        self.review_article.refresh_from_db()
        
        self.assertEqual(self.draft_article.status, 'published')
        self.assertEqual(self.review_article.status, 'published')
        self.assertIsNotNone(self.draft_article.published_at)
        self.assertIsNotNone(self.review_article.published_at)
        
    def test_bulk_draft_action(self):
        """Test bulk make draft action"""
        url = reverse('admin:content_article_changelist')
        data = {
            'action': 'make_draft',
            '_selected_action': [str(self.published_article.id)],
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify article was made draft
        self.published_article.refresh_from_db()
        self.assertEqual(self.published_article.status, 'draft')
        self.assertIsNone(self.published_article.published_at)
        
    def test_bulk_archive_action(self):
        """Test bulk archive action"""
        url = reverse('admin:content_article_changelist')
        data = {
            'action': 'make_archived',
            '_selected_action': [str(self.published_article.id)],
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify article was archived
        self.published_article.refresh_from_db()
        self.assertEqual(self.published_article.status, 'archived')
        
    def test_bulk_feature_action(self):
        """Test bulk feature articles action"""
        url = reverse('admin:content_article_changelist')
        data = {
            'action': 'make_featured',
            '_selected_action': [str(self.published_article.id)],
        }
        
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify article was featured
        self.published_article.refresh_from_db()
        self.assertTrue(self.published_article.is_featured)


class AdminPermissionTest(TestCase):
    """Test permission-based admin access"""
    
    def setUp(self):
        """Set up test data"""
        # Create permission groups
        self.admin_group = Group.objects.create(name='Editorial Admin')
        self.editor_group = Group.objects.create(name='Editorial Editor')
        self.author_group = Group.objects.create(name='Editorial Author')
        
        # Create users with different permissions
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='editorpass123',
            is_staff=True
        )
        self.editor_user.groups.add(self.editor_group)
        
        self.author_user = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123',
            is_staff=True
        )
        self.author_user.groups.add(self.author_group)
        
    def test_admin_can_access_all_models(self):
        """Test that admin users can access all content models"""
        client = Client()
        client.login(username='admin', password='adminpass123')
        
        # Test access to all model admin pages
        models = ['category', 'tag', 'article', 'articlefighter', 'articleevent', 'articleorganization']
        
        for model in models:
            url = reverse(f'admin:content_{model}_changelist')
            response = client.get(url)
            self.assertEqual(response.status_code, 200, f"Admin should access {model} admin")
            
    def test_editor_permissions(self):
        """Test editor user permissions"""
        client = Client()
        client.login(username='editor', password='editorpass123')
        
        # Editors should be able to access articles
        url = reverse('admin:content_article_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_author_permissions(self):
        """Test author user permissions"""
        client = Client()
        client.login(username='author', password='authorpass123')
        
        # Authors should be able to access articles
        url = reverse('admin:content_article_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # But might not be able to access categories (depending on permissions)
        url = reverse('admin:content_category_changelist')
        response = client.get(url)
        # Response could be 200 (if has permission) or 403 (if doesn't)
        self.assertIn(response.status_code, [200, 403])


class AdminInlineTest(TestCase):
    """Test admin inline functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        self.article = Article.objects.create(
            title="Test Article",
            content="Test content",
            author=self.author,
            status='draft'
        )
        
        self.fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter"
        )
        
    def test_article_relationships_inline(self):
        """Test that article relationships can be managed inline"""
        url = reverse('admin:content_article_change', args=[self.article.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should contain inline forms for relationships
        self.assertContains(response, 'fighter_relationships')  # Inline formset
        
    def test_adding_fighter_relationship_inline(self):
        """Test adding fighter relationship through inline"""
        url = reverse('admin:content_article_change', args=[self.article.id])
        
        # Data for adding fighter relationship inline
        data = {
            'title': self.article.title,
            'content': self.article.content,
            'author': self.author.id,
            'status': 'draft',
            'article_type': 'news',
            'view_count': 0,
            'reading_time': 1,
            
            # Inline formset data
            'fighter_relationships-TOTAL_FORMS': '1',
            'fighter_relationships-INITIAL_FORMS': '0',
            'fighter_relationships-MIN_NUM_FORMS': '0',
            'fighter_relationships-MAX_NUM_FORMS': '1000',
            'fighter_relationships-0-fighter': self.fighter.id,
            'fighter_relationships-0-relationship_type': 'about',
            'fighter_relationships-0-display_order': '1',
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful save
        
        # Verify relationship was created
        relationship = ArticleFighter.objects.filter(
            article=self.article,
            fighter=self.fighter
        ).first()
        
        self.assertIsNotNone(relationship)
        self.assertEqual(relationship.relationship_type, 'about')


class AdminCustomizationTest(TestCase):
    """Test custom admin features and customizations"""
    
    def setUp(self):
        """Set up test data"""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.client = Client()
        self.client.login(username='admin', password='adminpass123')
        
    def test_custom_admin_site_title(self):
        """Test custom admin site title and headers"""
        response = self.client.get('/admin/')
        
        # Should contain custom branding
        self.assertContains(response, "MMA Backend Administration")
        
    def test_admin_date_hierarchy(self):
        """Test date hierarchy in article admin"""
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should contain date hierarchy navigation
        self.assertContains(response, 'date_hierarchy')
        
    def test_admin_list_per_page(self):
        """Test pagination in admin lists"""
        # Create multiple articles
        author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        for i in range(30):  # Create more than default page size
            Article.objects.create(
                title=f"Article {i}",
                content=f"Content {i}",
                author=author,
                status='draft'
            )
        
        url = reverse('admin:content_article_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should contain pagination
        self.assertContains(response, 'paginator')
        
    def test_admin_readonly_fields(self):
        """Test readonly fields in admin"""
        author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='authorpass123'
        )
        
        article = Article.objects.create(
            title="Test Article",
            content="Test content",
            author=author,
            status='published',
            published_at=timezone.now(),
            view_count=50
        )
        
        url = reverse('admin:content_article_change', args=[article.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # View count should be readonly
        self.assertContains(response, str(article.view_count))
        
    def test_admin_fieldsets(self):
        """Test admin fieldsets organization"""
        url = reverse('admin:content_article_add')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should contain organized fieldsets
        self.assertContains(response, 'Content')  # Fieldset name
        self.assertContains(response, 'SEO')      # SEO fieldset
        self.assertContains(response, 'Publishing')  # Publishing fieldset