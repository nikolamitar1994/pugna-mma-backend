from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FighterViewSet, FightHistoryViewSet, OrganizationViewSet, WeightClassViewSet,
    EventViewSet, FightViewSet,
    # Ranking views
    FighterRankingViewSet, FighterStatisticsViewSet, RankingHistoryViewSet,
    # Content views
    CategoryViewSet, TagViewSet, ArticleViewSet,
    ArticleFighterViewSet, ArticleEventViewSet, ArticleOrganizationViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'fighters', FighterViewSet)
router.register(r'fight-history', FightHistoryViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'weight-classes', WeightClassViewSet)
router.register(r'events', EventViewSet)
router.register(r'fights', FightViewSet)

# Ranking endpoints
router.register(r'rankings', FighterRankingViewSet)
router.register(r'statistics', FighterStatisticsViewSet)
router.register(r'ranking-history', RankingHistoryViewSet)

# Content endpoints
router.register(r'categories', CategoryViewSet)
router.register(r'tags', TagViewSet)
router.register(r'articles', ArticleViewSet)
router.register(r'article-fighters', ArticleFighterViewSet)
router.register(r'article-events', ArticleEventViewSet)
router.register(r'article-organizations', ArticleOrganizationViewSet)

urlpatterns = [
    # Include all router URLs
    path('', include(router.urls)),
]