"""
Sitemap generation for content management system.

This module provides XML sitemaps for articles, categories, and tags
to improve SEO and search engine crawling.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import Article, Category, Tag


class ArticleSitemap(Sitemap):
    """
    Sitemap for published articles.
    
    Includes only published articles with proper change frequency
    and priority based on article type and recency.
    """
    
    changefreq = "weekly"
    priority = 0.7
    protocol = 'https'
    
    def items(self):
        """Return published articles ordered by publication date."""
        return Article.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('category', 'author').order_by('-published_at')
    
    def lastmod(self, obj):
        """Return the last modification date."""
        return obj.updated_at
    
    def changefreq(self, obj):
        """
        Determine change frequency based on article age and type.
        
        Recent articles change more frequently, older ones less so.
        Breaking news and analysis change more often than profiles.
        """
        now = timezone.now()
        age = now - obj.published_at if obj.published_at else timedelta(days=365)
        
        # Breaking news changes very frequently
        if obj.is_breaking:
            return 'hourly'
        
        # Recent articles (less than 7 days old)
        if age < timedelta(days=7):
            if obj.article_type in ['news', 'coverage']:
                return 'daily'
            return 'weekly'
        
        # Medium age articles (7-30 days)
        elif age < timedelta(days=30):
            return 'weekly'
        
        # Older articles change less frequently
        else:
            return 'monthly'
    
    def priority(self, obj):
        """
        Calculate priority based on article importance and type.
        
        Featured articles and certain types get higher priority.
        """
        base_priority = 0.5
        
        # Featured articles get higher priority
        if obj.is_featured:
            base_priority += 0.2
        
        # Breaking news gets highest priority
        if obj.is_breaking:
            base_priority += 0.3
        
        # Article type adjustments
        type_priorities = {
            'news': 0.1,
            'analysis': 0.15,
            'preview': 0.1,
            'recap': 0.1,
            'interview': 0.05,
            'profile': 0.0,
            'ranking': 0.1,
            'technical': 0.0,
        }
        
        base_priority += type_priorities.get(obj.article_type, 0)
        
        # Recent articles get slightly higher priority
        now = timezone.now()
        if obj.published_at:
            age = now - obj.published_at
            if age < timedelta(days=7):
                base_priority += 0.1
            elif age < timedelta(days=30):
                base_priority += 0.05
        
        # Ensure priority stays within valid range
        return min(1.0, max(0.1, base_priority))
    
    def location(self, obj):
        """Return the URL for the article."""
        return obj.get_absolute_url()


class CategorySitemap(Sitemap):
    """
    Sitemap for article categories.
    
    Includes active categories with article counts.
    """
    
    changefreq = "daily"
    priority = 0.6
    protocol = 'https'
    
    def items(self):
        """Return active categories with published articles."""
        return Category.objects.filter(
            is_active=True,
            articles__status='published'
        ).distinct().order_by('order', 'name')
    
    def lastmod(self, obj):
        """
        Return the last modification date based on the most recent article.
        """
        latest_article = obj.articles.filter(
            status='published'
        ).order_by('-updated_at').first()
        
        if latest_article:
            return latest_article.updated_at
        return obj.updated_at
    
    def changefreq(self, obj):
        """
        Determine change frequency based on category activity.
        """
        # Count recent articles in this category
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = obj.articles.filter(
            status='published',
            published_at__gte=week_ago
        ).count()
        
        if recent_count >= 5:
            return 'daily'
        elif recent_count >= 2:
            return 'weekly'
        else:
            return 'monthly'
    
    def priority(self, obj):
        """
        Calculate priority based on article count and recent activity.
        """
        base_priority = 0.6
        
        # Get article count
        article_count = obj.get_article_count()
        
        # More articles = higher priority
        if article_count >= 50:
            base_priority += 0.2
        elif article_count >= 20:
            base_priority += 0.1
        elif article_count >= 5:
            base_priority += 0.05
        
        # Recent activity boosts priority
        week_ago = timezone.now() - timedelta(days=7)
        recent_count = obj.articles.filter(
            status='published',
            published_at__gte=week_ago
        ).count()
        
        if recent_count >= 3:
            base_priority += 0.1
        elif recent_count >= 1:
            base_priority += 0.05
        
        return min(1.0, max(0.3, base_priority))
    
    def location(self, obj):
        """Return the URL for the category."""
        return obj.get_absolute_url()


class TagSitemap(Sitemap):
    """
    Sitemap for article tags.
    
    Includes tags that have published articles associated.
    """
    
    changefreq = "weekly"
    priority = 0.4
    protocol = 'https'
    
    def items(self):
        """Return tags with published articles."""
        return Tag.objects.filter(
            articles__status='published',
            usage_count__gt=0
        ).distinct().order_by('-usage_count', 'name')
    
    def lastmod(self, obj):
        """
        Return the last modification date based on the most recent article.
        """
        latest_article = obj.articles.filter(
            status='published'
        ).order_by('-updated_at').first()
        
        if latest_article:
            return latest_article.updated_at
        return obj.updated_at
    
    def changefreq(self, obj):
        """
        Determine change frequency based on tag usage.
        """
        if obj.usage_count >= 10:
            return 'weekly'
        elif obj.usage_count >= 5:
            return 'monthly'
        else:
            return 'yearly'
    
    def priority(self, obj):
        """
        Calculate priority based on tag usage count.
        """
        base_priority = 0.3
        
        # More usage = higher priority
        if obj.usage_count >= 20:
            base_priority += 0.2
        elif obj.usage_count >= 10:
            base_priority += 0.1
        elif obj.usage_count >= 5:
            base_priority += 0.05
        
        return min(0.6, max(0.2, base_priority))
    
    def location(self, obj):
        """Return the URL for the tag."""
        return obj.get_absolute_url()


class StaticContentSitemap(Sitemap):
    """
    Sitemap for static content pages.
    
    Includes important static pages like about, contact, etc.
    """
    
    changefreq = "monthly"
    priority = 0.5
    protocol = 'https'
    
    def items(self):
        """Return list of static page identifiers."""
        return [
            'content:article_list',
            'content:category_list',
            'content:tag_list',
        ]
    
    def location(self, item):
        """Return the URL for static pages."""
        return reverse(item)
    
    def changefreq(self, obj):
        """Static pages change monthly."""
        return 'monthly'
    
    def priority(self, obj):
        """All static pages have medium priority."""
        return 0.5


# Sitemap index that combines all sitemaps
sitemaps = {
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
    'tags': TagSitemap,
    'static': StaticContentSitemap,
}