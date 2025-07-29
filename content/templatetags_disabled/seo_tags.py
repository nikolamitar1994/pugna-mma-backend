"""
Template tags for SEO optimization in content management system.

Provides template tags for generating meta tags, structured data,
and other SEO-related HTML elements.
"""

from django import template
from django.utils.safestring import mark_safe
from django.core.cache import cache
import hashlib

# Import optional modules
try:
    from ..seo_tags import SEOTagGenerator
except ImportError:
    SEOTagGenerator = None

try:
    from ..schema import SchemaGenerator, generate_schema_json
except ImportError:
    SchemaGenerator = None
    generate_schema_json = None

try:
    from ..image_optimization import SEOImageProcessor
except ImportError:
    SEOImageProcessor = None

register = template.Library()


@register.simple_tag(takes_context=True)
def article_meta_tags(context, article):
    """
    Generate HTML meta tags for an article.
    
    Usage:
        {% article_meta_tags article %}
    """
    if SEOTagGenerator is None:
        # Return basic meta tags if SEO module is not available
        return mark_safe(f'''
        <title>{article.title}</title>
        <meta name="description" content="{article.excerpt or article.title}">
        <meta property="og:title" content="{article.title}">
        <meta property="og:description" content="{article.excerpt or article.title}">
        ''')
    
    request = context.get('request')
    
    # Create cache key based on article and last update
    cache_key = f"article_meta_{article.id}_{article.updated_at.timestamp()}"
    
    # Try to get from cache
    meta_html = cache.get(cache_key)
    if meta_html is None:
        generator = SEOTagGenerator(request)
        meta_tags = generator.generate_article_meta_tags(article)
        meta_html = generator.generate_meta_html(meta_tags)
        
        # Cache for 1 hour
        cache.set(cache_key, meta_html, 3600)
    
    return mark_safe(meta_html)


@register.simple_tag(takes_context=True)
def fighter_meta_tags(context, fighter):
    """
    Generate HTML meta tags for a fighter profile.
    
    Usage:
        {% fighter_meta_tags fighter %}
    """
    request = context.get('request')
    
    cache_key = f"fighter_meta_{fighter.id}_{fighter.updated_at.timestamp()}"
    
    meta_html = cache.get(cache_key)
    if meta_html is None:
        generator = SEOTagGenerator(request)
        meta_tags = generator.generate_fighter_meta_tags(fighter)
        meta_html = generator.generate_meta_html(meta_tags)
        
        cache.set(cache_key, meta_html, 3600)
    
    return mark_safe(meta_html)


@register.simple_tag(takes_context=True)
def event_meta_tags(context, event):
    """
    Generate HTML meta tags for an event.
    
    Usage:
        {% event_meta_tags event %}
    """
    request = context.get('request')
    
    cache_key = f"event_meta_{event.id}_{event.updated_at.timestamp()}"
    
    meta_html = cache.get(cache_key)
    if meta_html is None:
        generator = SEOTagGenerator(request)
        meta_tags = generator.generate_event_meta_tags(event)
        meta_html = generator.generate_meta_html(meta_tags)
        
        cache.set(cache_key, meta_html, 3600)
    
    return mark_safe(meta_html)


@register.simple_tag(takes_context=True)
def category_meta_tags(context, category):
    """
    Generate HTML meta tags for a category.
    
    Usage:
        {% category_meta_tags category %}
    """
    request = context.get('request')
    
    cache_key = f"category_meta_{category.id}_{category.updated_at.timestamp()}"
    
    meta_html = cache.get(cache_key)
    if meta_html is None:
        generator = SEOTagGenerator(request)
        meta_tags = generator.generate_category_meta_tags(category)
        meta_html = generator.generate_meta_html(meta_tags)
        
        cache.set(cache_key, meta_html, 3600)
    
    return mark_safe(meta_html)


@register.simple_tag(takes_context=True)
def article_json_ld(context, article):
    """
    Generate JSON-LD structured data for an article.
    
    Usage:
        {% article_json_ld article %}
    """
    request = context.get('request')
    
    cache_key = f"article_jsonld_{article.id}_{article.updated_at.timestamp()}"
    
    json_ld = cache.get(cache_key)
    if json_ld is None:
        generator = SchemaGenerator(request)
        schema = generator.generate_article_schema(article)
        json_ld = f'<script type="application/ld+json">\n{generate_schema_json(schema)}\n</script>'
        
        cache.set(cache_key, json_ld, 3600)
    
    return mark_safe(json_ld)


@register.simple_tag(takes_context=True)
def fighter_json_ld(context, fighter):
    """
    Generate JSON-LD structured data for a fighter.
    
    Usage:
        {% fighter_json_ld fighter %}
    """
    request = context.get('request')
    
    cache_key = f"fighter_jsonld_{fighter.id}_{fighter.updated_at.timestamp()}"
    
    json_ld = cache.get(cache_key)
    if json_ld is None:
        generator = SchemaGenerator(request)
        schema = generator.generate_person_schema(fighter)
        json_ld = f'<script type="application/ld+json">\n{generate_schema_json(schema)}\n</script>'
        
        cache.set(cache_key, json_ld, 3600)
    
    return mark_safe(json_ld)


@register.simple_tag(takes_context=True)
def event_json_ld(context, event):
    """
    Generate JSON-LD structured data for an event.
    
    Usage:
        {% event_json_ld event %}
    """
    request = context.get('request')
    
    cache_key = f"event_jsonld_{event.id}_{event.updated_at.timestamp()}"
    
    json_ld = cache.get(cache_key)
    if json_ld is None:
        generator = SchemaGenerator(request)
        schema = generator.generate_sports_event_schema(event)
        json_ld = f'<script type="application/ld+json">\n{generate_schema_json(schema)}\n</script>'
        
        cache.set(cache_key, json_ld, 3600)
    
    return mark_safe(json_ld)


@register.simple_tag(takes_context=True)
def breadcrumb_json_ld(context, breadcrumbs):
    """
    Generate JSON-LD structured data for breadcrumbs.
    
    Usage:
        {% breadcrumb_json_ld breadcrumbs %}
    
    Where breadcrumbs is a list of {"name": "Page Name", "url": "/page/url/"} dicts
    """
    request = context.get('request')
    
    # Create cache key from breadcrumbs
    breadcrumb_str = '|'.join([f"{b['name']}:{b['url']}" for b in breadcrumbs])
    cache_key = f"breadcrumb_jsonld_{hashlib.md5(breadcrumb_str.encode()).hexdigest()}"
    
    json_ld = cache.get(cache_key)
    if json_ld is None:
        generator = SchemaGenerator(request)
        schema = generator.generate_breadcrumb_schema(breadcrumbs)
        json_ld = f'<script type="application/ld+json">\n{generate_schema_json(schema)}\n</script>'
        
        cache.set(cache_key, json_ld, 1800)  # 30 minutes
    
    return mark_safe(json_ld)


@register.simple_tag
def responsive_image(article, alt_text="", css_classes=""):
    """
    Generate responsive image HTML with WebP support.
    
    Usage:
        {% responsive_image article "Alt text" "css-classes" %}
    """
    if not article.featured_image:
        return ""
    
    # Check if article has processed SEO images
    if hasattr(article, 'seo_image_data') and article.seo_image_data:
        processor = SEOImageProcessor()
        return mark_safe(processor.generate_picture_element(
            article.seo_image_data,
            alt_text or article.featured_image_alt or article.title,
            css_classes
        ))
    
    # Fallback to simple img tag
    img_url = article.featured_image.url
    alt = alt_text or article.featured_image_alt or article.title
    classes = f' class="{css_classes}"' if css_classes else ''
    
    return mark_safe(f'<img src="{img_url}" alt="{alt}"{classes} loading="lazy">')


@register.inclusion_tag('content/partials/rss_links.html')
def rss_links(category=None, tag=None):
    """
    Generate RSS feed links for inclusion in HTML head.
    
    Usage:
        {% rss_links %}
        {% rss_links category=category %}
        {% rss_links tag=tag %}
    """
    return {
        'category': category,
        'tag': tag,
    }


@register.simple_tag
def canonical_url(obj, request=None):
    """
    Generate canonical URL for an object.
    
    Usage:
        {% canonical_url article request %}
    """
    if hasattr(obj, 'get_absolute_url'):
        relative_url = obj.get_absolute_url()
        
        if request:
            return f"{request.scheme}://{request.get_host()}{relative_url}"
        else:
            from django.conf import settings
            site_url = getattr(settings, 'SITE_URL', 'https://mmadatabase.com')
            return f"{site_url}{relative_url}"
    
    return ""


@register.filter
def truncate_meta_description(text, length=160):
    """
    Truncate text for meta description with proper length.
    
    Usage:
        {{ article.content|striptags|truncate_meta_description }}
    """
    if not text:
        return ""
    
    if len(text) <= length:
        return text
    
    # Find last space before length limit
    truncated = text[:length]
    last_space = truncated.rfind(' ')
    
    if last_space > length * 0.8:  # If last space is reasonably close to limit
        return text[:last_space] + '...'
    else:
        return text[:length-3] + '...'


@register.simple_tag
def reading_time(content):
    """
    Calculate and format reading time for content.
    
    Usage:
        {% reading_time article.content %}
    """
    if not content:
        return "1 min read"
    
    from django.utils.html import strip_tags
    word_count = len(strip_tags(content).split())
    minutes = max(1, word_count // 200)  # Average 200 words per minute
    
    if minutes == 1:
        return "1 min read"
    else:
        return f"{minutes} min read"


@register.simple_tag
def article_word_count(content):
    """
    Get word count for article content.
    
    Usage:
        {% article_word_count article.content %}
    """
    if not content:
        return 0
    
    from django.utils.html import strip_tags
    return len(strip_tags(content).split())


@register.simple_tag(takes_context=True)
def social_share_urls(context, article):
    """
    Generate social media sharing URLs.
    
    Usage:
        {% social_share_urls article %}
    """
    request = context.get('request')
    
    if request:
        article_url = f"{request.scheme}://{request.get_host()}{article.get_absolute_url()}"
    else:
        from django.conf import settings
        site_url = getattr(settings, 'SITE_URL', 'https://mmadatabase.com')
        article_url = f"{site_url}{article.get_absolute_url()}"
    
    title = article.title
    
    return {
        'twitter': f"https://twitter.com/intent/tweet?url={article_url}&text={title}",
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={article_url}",
        'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={article_url}",
        'reddit': f"https://www.reddit.com/submit?url={article_url}&title={title}",
    }