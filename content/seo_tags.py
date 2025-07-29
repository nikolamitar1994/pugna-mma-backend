"""
SEO meta tags generation for content management system.

Provides comprehensive meta tag generation including Open Graph,
Twitter Cards, and other SEO-related HTML meta tags.
"""

from django.conf import settings
from django.utils.html import escape, strip_tags
from django.utils.text import Truncator
from typing import Dict, List, Optional, Any
import re


class SEOTagGenerator:
    """
    Generate comprehensive SEO meta tags for various content types.
    """
    
    def __init__(self, request=None):
        """Initialize with optional request object for absolute URLs."""
        self.request = request
        self.site_url = self._get_site_url()
        self.site_name = getattr(settings, 'SITE_NAME', 'MMA Database')
        self.default_image = getattr(settings, 'DEFAULT_OG_IMAGE', '/static/images/og-default.jpg')
    
    def _get_site_url(self) -> str:
        """Get the base site URL."""
        if self.request:
            return f"{self.request.scheme}://{self.request.get_host()}"
        return getattr(settings, 'SITE_URL', 'https://mmadatabase.com')
    
    def _get_absolute_url(self, path: str) -> str:
        """Convert relative path to absolute URL."""
        if path.startswith('http'):
            return path
        return f"{self.site_url}{path}"
    
    def generate_article_meta_tags(self, article) -> Dict[str, Any]:
        """
        Generate comprehensive meta tags for an article.
        
        Args:
            article: Article model instance
            
        Returns:
            Dictionary containing all meta tag data
        """
        # Basic SEO meta tags
        title = self._get_seo_title(article)
        description = self._get_seo_description(article)
        canonical_url = self._get_absolute_url(article.get_absolute_url())
        
        # Image URLs
        image_url = self._get_article_image_url(article)
        og_image_url = self._get_og_image_url(article)
        
        # Keywords
        keywords = self._get_article_keywords(article)
        
        meta_tags = {
            # Basic SEO
            'title': title,
            'description': description,
            'keywords': ', '.join(keywords) if keywords else None,
            'canonical': canonical_url,
            'robots': self._get_robots_directive(article),
            
            # Open Graph
            'og:type': 'article',
            'og:title': title,
            'og:description': description,
            'og:url': canonical_url,
            'og:site_name': self.site_name,
            'og:image': og_image_url,
            'og:image:width': '1200',
            'og:image:height': '630',
            'og:image:alt': article.featured_image_alt or title,
            'og:locale': 'en_US',
            
            # Twitter Cards
            'twitter:card': 'summary_large_image',
            'twitter:site': getattr(settings, 'TWITTER_SITE', '@mmadatabase'),
            'twitter:title': title,
            'twitter:description': description,
            'twitter:image': og_image_url,
            'twitter:image:alt': article.featured_image_alt or title,
            
            # Article-specific Open Graph
            'article:published_time': article.published_at.isoformat() if article.published_at else None,
            'article:modified_time': article.updated_at.isoformat(),
            'article:author': self._get_author_url(article.author) if article.author else None,
            'article:section': article.category.name if article.category else None,
            'article:tag': [tag.name for tag in article.tags.all()],
            
            # Additional SEO
            'news_keywords': ', '.join(keywords[:5]) if keywords else None,  # First 5 keywords
            'article:reading_time': f"{article.reading_time} min" if article.reading_time else None,
            'article:word_count': self._calculate_word_count(article.content),
        }
        
        # Add author information if available
        if article.author:
            author_meta = self._get_author_meta(article.author)
            meta_tags.update(author_meta)
        
        # Add publication-specific tags
        if article.is_breaking:
            meta_tags['news:urgency'] = 'high'
        
        # Remove None values
        return {k: v for k, v in meta_tags.items() if v is not None}
    
    def generate_category_meta_tags(self, category) -> Dict[str, Any]:
        """
        Generate meta tags for a category page.
        
        Args:
            category: Category model instance
            
        Returns:
            Dictionary containing meta tag data
        """
        title = self._get_category_title(category)
        description = self._get_category_description(category)
        canonical_url = self._get_absolute_url(category.get_absolute_url())
        
        meta_tags = {
            'title': title,
            'description': description,
            'canonical': canonical_url,
            'robots': 'index, follow',
            
            # Open Graph
            'og:type': 'website',
            'og:title': title,
            'og:description': description,
            'og:url': canonical_url,
            'og:site_name': self.site_name,
            'og:image': self._get_absolute_url(self.default_image),
            
            # Twitter Cards
            'twitter:card': 'summary',
            'twitter:site': getattr(settings, 'TWITTER_SITE', '@mmadatabase'),
            'twitter:title': title,
            'twitter:description': description,
        }
        
        return {k: v for k, v in meta_tags.items() if v is not None}
    
    def generate_fighter_meta_tags(self, fighter) -> Dict[str, Any]:
        """
        Generate meta tags for a fighter profile page.
        
        Args:
            fighter: Fighter model instance
            
        Returns:
            Dictionary containing meta tag data
        """
        title = f"{fighter.get_full_name()} - MMA Fighter Profile | {self.site_name}"
        description = self._get_fighter_description(fighter)
        canonical_url = self._get_absolute_url(fighter.get_absolute_url())
        
        meta_tags = {
            'title': title,
            'description': description,
            'canonical': canonical_url,
            'robots': 'index, follow',
            
            # Open Graph
            'og:type': 'profile',
            'og:title': title,
            'og:description': description,
            'og:url': canonical_url,
            'og:site_name': self.site_name,
            'og:image': self._get_fighter_image_url(fighter),
            
            # Profile-specific Open Graph
            'profile:first_name': fighter.first_name,
            'profile:last_name': fighter.last_name,
            'profile:username': fighter.nickname if fighter.nickname else None,
            
            # Twitter Cards
            'twitter:card': 'summary',
            'twitter:site': getattr(settings, 'TWITTER_SITE', '@mmadatabase'),
            'twitter:title': title,
            'twitter:description': description,
            'twitter:image': self._get_fighter_image_url(fighter),
        }
        
        return {k: v for k, v in meta_tags.items() if v is not None}
    
    def generate_event_meta_tags(self, event) -> Dict[str, Any]:
        """
        Generate meta tags for an event page.
        
        Args:
            event: Event model instance
            
        Returns:
            Dictionary containing meta tag data
        """
        title = f"{event.name} - MMA Event | {self.site_name}"
        description = self._get_event_description(event)
        canonical_url = self._get_absolute_url(event.get_absolute_url())
        
        meta_tags = {
            'title': title,
            'description': description,
            'canonical': canonical_url,
            'robots': 'index, follow',
            
            # Open Graph
            'og:type': 'article',  # Events are treated as articles
            'og:title': title,
            'og:description': description,
            'og:url': canonical_url,
            'og:site_name': self.site_name,
            'og:image': self._get_event_image_url(event),
            
            # Event-specific data
            'event:start_time': event.date.isoformat() if event.date else None,
            'event:location': event.location if event.location else None,
            'event:organizer': event.organization.name if event.organization else None,
            
            # Twitter Cards
            'twitter:card': 'summary_large_image',
            'twitter:site': getattr(settings, 'TWITTER_SITE', '@mmadatabase'),
            'twitter:title': title,
            'twitter:description': description,
            'twitter:image': self._get_event_image_url(event),
        }
        
        return {k: v for k, v in meta_tags.items() if v is not None}
    
    def generate_meta_html(self, meta_tags: Dict[str, Any]) -> str:
        """
        Convert meta tags dictionary to HTML meta tags.
        
        Args:
            meta_tags: Dictionary of meta tag data
            
        Returns:
            HTML string with meta tags
        """
        html_tags = []
        
        # Basic meta tags
        basic_tags = ['title', 'description', 'keywords', 'robots']
        for tag in basic_tags:
            if tag in meta_tags and meta_tags[tag]:
                if tag == 'title':
                    html_tags.append(f'<title>{escape(meta_tags[tag])}</title>')
                else:
                    html_tags.append(f'<meta name="{tag}" content="{escape(str(meta_tags[tag]))}">')
        
        # Canonical link
        if 'canonical' in meta_tags:
            html_tags.append(f'<link rel="canonical" href="{meta_tags["canonical"]}">')
        
        # Open Graph tags
        og_tags = {k: v for k, v in meta_tags.items() if k.startswith('og:')}
        for key, value in og_tags.items():
            if isinstance(value, list):
                for item in value:
                    html_tags.append(f'<meta property="{key}" content="{escape(str(item))}">')
            else:
                html_tags.append(f'<meta property="{key}" content="{escape(str(value))}">')
        
        # Twitter Card tags
        twitter_tags = {k: v for k, v in meta_tags.items() if k.startswith('twitter:')}
        for key, value in twitter_tags.items():
            html_tags.append(f'<meta name="{key}" content="{escape(str(value))}">')
        
        # Article-specific tags
        article_tags = {k: v for k, v in meta_tags.items() if k.startswith('article:')}
        for key, value in article_tags.items():
            if isinstance(value, list):
                for item in value:
                    html_tags.append(f'<meta property="{key}" content="{escape(str(item))}">')
            else:
                html_tags.append(f'<meta property="{key}" content="{escape(str(value))}">')
        
        # Other meta tags
        other_tags = {
            k: v for k, v in meta_tags.items() 
            if not any(k.startswith(prefix) for prefix in ['og:', 'twitter:', 'article:']) 
            and k not in basic_tags + ['canonical']
        }
        for key, value in other_tags.items():
            html_tags.append(f'<meta name="{key}" content="{escape(str(value))}">')
        
        return '\n'.join(html_tags)
    
    def _get_seo_title(self, article) -> str:
        """Get SEO-optimized title for article."""
        seo_title = article.meta_title or article.title
        
        # Ensure title is within optimal length (50-60 characters)
        if len(seo_title) > 60:
            seo_title = Truncator(seo_title).chars(57) + '...'
        
        # Add site name if not already present
        if self.site_name.lower() not in seo_title.lower():
            seo_title = f"{seo_title} | {self.site_name}"
        
        return seo_title
    
    def _get_seo_description(self, article) -> str:
        """Get SEO-optimized description for article."""
        description = article.meta_description or article.excerpt
        
        if not description and article.content:
            # Generate from content
            plain_text = strip_tags(article.content)
            description = Truncator(plain_text).chars(155)
        
        # Ensure description is within optimal length (150-160 characters)
        if description and len(description) > 160:
            description = Truncator(description).chars(157) + '...'
        
        return description or f"Read about {article.title} on {self.site_name}"
    
    def _get_article_image_url(self, article) -> str:
        """Get article's featured image URL."""
        if article.featured_image:
            return self._get_absolute_url(article.featured_image.url)
        return self._get_absolute_url(self.default_image)
    
    def _get_og_image_url(self, article) -> str:
        """Get Open Graph optimized image URL."""
        # If article has processed SEO images, use OG version
        if hasattr(article, 'seo_images') and article.seo_images.get('og_image'):
            return self._get_absolute_url(article.seo_images['og_image'])
        
        # Fallback to regular featured image
        return self._get_article_image_url(article)
    
    def _get_article_keywords(self, article) -> List[str]:
        """Extract keywords from article."""
        keywords = []
        
        # Add category
        if article.category:
            keywords.append(article.category.name)
        
        # Add tags
        keywords.extend([tag.name for tag in article.tags.all()])
        
        # Add related entities
        for fighter_rel in article.fighter_relationships.all():
            keywords.append(fighter_rel.fighter.get_full_name())
        
        for event_rel in article.event_relationships.all():
            keywords.append(event_rel.event.name)
        
        # Limit to top 10 keywords
        return keywords[:10]
    
    def _get_robots_directive(self, article) -> str:
        """Get robots meta directive for article."""
        if article.status != 'published':
            return 'noindex, nofollow'
        
        if article.is_breaking:
            return 'index, follow, max-snippet:-1, max-image-preview:large'
        
        return 'index, follow'
    
    def _get_author_url(self, author) -> str:
        """Get author profile URL."""
        # This would need to be implemented based on your URL structure
        return f"{self.site_url}/author/{author.username}/"
    
    def _get_author_meta(self, author) -> Dict[str, str]:
        """Get author-specific meta tags."""
        return {
            'author': author.get_full_name() or author.username,
        }
    
    def _calculate_word_count(self, content: str) -> int:
        """Calculate word count from HTML content."""
        plain_text = strip_tags(content)
        return len(plain_text.split())
    
    def _get_category_title(self, category) -> str:
        """Get SEO title for category."""
        title = category.meta_title or f"{category.name} Articles"
        return f"{title} | {self.site_name}"
    
    def _get_category_description(self, category) -> str:
        """Get SEO description for category."""
        if category.meta_description:
            return category.meta_description
        
        if category.description:
            return Truncator(category.description).chars(155)
        
        article_count = category.get_article_count()
        return f"Browse {article_count} articles in {category.name} category on {self.site_name}"
    
    def _get_fighter_description(self, fighter) -> str:
        """Get SEO description for fighter."""
        record = f"{fighter.wins}-{fighter.losses}"
        if fighter.draws > 0:
            record += f"-{fighter.draws}"
        
        description = f"{fighter.get_full_name()} is a professional MMA fighter with a record of {record}."
        
        if fighter.nickname:
            description = f'{fighter.get_full_name()} "{fighter.nickname}" is a professional MMA fighter with a record of {record}.'
        
        if fighter.nationality:
            description += f" Fighting out of {fighter.nationality}."
        
        return description
    
    def _get_fighter_image_url(self, fighter) -> str:
        """Get fighter's profile image URL."""
        if hasattr(fighter, 'image') and fighter.image:
            return self._get_absolute_url(fighter.image.url)
        return self._get_absolute_url(self.default_image)
    
    def _get_event_description(self, event) -> str:
        """Get SEO description for event."""
        description = f"{event.name} is a mixed martial arts event"
        
        if event.organization:
            description += f" organized by {event.organization.name}"
        
        if event.date:
            description += f" scheduled for {event.date.strftime('%B %d, %Y')}"
        
        if event.location:
            description += f" in {event.location}"
        
        description += "."
        
        return description
    
    def _get_event_image_url(self, event) -> str:
        """Get event's promotional image URL."""
        if hasattr(event, 'poster_image') and event.poster_image:
            return self._get_absolute_url(event.poster_image.url)
        return self._get_absolute_url(self.default_image)


def get_article_meta_html(article, request=None) -> str:
    """
    Convenience function to get article meta tags as HTML.
    
    Args:
        article: Article model instance
        request: Django request object (optional)
        
    Returns:
        HTML string with meta tags
    """
    generator = SEOTagGenerator(request)
    meta_tags = generator.generate_article_meta_tags(article)
    return generator.generate_meta_html(meta_tags)


def get_fighter_meta_html(fighter, request=None) -> str:
    """
    Convenience function to get fighter meta tags as HTML.
    
    Args:
        fighter: Fighter model instance
        request: Django request object (optional)
        
    Returns:
        HTML string with meta tags
    """
    generator = SEOTagGenerator(request)
    meta_tags = generator.generate_fighter_meta_tags(fighter)
    return generator.generate_meta_html(meta_tags)


def get_event_meta_html(event, request=None) -> str:
    """
    Convenience function to get event meta tags as HTML.
    
    Args:
        event: Event model instance
        request: Django request object (optional)
        
    Returns:
        HTML string with meta tags
    """
    generator = SEOTagGenerator(request)
    meta_tags = generator.generate_event_meta_tags(event)
    return generator.generate_meta_html(meta_tags)