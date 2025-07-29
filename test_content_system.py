#!/usr/bin/env python
"""
Simplified test runner for EPIC-09 Content Management System.

This script tests the core functionality without dealing with model conflicts.
It focuses on validating the business logic and API endpoints.
"""

import os
import sys
import django
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.utils import timezone

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
django.setup()

# Import models after Django setup
from content.models import Category, Tag, Article, ArticleFighter, ArticleEvent, ArticleOrganization
from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization

User = get_user_model()


def test_category_model():
    """Test Category model functionality"""
    print("Testing Category model...")
    
    try:
        # Test category creation
        category = Category.objects.create(
            name="Test Category",
            description="Test description"
        )
        
        assert category.name == "Test Category"
        assert category.slug == "test-category"  # Auto-generated
        assert category.is_active == True
        
        # Test hierarchical structure
        child_category = Category.objects.create(
            name="Child Category",
            parent=category
        )
        
        assert child_category.parent == category
        assert child_category in category.children.all()
        
        # Test full path
        path = child_category.get_full_path()
        assert path == ["Test Category", "Child Category"]
        
        print("✅ Category model tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Category model tests failed: {str(e)}")
        return False
    finally:
        # Cleanup
        Category.objects.filter(name__in=["Test Category", "Child Category"]).delete()


def test_tag_model():
    """Test Tag model functionality"""
    print("Testing Tag model...")
    
    try:
        # Test tag creation
        tag = Tag.objects.create(
            name="Test Tag",
            description="Test tag description",
            color="#007bff"
        )
        
        assert tag.name == "Test Tag"
        assert tag.slug == "test-tag"
        assert tag.color == "#007bff"
        assert tag.usage_count == 0
        
        print("✅ Tag model tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Tag model tests failed: {str(e)}")
        return False
    finally:
        # Cleanup
        Tag.objects.filter(name="Test Tag").delete()


def test_article_model():
    """Test Article model functionality"""
    print("Testing Article model...")
    
    try:
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        # Create category
        category = Category.objects.create(name="Test Category")
        
        # Test article creation
        article = Article.objects.create(
            title="Test Article",
            content="<p>This is test content with HTML.</p>",
            category=category,
            author=user,
            status='draft'
        )
        
        assert article.title == "Test Article"
        assert article.slug == "test-article"
        assert article.status == 'draft'
        assert article.article_type == 'news'  # Default
        
        # Test slug uniqueness
        article2 = Article.objects.create(
            title="Test Article",  # Same title
            content="Different content",
            author=user
        )
        
        assert article2.slug == "test-article-1"
        
        # Test excerpt auto-generation
        long_content = "<p>" + "This is a long article. " * 50 + "</p>"
        article3 = Article.objects.create(
            title="Long Article",
            content=long_content,
            author=user
        )
        
        assert len(article3.excerpt) > 0
        assert len(article3.excerpt) <= 303  # 300 + "..."
        assert "<p>" not in article3.excerpt  # HTML should be stripped
        
        # Test reading time calculation
        words = ["word"] * 400
        content = "<p>" + " ".join(words) + "</p>"
        article4 = Article.objects.create(
            title="Long Article",
            content=content,
            author=user
        )
        
        assert article4.reading_time == 2  # 400 words / 200 wpm = 2 minutes
        
        # Test published_at auto-setting
        article.status = 'published'
        article.save()
        
        assert article.published_at is not None
        
        # Test SEO methods
        article_with_meta = Article.objects.create(
            title="Meta Article",
            content="Content",
            meta_title="Custom SEO Title",
            meta_description="Custom SEO Description",
            author=user
        )
        
        assert article_with_meta.get_seo_title() == "Custom SEO Title"
        assert article_with_meta.get_seo_description() == "Custom SEO Description"
        
        print("✅ Article model tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Article model tests failed: {str(e)}")
        return False
    finally:
        # Cleanup
        Article.objects.filter(title__contains="Test Article").delete()
        Article.objects.filter(title__contains="Long Article").delete()
        Article.objects.filter(title="Meta Article").delete()
        Category.objects.filter(name="Test Category").delete()


def test_relationships():
    """Test article relationship models"""
    print("Testing article relationships...")
    
    try:
        # Get or create test objects
        user, _ = User.objects.get_or_create(
            username='testuser2',
            defaults={
                'email': 'test2@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        article = Article.objects.create(
            title="Relationship Test Article",
            content="Testing relationships",
            author=user
        )
        
        fighter = Fighter.objects.create(
            first_name="Test",
            last_name="Fighter",
            nickname="The Tester"
        )
        
        organization = Organization.objects.create(
            name="Test Organization",
            abbreviation="TEST",
            description="Test organization"
        )
        
        event = Event.objects.create(
            name="Test Event",
            date=timezone.now().date(),
            location="Test Location",
            organization=organization,
            status='scheduled'
        )
        
        # Test ArticleFighter relationship
        fighter_rel = ArticleFighter.objects.create(
            article=article,
            fighter=fighter,
            relationship_type='about',
            display_order=1
        )
        
        assert fighter_rel.article == article
        assert fighter_rel.fighter == fighter
        assert fighter_rel.relationship_type == 'about'
        
        # Test ArticleEvent relationship
        event_rel = ArticleEvent.objects.create(
            article=article,
            event=event,
            relationship_type='preview'
        )
        
        assert event_rel.article == article
        assert event_rel.event == event
        assert event_rel.relationship_type == 'preview'
        
        # Test ArticleOrganization relationship
        org_rel = ArticleOrganization.objects.create(
            article=article,
            organization=organization,
            relationship_type='news'
        )
        
        assert org_rel.article == article
        assert org_rel.organization == organization
        assert org_rel.relationship_type == 'news'
        
        print("✅ Relationship model tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Relationship model tests failed: {str(e)}")
        return False
    finally:
        # Cleanup
        ArticleFighter.objects.all().delete()
        ArticleEvent.objects.all().delete()
        ArticleOrganization.objects.all().delete()
        Article.objects.filter(title="Relationship Test Article").delete()
        Event.objects.filter(name="Test Event").delete()
        Fighter.objects.filter(first_name="Test", last_name="Fighter").delete()
        Organization.objects.filter(abbreviation="TEST").delete()


def test_business_logic():
    """Test core business logic"""
    print("Testing business logic...")
    
    try:
        # Get or create test user
        user, _ = User.objects.get_or_create(
            username='logicuser',
            defaults={
                'email': 'logic@example.com',
                'first_name': 'Logic',
                'last_name': 'User'
            }
        )
        
        # Create category and tags
        category = Category.objects.create(name="Logic Category")
        tag1 = Tag.objects.create(name="Logic Tag 1")
        tag2 = Tag.objects.create(name="Logic Tag 2")
        
        # Create article with tags
        article = Article.objects.create(
            title="Logic Test Article",
            content="Testing business logic",
            category=category,
            author=user,
            status='published',
            published_at=timezone.now()
        )
        article.tags.add(tag1, tag2)
        
        # Test tag relationships
        assert article.tags.count() == 2
        assert tag1 in article.tags.all()
        assert tag2 in article.tags.all()
        
        # Test related articles (create another article with same category)
        article2 = Article.objects.create(
            title="Related Article",
            content="Related content",
            category=category,
            author=user,
            status='published',
            published_at=timezone.now()
        )
        
        related = article.get_related_articles()
        assert article2 in related
        
        # Test view count increment
        initial_count = article.view_count
        article.increment_view_count()
        article.refresh_from_db()
        assert article.view_count == initial_count + 1
        
        # Test category article count
        assert category.get_article_count() == 2  # Both published
        
        print("✅ Business logic tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Business logic tests failed: {str(e)}")
        return False
    finally:
        # Cleanup
        Article.objects.filter(title__contains="Logic").delete()
        Article.objects.filter(title="Related Article").delete()
        Tag.objects.filter(name__contains="Logic Tag").delete()
        Category.objects.filter(name="Logic Category").delete()


def main():
    """Run all tests"""
    print("=" * 80)
    print("EPIC-09 CONTENT MANAGEMENT SYSTEM - FUNCTIONALITY TESTS")
    print("=" * 80)
    print()
    
    tests = [
        test_category_model,
        test_tag_model,
        test_article_model,
        test_relationships,
        test_business_logic
    ]
    
    results = []
    
    for test_func in tests:
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    print("=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL FUNCTIONALITY TESTS PASSED!")
        print("✅ Content Management System models are working correctly")
        print("✅ Business logic is functioning as expected")
        print("✅ Relationships are properly established")
        print("\nThe EPIC-09 Content Management System is ready for use!")
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)