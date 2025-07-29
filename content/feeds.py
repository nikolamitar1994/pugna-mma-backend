"""
RSS/Atom feeds for content management system.

Provides RSS feeds for latest articles, categories, and tags
with proper metadata and SEO optimization.
"""

from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from django.utils.html import strip_tags
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from .models import Article, Category, Tag


class LatestArticlesFeed(Feed):
    """
    RSS feed for the latest published articles across all categories.
    """
    
    title = "MMA Database - Latest Articles"
    link = "/content/"
    description = "Latest news, analysis, and articles from MMA Database"
    feed_type = Atom1Feed
    
    def items(self):
        """Return the latest 20 published articles."""
        return Article.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')[:20]
    
    def item_title(self, item):
        """Return article title."""
        return item.title
    
    def item_description(self, item):
        """Return article excerpt or truncated content."""
        if item.excerpt:
            return item.excerpt
        
        # Fallback to truncated content
        content = strip_tags(item.content)
        return content[:300] + '...' if len(content) > 300 else content
    
    def item_link(self, item):
        """Return article URL."""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Return publication date."""
        return item.published_at
    
    def item_updateddate(self, item):
        """Return last update date."""
        return item.updated_at
    
    def item_author_name(self, item):
        """Return author name."""
        return item.author.get_full_name() if item.author else "MMA Database"
    
    def item_categories(self, item):
        """Return categories and tags."""
        categories = []
        
        # Add primary category
        if item.category:
            categories.append(item.category.name)
        
        # Add tags
        categories.extend([tag.name for tag in item.tags.all()])
        
        return categories
    
    def item_extra_kwargs(self, item):
        """Add extra metadata for feed items."""
        extra = {}
        
        # Featured image
        if item.featured_image:
            extra['enclosure'] = {
                'url': item.get_featured_image_url(),
                'type': 'image/jpeg',  # Assume JPEG for now
                'length': '0'  # RSS doesn't require accurate length
            }
        
        # Article type
        extra['type'] = item.get_article_type_display()
        
        return extra


class CategoryFeed(Feed):
    """
    RSS feed for articles in a specific category.
    """
    
    feed_type = Atom1Feed
    
    def get_object(self, request, slug):
        """Get the category object."""
        return get_object_or_404(Category, slug=slug, is_active=True)
    
    def title(self, obj):
        """Return feed title."""
        return f"MMA Database - {obj.name}"
    
    def link(self, obj):
        """Return category URL."""
        return obj.get_absolute_url()
    
    def description(self, obj):
        """Return feed description."""
        if obj.description:
            return obj.description
        return f"Latest articles in {obj.name} category"
    
    def items(self, obj):
        """Return latest articles in this category."""
        return Article.objects.filter(
            category=obj,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')[:15]
    
    def item_title(self, item):
        """Return article title."""
        return item.title
    
    def item_description(self, item):
        """Return article excerpt or truncated content."""
        if item.excerpt:
            return item.excerpt
        
        content = strip_tags(item.content)
        return content[:300] + '...' if len(content) > 300 else content
    
    def item_link(self, item):
        """Return article URL."""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Return publication date."""
        return item.published_at
    
    def item_updateddate(self, item):
        """Return last update date."""
        return item.updated_at
    
    def item_author_name(self, item):
        """Return author name."""
        return item.author.get_full_name() if item.author else "MMA Database"
    
    def item_categories(self, item):
        """Return tags for this article."""
        return [tag.name for tag in item.tags.all()]


class TagFeed(Feed):
    """
    RSS feed for articles with a specific tag.
    """
    
    feed_type = Atom1Feed
    
    def get_object(self, request, slug):
        """Get the tag object."""
        return get_object_or_404(Tag, slug=slug)
    
    def title(self, obj):
        """Return feed title."""
        return f"MMA Database - Articles tagged '{obj.name}'"
    
    def link(self, obj):
        """Return tag URL."""
        return obj.get_absolute_url()
    
    def description(self, obj):
        """Return feed description."""
        if obj.description:
            return obj.description
        return f"Latest articles tagged with '{obj.name}'"
    
    def items(self, obj):
        """Return latest articles with this tag."""
        return Article.objects.filter(
            tags=obj,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')[:15]
    
    def item_title(self, item):
        """Return article title."""
        return item.title
    
    def item_description(self, item):
        """Return article excerpt or truncated content."""
        if item.excerpt:
            return item.excerpt
        
        content = strip_tags(item.content)
        return content[:300] + '...' if len(content) > 300 else content
    
    def item_link(self, item):
        """Return article URL."""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Return publication date."""
        return item.published_at
    
    def item_updateddate(self, item):
        """Return last update date."""
        return item.updated_at
    
    def item_author_name(self, item):
        """Return author name."""
        return item.author.get_full_name() if item.author else "MMA Database"
    
    def item_categories(self, item):
        """Return category and other tags."""
        categories = []
        
        # Add primary category
        if item.category:
            categories.append(item.category.name)
        
        # Add other tags (excluding current tag to avoid duplication)
        other_tags = item.tags.exclude(slug=self.get_object(None, None).slug)
        categories.extend([tag.name for tag in other_tags])
        
        return categories


class FighterArticlesFeed(Feed):
    """
    RSS feed for articles related to a specific fighter.
    """
    
    feed_type = Atom1Feed
    
    def get_object(self, request, fighter_id):
        """Get the fighter object."""
        # This would require importing Fighter model
        from fighters.models import Fighter
        return get_object_or_404(Fighter, id=fighter_id)
    
    def title(self, obj):
        """Return feed title."""
        return f"MMA Database - Articles about {obj.get_full_name()}"
    
    def link(self, obj):
        """Return fighter URL."""
        return obj.get_absolute_url()
    
    def description(self, obj):
        """Return feed description."""
        return f"Latest news and articles about {obj.get_full_name()}"
    
    def items(self, obj):
        """Return latest articles about this fighter."""
        return Article.objects.filter(
            fighter_relationships__fighter=obj,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')[:10]
    
    def item_title(self, item):
        """Return article title."""
        return item.title
    
    def item_description(self, item):
        """Return article excerpt."""
        return item.excerpt or strip_tags(item.content)[:300] + '...'
    
    def item_link(self, item):
        """Return article URL."""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Return publication date."""
        return item.published_at
    
    def item_author_name(self, item):
        """Return author name."""
        return item.author.get_full_name() if item.author else "MMA Database"


class EventArticlesFeed(Feed):
    """
    RSS feed for articles related to a specific event.
    """
    
    feed_type = Atom1Feed
    
    def get_object(self, request, event_id):
        """Get the event object."""
        from events.models import Event
        return get_object_or_404(Event, id=event_id)
    
    def title(self, obj):
        """Return feed title."""
        return f"MMA Database - Articles about {obj.name}"
    
    def link(self, obj):
        """Return event URL."""
        return obj.get_absolute_url()
    
    def description(self, obj):
        """Return feed description."""
        return f"Coverage and analysis of {obj.name}"
    
    def items(self, obj):
        """Return latest articles about this event."""
        return Article.objects.filter(
            event_relationships__event=obj,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')[:10]
    
    def item_title(self, item):
        """Return article title."""
        return item.title
    
    def item_description(self, item):
        """Return article excerpt."""
        return item.excerpt or strip_tags(item.content)[:300] + '...'
    
    def item_link(self, item):
        """Return article URL."""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Return publication date."""
        return item.published_at
    
    def item_author_name(self, item):
        """Return author name."""
        return item.author.get_full_name() if item.author else "MMA Database"