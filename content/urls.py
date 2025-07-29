"""
URL configuration for content management system.

Includes routes for articles, categories, tags, and SEO features
like sitemaps and RSS feeds.
"""

from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from . import views
from .sitemaps import sitemaps
from .feeds import CategoryFeed, TagFeed, LatestArticlesFeed

app_name = 'content'

# API URLs are handled by the main API router in api/urls.py

# Main URL patterns
urlpatterns = [
    # Article URLs
    path('', views.ArticleListView.as_view(), name='article_list'),
    path('article/<slug:slug>/', views.ArticleDetailHTMLView.as_view(), name='article_detail'),
    
    # Category URLs
    path('categories/', views.CategoryListHTMLView.as_view(), name='category_list'),
    path('category/<slug:slug>/', views.CategoryDetailHTMLView.as_view(), name='category_detail'),
    
    # Tag URLs
    path('tags/', views.TagListHTMLView.as_view(), name='tag_list'),
    path('tag/<slug:slug>/', views.TagDetailHTMLView.as_view(), name='tag_detail'),
    
    # Search
    path('search/', views.ArticleSearchHTMLView.as_view(), name='article_search'),
    
    # SEO Features
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # RSS Feeds
    path('feeds/latest/', LatestArticlesFeed(), name='latest_articles_feed'),
    path('feeds/category/<slug:slug>/', CategoryFeed(), name='category_feed'), 
    path('feeds/tag/<slug:slug>/', TagFeed(), name='tag_feed'),
    
    # Robot.txt (if needed)
    path('robots.txt', TemplateView.as_view(template_name='content/robots.txt', content_type='text/plain'), name='robots_txt'),
]