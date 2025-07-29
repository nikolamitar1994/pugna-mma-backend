"""
Django Admin Configuration for Content Management System

This module provides comprehensive admin interfaces for managing articles,
categories, tags, and their relationships with fighters, events, and organizations.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
# from django_ckeditor_5.widgets import CKEditor5Widget  # Commented out temporarily
from django import forms

from .models import (
    Article, Category, Tag, ArticleFighter, ArticleEvent, 
    ArticleOrganization, ArticleView
)
from users.models import User, UserProfile, EditorialWorkflowLog, AssignmentNotification


# Custom Forms with Rich Text Editor

class ArticleAdminForm(forms.ModelForm):
    """Custom form for Article admin with CKEditor integration"""
    
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20, 'cols': 80}),
            # 'content': CKEditor5Widget(
            #     attrs={'class': 'django_ckeditor_5'},
            #     config_name='default'
            # ),
            'excerpt': forms.Textarea(attrs={'rows': 4, 'cols': 80}),
        }


# Inline Admin Classes

class ArticleFighterInline(admin.TabularInline):
    """Inline for managing article-fighter relationships"""
    model = ArticleFighter
    extra = 0
    fields = ('fighter', 'relationship_type', 'display_order')
    autocomplete_fields = ['fighter']
    ordering = ['display_order', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('fighter')


class ArticleEventInline(admin.TabularInline):
    """Inline for managing article-event relationships"""
    model = ArticleEvent
    extra = 0
    fields = ('event', 'relationship_type', 'display_order')
    autocomplete_fields = ['event']
    ordering = ['display_order', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')


class ArticleOrganizationInline(admin.TabularInline):
    """Inline for managing article-organization relationships"""
    model = ArticleOrganization
    extra = 0
    fields = ('organization', 'relationship_type', 'display_order')
    autocomplete_fields = ['organization']
    ordering = ['display_order', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


# Main Admin Classes

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Django admin interface for content categories"""
    
    list_display = [
        'get_name_hierarchy', 'slug', 'get_article_count', 'order', 
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Category Information', {
            'fields': (
                ('name', 'slug'),
                'description',
                'parent',
                ('order', 'is_active'),
            )
        }),
        ('SEO Settings', {
            'fields': (
                'meta_title',
                'meta_description',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['make_active', 'make_inactive', 'bulk_reorder']
    
    def get_name_hierarchy(self, obj):
        """Display category name with hierarchy"""
        path = obj.get_full_path()
        if len(path) > 1:
            return format_html(
                '<span style="color: #666;">{}</span> → <strong>{}</strong>',
                ' → '.join(path[:-1]),
                path[-1]
            )
        return format_html('<strong>{}</strong>', obj.name)
    get_name_hierarchy.short_description = 'Category'
    get_name_hierarchy.admin_order_field = 'name'
    
    def get_article_count(self, obj):
        """Display number of published articles in this category"""
        count = obj.get_article_count()
        if count > 0:
            url = reverse('admin:content_article_changelist') + f'?category={obj.pk}'
            return format_html(
                '<a href="{}" style="color: #0066cc;">{} articles</a>',
                url, count
            )
        return '0 articles'
    get_article_count.short_description = 'Articles'
    
    def make_active(self, request, queryset):
        """Mark selected categories as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} categories marked as active.")
    make_active.short_description = "Mark selected categories as active"
    
    def make_inactive(self, request, queryset):
        """Mark selected categories as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} categories marked as inactive.")
    make_inactive.short_description = "Mark selected categories as inactive"
    
    def bulk_reorder(self, request, queryset):
        """Reset order values for selected categories"""
        for i, category in enumerate(queryset.order_by('name'), 1):
            category.order = i * 10
            category.save()
        self.message_user(request, f"Reordered {queryset.count()} categories.")
    bulk_reorder.short_description = "Reorder selected categories"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Django admin interface for content tags"""
    
    list_display = [
        'get_colored_name', 'slug', 'usage_count', 'created_at'
    ]
    list_filter = ['color', 'created_at']
    search_fields = ['name', 'description', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Tag Information', {
            'fields': (
                ('name', 'slug'),
                'description',
                'color',
            )
        }),
        ('Usage Statistics', {
            'fields': ('usage_count',),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['update_usage_counts', 'set_color']
    
    def get_colored_name(self, obj):
        """Display tag name with its color"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            obj.color, obj.name
        )
    get_colored_name.short_description = 'Tag'
    get_colored_name.admin_order_field = 'name'
    
    def update_usage_counts(self, request, queryset):
        """Update usage counts for selected tags"""
        updated = 0
        for tag in queryset:
            old_count = tag.usage_count
            tag.usage_count = tag.articles.count()
            if old_count != tag.usage_count:
                tag.save()
                updated += 1
        self.message_user(request, f"Updated usage counts for {updated} tags.")
    update_usage_counts.short_description = "Update usage counts"
    
    def set_color(self, request, queryset):
        """Set color for selected tags (you'd extend this for color selection)"""
        # This would be extended with a color picker in a real implementation
        queryset.update(color='#007bff')
        self.message_user(request, f"Updated color for {queryset.count()} tags.")
    set_color.short_description = "Set color to blue"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """
    Comprehensive Django admin interface for articles with editorial workflow
    """
    
    form = ArticleAdminForm
    
    list_display = [
        'title', 'get_status_display', 'get_type_display', 'category',
        'author', 'editor', 'get_view_count', 'get_published_date', 'is_featured'
    ]
    
    list_filter = [
        'status', 'article_type', 'category', 'is_featured', 'is_breaking',
        'published_at', 'created_at', 'author', 'editor'
    ]
    
    search_fields = [
        'title', 'excerpt', 'content', 'slug', 'meta_title', 'meta_description'
    ]
    
    prepopulated_fields = {'slug': ('title',)}
    
    autocomplete_fields = ['category', 'author', 'editor']
    
    filter_horizontal = ['tags']
    
    date_hierarchy = 'published_at'
    
    def get_queryset(self, request):
        """Filter articles based on user permissions"""
        qs = super().get_queryset(request)
        
        # Superusers and content admins see everything
        if request.user.is_superuser or request.user.has_perm('content.can_edit_any_article'):
            return qs
        
        # Editors can see all published articles and articles in review
        if request.user.has_perm('content.can_view_unpublished'):
            return qs.filter(
                Q(status__in=['published', 'review']) | Q(author=request.user)
            )
        
        # Authors only see their own articles
        return qs.filter(author=request.user)
    
    def get_readonly_fields(self, request, obj=None):
        """Set readonly fields based on user permissions"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        if obj:  # Editing existing article
            # Authors can't change status directly (use workflow actions)
            if not request.user.has_perm('content.can_publish_article'):
                readonly_fields.extend(['status', 'published_at'])
            
            # Only publishers can set featured/breaking
            if not request.user.has_perm('content.can_feature_article'):
                readonly_fields.append('is_featured')
            
            if not request.user.has_perm('content.can_set_breaking_news'):
                readonly_fields.append('is_breaking')
            
            # Authors can't edit articles under review or published (unless they have higher perms)
            if (obj.status in ['review', 'published'] and 
                not request.user.has_perm('content.can_edit_any_article') and 
                obj.author != request.user):
                readonly_fields.extend([
                    'title', 'content', 'excerpt', 'category', 'tags', 'article_type'
                ])
        
        return readonly_fields
    
    def has_change_permission(self, request, obj=None):
        """Check if user can change this article"""
        if not super().has_change_permission(request, obj):
            return False
        
        if obj is None:  # List view
            return True
        
        # Use the user's can_edit_article method
        return request.user.can_edit_article(obj)
    
    def has_delete_permission(self, request, obj=None):
        """Check if user can delete this article"""
        if not super().has_delete_permission(request, obj):
            return False
        
        if obj is None:  # List view
            return request.user.has_perm('content.can_edit_any_article')
        
        # Only admin or author of draft articles can delete
        return (request.user.has_perm('content.can_edit_any_article') or 
                (obj.author == request.user and obj.status == 'draft'))
    
    fieldsets = (
        ('Article Content', {
            'fields': (
                'title',
                'slug',
                'excerpt',
                'content',
            )
        }),
        ('Organization', {
            'fields': (
                ('category', 'article_type'),
                'tags',
            )
        }),
        ('Publishing', {
            'fields': (
                ('status', 'published_at'),
                ('author', 'editor'),
                ('is_featured', 'is_breaking'),
                'allow_comments',
            )
        }),
        ('Media', {
            'fields': (
                'featured_image',
                'featured_image_alt',
                'featured_image_caption',
            ),
            'classes': ('collapse',),
        }),
        ('SEO & Metadata', {
            'fields': (
                'meta_title',
                'meta_description',
            ),
            'classes': ('collapse',),
        }),
        ('Analytics', {
            'fields': (
                'view_count',
                'reading_time',
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = [
        'view_count', 'reading_time', 'created_at', 'updated_at'
    ]
    
    inlines = [ArticleFighterInline, ArticleEventInline, ArticleOrganizationInline]
    
    actions = [
        'publish_articles', 'unpublish_articles', 'feature_articles',
        'unfeature_articles', 'duplicate_articles', 'generate_seo_data',
        'optimize_images'
    ]
    
    list_per_page = 25
    
    # Custom display methods
    def get_status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'draft': '#6c757d',
            'review': '#ffc107', 
            'published': '#28a745',
            'archived': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    get_status_display.short_description = 'Status'
    get_status_display.admin_order_field = 'status'
    
    def get_type_display(self, obj):
        """Display article type with icon"""
        icons = {
            'news': '📰',
            'analysis': '🔍',
            'interview': '🎙️',
            'preview': '👀',
            'recap': '📝',
            'profile': '👤',
            'ranking': '🏆',
            'technical': '⚙️',
        }
        icon = icons.get(obj.article_type, '📄')
        return format_html('{} {}', icon, obj.get_article_type_display())
    get_type_display.short_description = 'Type'
    get_type_display.admin_order_field = 'article_type'
    
    def get_view_count(self, obj):
        """Display view count with formatting"""
        if obj.view_count >= 1000:
            return format_html(
                '<strong style="color: #28a745;">{:.1f}k</strong>',
                obj.view_count / 1000
            )
        return obj.view_count
    get_view_count.short_description = 'Views'
    get_view_count.admin_order_field = 'view_count'
    
    def get_published_date(self, obj):
        """Display published date or status"""
        if obj.published_at:
            if obj.published_at <= timezone.now():
                return obj.published_at.strftime('%Y-%m-%d %H:%M')
            else:
                return format_html(
                    '<span style="color: #ffc107;">Scheduled: {}</span>',
                    obj.published_at.strftime('%Y-%m-%d %H:%M')
                )
        return '-'
    get_published_date.short_description = 'Published'
    get_published_date.admin_order_field = 'published_at'
    
    # Custom admin actions
    def publish_articles(self, request, queryset):
        """Publish selected articles"""
        updated = 0
        for article in queryset:
            if article.status != 'published':
                article.status = 'published'
                if not article.published_at:
                    article.published_at = timezone.now()
                article.save()
                updated += 1
        self.message_user(request, f"Published {updated} articles.")
    publish_articles.short_description = "Publish selected articles"
    
    def unpublish_articles(self, request, queryset):
        """Unpublish selected articles"""
        updated = queryset.filter(status='published').update(
            status='draft',
            published_at=None
        )
        self.message_user(request, f"Unpublished {updated} articles.")
    unpublish_articles.short_description = "Unpublish selected articles"
    
    def feature_articles(self, request, queryset):
        """Mark selected articles as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"Featured {updated} articles.")
    feature_articles.short_description = "Mark as featured"
    
    def unfeature_articles(self, request, queryset):
        """Remove featured status from selected articles"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"Removed featured status from {updated} articles.")
    unfeature_articles.short_description = "Remove featured status"
    
    def duplicate_articles(self, request, queryset):
        """Create duplicates of selected articles as drafts"""
        duplicated = 0
        for article in queryset:
            # Store related objects before duplication
            tags = list(article.tags.all())
            
            # Duplicate the article
            article.pk = None
            article.slug = f"{article.slug}-copy"
            article.title = f"{article.title} (Copy)"
            article.status = 'draft'
            article.published_at = None
            article.view_count = 0
            article.save()
            
            # Restore tags
            article.tags.set(tags)
            duplicated += 1
        
        self.message_user(request, f"Created {duplicated} article duplicates.")
    duplicate_articles.short_description = "Duplicate selected articles"
    
    def generate_seo_data(self, request, queryset):
        """Generate SEO meta tags and structured data for selected articles"""
        from .seo_tags import SEOTagGenerator
        from .schema import SchemaGenerator
        
        updated = 0
        for article in queryset:
            # Generate meta description if missing
            if not article.meta_description and article.excerpt:
                article.meta_description = article.excerpt[:160]
                updated += 1
            elif not article.meta_description and article.content:
                from django.utils.html import strip_tags
                from django.utils.text import Truncator
                plain_text = strip_tags(article.content)
                article.meta_description = Truncator(plain_text).chars(155)
                updated += 1
            
            # Generate meta title if missing
            if not article.meta_title:
                article.meta_title = article.title
                if len(article.meta_title) > 60:
                    article.meta_title = Truncator(article.meta_title).chars(57) + '...'
                updated += 1
            
            article.save()
        
        self.message_user(request, f"Generated SEO data for {updated} articles.")
    generate_seo_data.short_description = "Generate SEO meta tags"
    
    def optimize_images(self, request, queryset):
        """Optimize featured images for selected articles"""
        from .image_optimization import SEOImageProcessor
        
        optimized = 0
        for article in queryset:
            if article.featured_image:
                try:
                    processor = SEOImageProcessor()
                    image_data = processor.process_article_image(
                        article.featured_image, article.slug
                    )
                    
                    # Store the image data (you'd need to add a field to store this)
                    # article.seo_image_data = image_data
                    # article.save()
                    
                    optimized += 1
                except Exception as e:
                    self.message_user(request, f"Error optimizing image for '{article.title}': {e}", level='ERROR')
        
        self.message_user(request, f"Optimized images for {optimized} articles.")
    optimize_images.short_description = "Optimize featured images"
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related"""
        return super().get_queryset(request).select_related(
            'category', 'author', 'editor'
        ).prefetch_related('tags')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic for articles"""
        # Set author to current user if not set
        if not obj.author_id:
            obj.author = request.user
        
        # Auto-publish if status changed to published and no publish date
        if obj.status == 'published' and not obj.published_at:
            obj.published_at = timezone.now()
        
        super().save_model(request, obj, form, change)


# Relationship Model Admins

@admin.register(ArticleFighter)
class ArticleFighterAdmin(admin.ModelAdmin):
    """Admin interface for article-fighter relationships"""
    
    list_display = [
        'article', 'fighter', 'relationship_type', 'display_order', 'created_at'
    ]
    list_filter = ['relationship_type', 'created_at']
    search_fields = [
        'article__title', 'fighter__first_name', 'fighter__last_name'
    ]
    autocomplete_fields = ['article', 'fighter']
    ordering = ['article', 'display_order']


@admin.register(ArticleEvent) 
class ArticleEventAdmin(admin.ModelAdmin):
    """Admin interface for article-event relationships"""
    
    list_display = [
        'article', 'event', 'relationship_type', 'display_order', 'created_at'
    ]
    list_filter = ['relationship_type', 'created_at']
    search_fields = ['article__title', 'event__name']
    autocomplete_fields = ['article', 'event']
    ordering = ['article', 'display_order']


@admin.register(ArticleOrganization)
class ArticleOrganizationAdmin(admin.ModelAdmin):
    """Admin interface for article-organization relationships"""
    
    list_display = [
        'article', 'organization', 'relationship_type', 'display_order', 'created_at'
    ]
    list_filter = ['relationship_type', 'created_at']
    search_fields = ['article__title', 'organization__name']
    autocomplete_fields = ['article', 'organization']
    ordering = ['article', 'display_order']


# Analytics Admin

@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    """Admin interface for article view analytics"""
    
    list_display = [
        'article', 'user', 'ip_address', 'viewed_at'
    ]
    list_filter = ['viewed_at', 'article']
    search_fields = ['article__title', 'user__username', 'ip_address']
    readonly_fields = ['article', 'user', 'ip_address', 'user_agent', 'referrer', 'viewed_at']
    
    def has_add_permission(self, request):
        """Disable manual creation of view records"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make view records read-only"""
        return False


# Editorial Workflow Admin Classes


