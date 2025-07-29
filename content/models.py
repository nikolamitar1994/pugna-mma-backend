"""
Content Management System Models for MMA Backend

This module defines the core models for the news and content management system,
including articles, categories, tags, and their relationships to fighters,
events, and organizations.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()


class Category(models.Model):
    """
    Hierarchical category system for organizing articles.
    Supports nested categories (e.g., News > UFC News > Fight Results).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Brief description of this category")
    
    # Hierarchical structure
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', help_text="Parent category for hierarchical organization"
    )
    
    # Display and management
    order = models.PositiveIntegerField(default=0, help_text="Order for display (0 = first)")
    is_active = models.BooleanField(default=True)
    
    # SEO fields
    meta_title = models.CharField(max_length=60, blank=True, help_text="SEO title (leave blank to use name)")
    meta_description = models.CharField(max_length=160, blank=True, help_text="SEO meta description")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'content_categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent', 'order']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('content:category_detail', kwargs={'slug': self.slug})
    
    def get_full_path(self):
        """Get the full hierarchical path as a list"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return path
    
    def get_article_count(self):
        """Get count of published articles in this category and its children"""
        from django.db.models import Q
        descendant_ids = [self.id]
        
        # Get all descendant category IDs
        def get_descendants(category):
            children = category.children.all()
            for child in children:
                descendant_ids.append(child.id)
                get_descendants(child)
        
        get_descendants(self)
        
        return Article.objects.filter(
            category_id__in=descendant_ids,
            status='published'
        ).count()


class Tag(models.Model):
    """
    Simple tagging system for articles with color coding for organization.
    """
    
    COLOR_CHOICES = [
        ('#007bff', 'Blue'),
        ('#28a745', 'Green'), 
        ('#dc3545', 'Red'),
        ('#ffc107', 'Yellow'),
        ('#6f42c1', 'Purple'),
        ('#fd7e14', 'Orange'),
        ('#20c997', 'Teal'),
        ('#6c757d', 'Gray'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Optional description of this tag")
    color = models.CharField(
        max_length=7, choices=COLOR_CHOICES, default='#007bff',
        help_text="Color for UI display"
    )
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0, help_text="Number of articles using this tag")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'content_tags'
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('content:tag_detail', kwargs={'slug': self.slug})


class Article(models.Model):
    """
    Main content model for news articles, fighter profiles, event coverage, etc.
    Supports rich editorial workflow and SEO optimization.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    ARTICLE_TYPE_CHOICES = [
        ('news', 'News Article'),
        ('analysis', 'Analysis/Opinion'),
        ('interview', 'Interview'),
        ('preview', 'Event Preview'),
        ('recap', 'Event Recap'),
        ('profile', 'Fighter Profile'),
        ('ranking', 'Ranking Analysis'),
        ('technical', 'Technical Analysis'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Content fields
    title = models.CharField(max_length=200, help_text="Article headline")
    slug = models.SlugField(max_length=220, unique=True, blank=True, help_text="URL slug (auto-generated)")
    excerpt = models.TextField(
        max_length=500, blank=True,
        help_text="Brief summary for listings and SEO (auto-generated if blank)"
    )
    content = models.TextField(help_text="Main article content (supports HTML)")
    
    # Content organization
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True,
        related_name='articles', help_text="Primary category"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles')
    article_type = models.CharField(
        max_length=20, choices=ARTICLE_TYPE_CHOICES, default='news',
        help_text="Type of content for better organization"
    )
    
    # Publishing workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='articles', help_text="Article author"
    )
    editor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='edited_articles', help_text="Reviewing editor"
    )
    
    # Media (temporarily changed to URLField until Pillow is installed)
    featured_image = models.URLField(
        blank=True,
        help_text="Main article image URL (recommended: 1200x630px)"
    )
    featured_image_alt = models.CharField(
        max_length=200, blank=True,
        help_text="Alt text for featured image (accessibility)"
    )
    featured_image_caption = models.CharField(
        max_length=300, blank=True,
        help_text="Image caption or credit"
    )
    
    # SEO fields
    meta_title = models.CharField(
        max_length=60, blank=True,
        help_text="SEO title (leave blank to use article title)"
    )
    meta_description = models.CharField(
        max_length=160, blank=True,
        help_text="SEO meta description (leave blank to use excerpt)"
    )
    
    # Display options
    is_featured = models.BooleanField(
        default=False, help_text="Feature on homepage and category pages"
    )
    is_breaking = models.BooleanField(
        default=False, help_text="Mark as breaking news"
    )
    allow_comments = models.BooleanField(default=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(
        default=0, help_text="Number of times this article has been viewed"
    )
    reading_time = models.PositiveIntegerField(
        default=0, help_text="Estimated reading time in minutes (auto-calculated)"
    )
    
    # Timestamps
    published_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this article was/will be published"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'content_articles'
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', '-published_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['author', 'status']),
            models.Index(fields=['is_featured', 'status']),
            models.Index(fields=['article_type', 'status']),
            models.Index(fields=['-view_count']),
        ]
        unique_together = [
            ['slug'],  # Enforce unique slugs across all articles
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Article.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Auto-generate excerpt if not provided
        if not self.excerpt and self.content:
            # Remove HTML tags and truncate
            import re
            plain_text = re.sub(r'<[^>]+>', '', self.content)
            self.excerpt = plain_text[:300] + '...' if len(plain_text) > 300 else plain_text
        
        # Calculate reading time (average 200 words per minute)
        if self.content:
            import re
            word_count = len(re.findall(r'\w+', re.sub(r'<[^>]+>', '', self.content)))
            self.reading_time = max(1, word_count // 200)
        
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        elif self.status != 'published':
            self.published_at = None
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('content:article_detail', kwargs={'slug': self.slug})
    
    def get_seo_title(self):
        """Get SEO title, falling back to article title"""
        return self.meta_title or self.title
    
    def get_seo_description(self):
        """Get SEO description, falling back to excerpt"""
        return self.meta_description or self.excerpt
    
    def get_featured_image_url(self):
        """Get featured image URL or default placeholder"""
        if self.featured_image:
            return self.featured_image.url
        return '/static/images/default-article.jpg'  # Default image path
    
    def increment_view_count(self):
        """Increment view count (should be called when article is viewed)"""
        Article.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)
    
    def get_related_articles(self, limit=5):
        """Get related articles based on category and tags"""
        related = Article.objects.filter(
            status='published'
        ).exclude(
            pk=self.pk
        )
        
        # Prioritize same category
        if self.category:
            related = related.filter(category=self.category)
        
        # If we have tags, also include articles with shared tags
        if self.tags.exists():
            tag_related = Article.objects.filter(
                tags__in=self.tags.all(),
                status='published'
            ).exclude(pk=self.pk).distinct()
            
            # Combine and remove duplicates
            related = (related | tag_related).distinct()
        
        return related.order_by('-published_at')[:limit]
    
    @property
    def is_published(self):
        """Check if article is published"""
        return self.status == 'published' and self.published_at and self.published_at <= timezone.now()


# Relationship models for linking articles to fighters, events, and organizations

class ArticleFighter(models.Model):
    """
    Many-to-many relationship between articles and fighters with additional context.
    """
    
    RELATIONSHIP_CHOICES = [
        ('about', 'Article About Fighter'),
        ('mentions', 'Fighter Mentioned'),
        ('features', 'Fighter Featured'),
        ('interview', 'Fighter Interview'),
        ('analysis', 'Fighter Analysis'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='fighter_relationships')
    fighter = models.ForeignKey('fighters.Fighter', on_delete=models.CASCADE, related_name='article_relationships')
    
    relationship_type = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES, default='mentions',
        help_text="How this fighter relates to the article"
    )
    
    # Order for display when multiple fighters are involved
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'content_article_fighters'
        verbose_name = 'Article Fighter Relationship'
        verbose_name_plural = 'Article Fighter Relationships'
        unique_together = [['article', 'fighter']]
        ordering = ['display_order', 'created_at']
        indexes = [
            models.Index(fields=['article', 'relationship_type']),
            models.Index(fields=['fighter', 'relationship_type']),
        ]
    
    def __str__(self):
        return f"{self.article.title} → {self.fighter.get_full_name()} ({self.relationship_type})"


class ArticleEvent(models.Model):
    """
    Many-to-many relationship between articles and events with additional context.
    """
    
    RELATIONSHIP_CHOICES = [
        ('preview', 'Event Preview'),
        ('recap', 'Event Recap'),
        ('coverage', 'Live Coverage'),
        ('analysis', 'Event Analysis'),
        ('mentions', 'Event Mentioned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='event_relationships')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='article_relationships')
    
    relationship_type = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES, default='mentions',
        help_text="How this event relates to the article"
    )
    
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'content_article_events'
        verbose_name = 'Article Event Relationship'
        verbose_name_plural = 'Article Event Relationships'
        unique_together = [['article', 'event']]
        ordering = ['display_order', 'created_at']
        indexes = [
            models.Index(fields=['article', 'relationship_type']),
            models.Index(fields=['event', 'relationship_type']),
        ]
    
    def __str__(self):
        return f"{self.article.title} → {self.event.name} ({self.relationship_type})"


class ArticleOrganization(models.Model):
    """
    Many-to-many relationship between articles and organizations with additional context.
    """
    
    RELATIONSHIP_CHOICES = [
        ('news', 'Organization News'),
        ('announcement', 'Official Announcement'),
        ('analysis', 'Organization Analysis'),
        ('mentions', 'Organization Mentioned'),
        ('policy', 'Policy/Rules Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='organization_relationships')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='article_relationships')
    
    relationship_type = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES, default='mentions',
        help_text="How this organization relates to the article"
    )
    
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'content_article_organizations'
        verbose_name = 'Article Organization Relationship'
        verbose_name_plural = 'Article Organization Relationships'
        unique_together = [['article', 'organization']]
        ordering = ['display_order', 'created_at']
        indexes = [
            models.Index(fields=['article', 'relationship_type']),
            models.Index(fields=['organization', 'relationship_type']),
        ]
    
    def __str__(self):
        return f"{self.article.title} → {self.organization.name} ({self.relationship_type})"


# Content analytics and tracking models

class ArticleView(models.Model):
    """
    Track individual article views for analytics (optional detailed tracking).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='views')
    
    # Optional user tracking (for registered users)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Request tracking
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True, max_length=500)
    
    # Timestamps
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'content_article_views'
        verbose_name = 'Article View'
        verbose_name_plural = 'Article Views'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['article', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['-viewed_at']),
        ]
    
    def __str__(self):
        return f"View of '{self.article.title}' at {self.viewed_at}"