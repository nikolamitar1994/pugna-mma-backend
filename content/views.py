"""
HTML Views for content management system.

Provides HTML views for articles, categories, and tags with comprehensive
SEO optimization and user-friendly interfaces. API ViewSets are handled
separately in api/views.py to avoid naming conflicts.
"""

from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone

from .models import Article, Category, Tag


# HTML Views for Content Pages

class ArticleListView(ListView):
    """
    HTML view for listing articles with pagination and filtering.
    """
    model = Article
    template_name = 'content/article_list.html'
    context_object_name = 'articles'
    paginate_by = 20
    
    def get_queryset(self):
        """Return published articles with related data."""
        queryset = Article.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags',
            'fighter_relationships__fighter',
            'event_relationships__event'
        ).order_by('-published_at')
        
        # Filter by category if provided
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by tag if provided
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(excerpt__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context for SEO and filtering."""
        context = super().get_context_data(**kwargs)
        
        # Add categories for navigation
        context['categories'] = Category.objects.filter(
            is_active=True,
            articles__status='published'
        ).distinct().order_by('order', 'name')
        
        # Add popular tags
        context['popular_tags'] = Tag.objects.filter(
            articles__status='published'
        ).order_by('-usage_count')[:20]
        
        # Add current filters
        context['current_category'] = self.request.GET.get('category')
        context['current_tag'] = self.request.GET.get('tag')
        context['search_query'] = self.request.GET.get('q', '')
        
        return context


class ArticleDetailHTMLView(DetailView):
    """
    HTML view for individual article display with SEO optimization.
    """
    model = Article
    template_name = 'content/article_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Return published articles with all related data."""
        return Article.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author', 'editor'
        ).prefetch_related(
            'tags',
            'fighter_relationships__fighter',
            'event_relationships__event',
            'organization_relationships__organization'
        )
    
    def get_object(self, queryset=None):
        """Get article and increment view count."""
        article = super().get_object(queryset)
        
        # Increment view count (use F() to avoid race conditions in production)
        from django.db.models import F
        Article.objects.filter(pk=article.pk).update(view_count=F('view_count') + 1)
        
        # Refresh from DB to get updated view count
        article.refresh_from_db(fields=['view_count'])
        
        return article
    
    def get_context_data(self, **kwargs):
        """Add additional context for related content and SEO."""
        context = super().get_context_data(**kwargs)
        article = context['article']
        
        # Add related articles
        context['related_articles'] = article.get_related_articles(limit=4)
        
        # Add breadcrumb data for structured data
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Articles', 'url': '/content/'},
        ]
        
        if article.category:
            breadcrumbs.append({
                'name': article.category.name,
                'url': article.category.get_absolute_url()
            })
        
        breadcrumbs.append({
            'name': article.title,
            'url': article.get_absolute_url()
        })
        
        context['breadcrumbs'] = breadcrumbs
        
        return context


class CategoryDetailHTMLView(DetailView):
    """
    HTML view for category pages with article listings.
    """
    model = Category
    template_name = 'content/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Return active categories."""
        return Category.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        """Add category articles and pagination."""
        context = super().get_context_data(**kwargs)
        category = context['category']
        
        # Get articles in this category
        articles = Article.objects.filter(
            category=category,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'author'
        ).prefetch_related(
            'tags'
        ).order_by('-published_at')
        
        # Paginate articles
        paginator = Paginator(articles, 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['articles'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        context['page_obj'] = page_obj
        
        return context


class CategoryListHTMLView(ListView):
    """
    HTML view for listing all categories.
    """
    model = Category
    template_name = 'content/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        """Return active categories with article counts."""
        return Category.objects.filter(
            is_active=True,
            articles__status='published'
        ).distinct().order_by('order', 'name')


class TagDetailHTMLView(DetailView):
    """
    HTML view for tag pages with article listings.
    """
    model = Tag
    template_name = 'content/tag_detail.html'
    context_object_name = 'tag'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        """Add tag articles and pagination."""
        context = super().get_context_data(**kwargs)
        tag = context['tag']
        
        # Get articles with this tag
        articles = Article.objects.filter(
            tags=tag,
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).order_by('-published_at')
        
        # Paginate articles
        paginator = Paginator(articles, 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['articles'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        context['page_obj'] = page_obj
        
        return context


class TagListHTMLView(ListView):
    """
    HTML view for listing all tags.
    """
    model = Tag
    template_name = 'content/tag_list.html'
    context_object_name = 'tags'
    
    def get_queryset(self):
        """Return tags with articles, ordered by usage."""
        return Tag.objects.filter(
            articles__status='published'
        ).distinct().order_by('-usage_count', 'name')


class ArticleSearchHTMLView(ListView):
    """
    HTML view for article search results.
    """
    model = Article
    template_name = 'content/search_results.html'
    context_object_name = 'articles'
    paginate_by = 15
    
    def get_queryset(self):
        """Return search results."""
        query = self.request.GET.get('q', '').strip()
        
        if not query:
            return Article.objects.none()
        
        return Article.objects.filter(
            Q(title__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__icontains=query) |
            Q(category__name__icontains=query),
            status='published',
            published_at__lte=timezone.now()
        ).select_related(
            'category', 'author'
        ).prefetch_related(
            'tags'
        ).distinct().order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        """Add search context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['total_results'] = self.get_queryset().count()
        return context


# Note: API ViewSets are defined in api/views.py to avoid conflicts
# This file contains only HTML views for the content management system