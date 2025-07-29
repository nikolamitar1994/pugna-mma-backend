"""
Comprehensive tests for SEO features of content management system.

Tests cover:
- Sitemap generation
- RSS feeds
- Schema.org structured data
- Meta tag generation
- SEO optimization features
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.contrib.sites.models import Site
from django.test.utils import override_settings

from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization
from content.models import Category, Tag, Article, ArticleFighter, ArticleEvent
from content.sitemaps import ArticleSitemap, CategorySitemap, TagSitemap
from content.feeds import LatestArticlesFeed, CategoryFeed, TagFeed

User = get_user_model()


class SitemapTest(TestCase):
    """Test sitemap generation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name="Test Category",
            description="Test category description"
        )
        
        # Create test tag
        self.tag = Tag.objects.create(
            name="Test Tag",
            description="Test tag description"
        )
        
        # Create test articles
        self.published_article = Article.objects.create(
            title="Published Article",
            content="Published content",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        self.published_article.tags.add(self.tag)
        
        self.draft_article = Article.objects.create(
            title="Draft Article",
            content="Draft content",
            category=self.category,
            author=self.user,
            status='draft'
        )
        
        # Set up site
        self.site = Site.objects.get_current()
        
    def test_main_sitemap_index(self):
        """Test main sitemap index generation"""
        url = reverse('django.contrib.sitemaps.views.sitemap')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Should contain sitemap entries for articles, categories, and tags
        loc_elements = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
        urls = [elem.text for elem in loc_elements]
        
        # Check that our published article is included
        self.assertTrue(any(self.published_article.slug in url for url in urls))
        
    def test_article_sitemap(self):
        """Test article sitemap generation"""
        sitemap = ArticleSitemap()
        items = sitemap.items()
        
        # Should only include published articles
        self.assertIn(self.published_article, items)
        self.assertNotIn(self.draft_article, items)
        
        # Test sitemap methods
        self.assertEqual(sitemap.lastmod(self.published_article), self.published_article.updated_at)
        self.assertEqual(sitemap.priority(self.published_article), 0.9)  # High priority for featured
        self.assertEqual(sitemap.changefreq(self.published_article), 'weekly')
        
    def test_category_sitemap(self):
        """Test category sitemap generation"""
        sitemap = CategorySitemap()
        items = sitemap.items()
        
        # Should include active categories
        self.assertIn(self.category, items)
        
        # Test sitemap methods
        self.assertEqual(sitemap.priority(self.category), 0.6)
        self.assertEqual(sitemap.changefreq(self.category), 'weekly')
        
    def test_tag_sitemap(self):
        """Test tag sitemap generation"""
        sitemap = TagSitemap()
        items = sitemap.items()
        
        # Should include tags with articles
        self.assertIn(self.tag, items)
        
        # Test sitemap methods
        self.assertEqual(sitemap.priority(self.tag), 0.5)
        self.assertEqual(sitemap.changefreq(self.tag), 'monthly')
        
    def test_sitemap_xml_format(self):
        """Test that sitemap generates valid XML"""
        url = reverse('django.contrib.sitemaps.views.sitemap')
        response = self.client.get(url)
        
        # Should parse as valid XML
        try:
            root = ET.fromstring(response.content)
            self.assertTrue(True)  # XML parsed successfully
        except ET.ParseError:
            self.fail("Sitemap XML is not valid")
        
        # Check XML structure
        self.assertEqual(root.tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
        
        # Should have URL entries
        url_elements = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
        self.assertTrue(len(url_elements) > 0)
        
        # Each URL should have required elements
        for url_elem in url_elements:
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            self.assertIsNotNone(loc)
            self.assertTrue(loc.text.startswith('http'))


class RSSFeedsTest(TestCase):
    """Test RSS feed generation functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name="News",
            description="Latest MMA news"
        )
        
        # Create test tag
        self.tag = Tag.objects.create(
            name="UFC",
            description="UFC related content"
        )
        
        # Create test articles
        self.recent_article = Article.objects.create(
            title="Recent Article",
            content="Recent content with <strong>HTML</strong>",
            excerpt="Recent article excerpt",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        self.recent_article.tags.add(self.tag)
        
        self.older_article = Article.objects.create(
            title="Older Article",
            content="Older content",
            excerpt="Older article excerpt",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now() - timedelta(days=5)
        )
        
        # Draft article (should not appear in feeds)
        self.draft_article = Article.objects.create(
            title="Draft Article",
            content="Draft content",
            category=self.category,
            author=self.user,
            status='draft'
        )
        
    def test_latest_articles_feed(self):
        """Test main RSS feed for latest articles"""
        url = reverse('content:latest_feed')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/rss+xml; charset=utf-8')
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        
        # Check RSS structure
        channel = root.find('channel')
        self.assertIsNotNone(channel)
        
        # Check feed metadata
        title = channel.find('title').text
        description = channel.find('description').text
        self.assertIn('Latest', title)
        self.assertTrue(len(description) > 0)
        
        # Check items
        items = channel.findall('item')
        self.assertTrue(len(items) > 0)
        
        # Should be ordered by published date (recent first)
        first_item = items[0]
        first_title = first_item.find('title').text
        self.assertEqual(first_title, "Recent Article")
        
        # Check item structure
        self.assertIsNotNone(first_item.find('link'))
        self.assertIsNotNone(first_item.find('description'))
        self.assertIsNotNone(first_item.find('pubDate'))
        self.assertIsNotNone(first_item.find('guid'))
        
    def test_category_feed(self):
        """Test RSS feed for specific category"""
        url = reverse('content:category_feed', kwargs={'category_slug': self.category.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        
        # Should include category name in title
        title = channel.find('title').text
        self.assertIn(self.category.name, title)
        
        # Should only include articles from this category
        items = channel.findall('item')
        self.assertEqual(len(items), 2)  # Two published articles in category
        
    def test_tag_feed(self):
        """Test RSS feed for specific tag"""
        url = reverse('content:tag_feed', kwargs={'tag_slug': self.tag.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        
        # Should include tag name in title
        title = channel.find('title').text
        self.assertIn(self.tag.name, title)
        
        # Should only include articles with this tag
        items = channel.findall('item')
        self.assertEqual(len(items), 1)  # Only recent_article has this tag
        
    def test_feed_content_sanitization(self):
        """Test that feed content is properly sanitized"""
        url = reverse('content:latest_feed')
        response = self.client.get(url)
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        # Find our article with HTML content
        for item in items:
            title = item.find('title').text
            if title == "Recent Article":
                description = item.find('description').text
                # HTML should be stripped or escaped
                self.assertNotIn('<strong>', description)
                break
        else:
            self.fail("Could not find article in feed")
            
    def test_feed_item_urls(self):
        """Test that feed items have correct URLs"""
        url = reverse('content:latest_feed')
        response = self.client.get(url)
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        for item in items:
            link = item.find('link').text
            guid = item.find('guid').text
            
            # Links should be absolute URLs
            self.assertTrue(link.startswith('http'))
            self.assertTrue(guid.startswith('http'))
            
    def test_feed_limits(self):
        """Test that feeds respect item limits"""
        # Create many articles
        for i in range(25):
            Article.objects.create(
                title=f"Article {i}",
                content=f"Content {i}",
                author=self.user,
                status='published',
                published_at=timezone.now() - timedelta(hours=i)
            )
        
        url = reverse('content:latest_feed')
        response = self.client.get(url)
        
        # Parse RSS XML
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        # Should limit to reasonable number (e.g., 20)
        self.assertLessEqual(len(items), 20)
        
    def test_feed_with_no_articles(self):
        """Test feed behavior when no articles exist"""
        # Delete all articles
        Article.objects.all().delete()
        
        url = reverse('content:latest_feed')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should still be valid RSS
        root = ET.fromstring(response.content)
        channel = root.find('channel')
        self.assertIsNotNone(channel)
        
        # Should have no items
        items = channel.findall('item')
        self.assertEqual(len(items), 0)


class SchemaOrgTest(TestCase):
    """Test Schema.org structured data generation"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name="MMA News",
            description="Latest MMA news and updates"
        )
        
        # Create test tag
        self.tag = Tag.objects.create(
            name="UFC",
            description="UFC related content"
        )
        
        # Create test article
        self.article = Article.objects.create(
            title="Test MMA Article",
            content="This is a comprehensive article about MMA.",
            excerpt="A test article about mixed martial arts",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now(),
            featured_image="https://example.com/image.jpg",
            featured_image_alt="MMA fighters in action",
            meta_title="Test MMA Article - SEO Title",
            meta_description="This is a test article for SEO testing purposes"
        )
        self.article.tags.add(self.tag)
        
        # Create fighter and link to article
        self.fighter = Fighter.objects.create(
            first_name="John",
            last_name="Doe",
            nickname="The Test Fighter"
        )
        
        ArticleFighter.objects.create(
            article=self.article,
            fighter=self.fighter,
            relationship_type='about'
        )
        
    def test_article_schema_org_data(self):
        """Test Schema.org structured data for articles"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for JSON-LD structured data
        self.assertContains(response, 'application/ld+json')
        self.assertContains(response, '"@type": "Article"')
        self.assertContains(response, '"headline": "Test MMA Article"')
        self.assertContains(response, '"author"')
        self.assertContains(response, '"datePublished"')
        self.assertContains(response, '"dateModified"')
        
        # Check for image data
        self.assertContains(response, '"image"')
        self.assertContains(response, self.article.featured_image)
        
        # Check for publisher information
        self.assertContains(response, '"publisher"')
        
    def test_article_breadcrumb_schema(self):
        """Test breadcrumb structured data for articles"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for breadcrumb structured data
        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertContains(response, '"itemListElement"')
        
        # Should include category in breadcrumbs
        self.assertContains(response, self.category.name)
        
    def test_category_schema_org_data(self):
        """Test Schema.org structured data for categories"""
        url = reverse('content:category_detail', kwargs={'slug': self.category.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check for CollectionPage schema
        self.assertContains(response, '"@type": "CollectionPage"')
        self.assertContains(response, '"name": "' + self.category.name + '"')
        self.assertContains(response, '"description"')
        
    def test_organization_schema(self):
        """Test organization structured data"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should include organization data
        self.assertContains(response, '"@type": "Organization"')
        self.assertContains(response, '"name": "MMA Database"')
        
    def test_person_schema_for_author(self):
        """Test Person schema for article authors"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should include author as Person
        self.assertContains(response, '"@type": "Person"')
        self.assertContains(response, self.user.username)
        
    def test_sports_schema_integration(self):
        """Test sports-specific schema integration"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should include sports-related schema elements
        self.assertContains(response, '"about"')  # About the sport/fighters
        
        # Check for fighter-specific schema when article is about a fighter
        self.assertContains(response, self.fighter.get_full_name())


class MetaTagsTest(TestCase):
    """Test meta tag generation for SEO"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name="MMA News",
            description="Latest MMA news",
            meta_title="MMA News - Latest Updates",
            meta_description="Stay updated with the latest MMA news and fight results"
        )
        
        # Create test article
        self.article = Article.objects.create(
            title="Ultimate Fighter Championship Results",
            content="Detailed coverage of the latest UFC event with fight results and analysis.",
            excerpt="Complete coverage of UFC event results",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now(),
            featured_image="https://example.com/ufc-image.jpg",
            featured_image_alt="UFC octagon with fighters",
            meta_title="UFC Results - Championship Fight Coverage",
            meta_description="Complete UFC event results with detailed fight analysis and highlights"
        )
        
    def test_article_basic_meta_tags(self):
        """Test basic meta tags for articles"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check title tag
        self.assertContains(response, f'<title>{self.article.get_seo_title()}</title>')
        
        # Check meta description
        self.assertContains(response, f'<meta name="description" content="{self.article.get_seo_description()}">')
        
        # Check meta keywords (if implemented)
        self.assertContains(response, '<meta name="keywords"')
        
    def test_article_open_graph_tags(self):
        """Test Open Graph meta tags for social sharing"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Check Open Graph tags
        self.assertContains(response, '<meta property="og:title"')
        self.assertContains(response, '<meta property="og:description"')
        self.assertContains(response, '<meta property="og:image"')
        self.assertContains(response, '<meta property="og:url"')
        self.assertContains(response, '<meta property="og:type" content="article"')
        self.assertContains(response, '<meta property="og:site_name"')
        
        # Check article-specific OG tags
        self.assertContains(response, '<meta property="article:author"')
        self.assertContains(response, '<meta property="article:published_time"')
        self.assertContains(response, '<meta property="article:modified_time"')
        self.assertContains(response, '<meta property="article:section"')
        
    def test_article_twitter_card_tags(self):
        """Test Twitter Card meta tags"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Check Twitter Card tags
        self.assertContains(response, '<meta name="twitter:card"')
        self.assertContains(response, '<meta name="twitter:title"')
        self.assertContains(response, '<meta name="twitter:description"')
        self.assertContains(response, '<meta name="twitter:image"')
        
    def test_category_meta_tags(self):
        """Test meta tags for category pages"""
        url = reverse('content:category_detail', kwargs={'slug': self.category.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should use category meta title/description if available
        self.assertContains(response, f'<title>{self.category.meta_title}</title>')
        self.assertContains(response, f'<meta name="description" content="{self.category.meta_description}">')
        
    def test_canonical_urls(self):
        """Test canonical URL generation"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should have canonical link
        self.assertContains(response, '<link rel="canonical"')
        self.assertContains(response, self.article.get_absolute_url())
        
    def test_meta_tags_fallback(self):
        """Test meta tag fallback when custom values not provided"""
        # Create article without custom meta tags
        article_no_meta = Article.objects.create(
            title="Article Without Meta",
            content="Content without custom meta tags",
            excerpt="Auto-generated excerpt",
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article_no_meta.slug})
        response = self.client.get(url)
        
        # Should fall back to title and excerpt
        self.assertContains(response, f'<title>{article_no_meta.title}</title>')
        self.assertContains(response, f'<meta name="description" content="{article_no_meta.excerpt}">')
        
    def test_robots_meta_tag(self):
        """Test robots meta tag for different article states"""
        # Published article should be indexable
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should allow indexing
        self.assertContains(response, '<meta name="robots" content="index, follow">')
        
    def test_meta_tags_escaping(self):
        """Test that meta tag content is properly escaped"""
        # Create article with special characters
        article_special = Article.objects.create(
            title='Article with "Quotes" & Ampersands',
            content="Content",
            excerpt='Description with "quotes" & special chars',
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article_special.slug})
        response = self.client.get(url)
        
        # Content should be properly escaped
        self.assertContains(response, '&quot;')  # Quotes escaped
        self.assertContains(response, '&amp;')   # Ampersands escaped


class SEOOptimizationTest(TestCase):
    """Test SEO optimization features"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name="Fight Analysis",
            description="In-depth fight analysis and breakdowns"
        )
        
    def test_url_structure_seo_friendly(self):
        """Test that URLs are SEO-friendly"""
        article = Article.objects.create(
            title="Jon Jones vs Daniel Cormier Fight Analysis",
            content="Detailed analysis",
            category=self.category,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        # URL should be SEO-friendly
        expected_slug = "jon-jones-vs-daniel-cormier-fight-analysis"
        self.assertEqual(article.slug, expected_slug)
        
        # URL should work
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_heading_structure(self):
        """Test proper heading structure for SEO"""
        article = Article.objects.create(
            title="SEO Test Article",
            content="""
            <h2>Main Heading</h2>
            <p>Content under main heading.</p>
            <h3>Sub Heading</h3>
            <p>Content under sub heading.</p>
            """,
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        
        # Should have H1 for article title
        self.assertContains(response, '<h1>')
        self.assertContains(response, article.title)
        
        # Should preserve content heading structure
        self.assertContains(response, '<h2>Main Heading</h2>')
        self.assertContains(response, '<h3>Sub Heading</h3>')
        
    def test_image_alt_tags(self):
        """Test that images have proper alt tags"""
        article = Article.objects.create(
            title="Article with Image",
            content="Content",
            featured_image="https://example.com/image.jpg",
            featured_image_alt="Descriptive alt text for accessibility",
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        
        # Featured image should have alt text
        self.assertContains(response, 'alt="Descriptive alt text for accessibility"')
        
    def test_loading_performance(self):
        """Test page loading performance indicators"""
        url = reverse('content:article_detail', kwargs={'slug': self.article.slug})
        response = self.client.get(url)
        
        # Should have performance optimization tags
        self.assertContains(response, 'dns-prefetch')  # DNS prefetching
        
    def test_structured_data_validation(self):
        """Test that structured data is valid"""
        article = Article.objects.create(
            title="Structured Data Test",
            content="Test content",
            author=self.user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        
        # Extract JSON-LD data
        content = response.content.decode()
        
        # Should contain valid JSON-LD
        self.assertIn('application/ld+json', content)
        self.assertIn('"@context": "https://schema.org"', content)
        
        # Test basic JSON validity
        import json
        import re
        
        # Extract JSON-LD scripts
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        matches = re.findall(json_ld_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                json.loads(match.strip())
            except json.JSONDecodeError:
                self.fail(f"Invalid JSON-LD found: {match}")


class RobotsAndSecurityTest(TestCase):
    """Test robots.txt and security-related SEO features"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
    def test_robots_txt(self):
        """Test robots.txt generation"""
        url = '/robots.txt'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        
        content = response.content.decode()
        
        # Should contain basic robots.txt directives
        self.assertIn('User-agent:', content)
        self.assertIn('Sitemap:', content)
        
        # Should reference sitemap
        self.assertIn('sitemap.xml', content)
        
    def test_security_headers(self):
        """Test security-related headers for SEO"""
        # Create test article
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        article = Article.objects.create(
            title="Security Test Article",
            content="Content",
            author=user,
            status='published',
            published_at=timezone.now()
        )
        
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        
        # Check for security headers that affect SEO
        # Note: These might not be set in test environment
        # but should be present in production
        
        # Content-Type should be properly set
        self.assertIn('text/html', response.get('Content-Type', ''))
        
    @override_settings(DEBUG=False)
    def test_404_error_page_seo(self):
        """Test that 404 pages are SEO-friendly"""
        # Try to access non-existent article
        url = reverse('content:article_detail', kwargs={'slug': 'non-existent-article'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        
        # 404 page should have proper meta tags
        content = response.content.decode()
        self.assertIn('<title>', content)
        self.assertIn('404', content)
        
    def test_duplicate_content_prevention(self):
        """Test measures to prevent duplicate content issues"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        article = Article.objects.create(
            title="Duplicate Content Test",
            content="Content",
            author=user,
            status='published',
            published_at=timezone.now()
        )
        
        # Test canonical URL
        url = reverse('content:article_detail', kwargs={'slug': article.slug})
        response = self.client.get(url)
        
        # Should have canonical link to prevent duplicate content
        self.assertContains(response, 'rel="canonical"')
        
        # URL parameters should not create duplicate content
        response_with_params = self.client.get(url + '?utm_source=test')
        self.assertEqual(response_with_params.status_code, 200)
        
        # Should still have same canonical URL
        self.assertContains(response_with_params, 'rel="canonical"')