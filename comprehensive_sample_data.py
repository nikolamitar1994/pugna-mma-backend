#!/usr/bin/env python3
"""
Comprehensive Sample Data Creator for MMA Backend
Creates realistic sample data across all Django models for admin panel testing
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from organizations.models import Organization, WeightClass
from fighters.models import Fighter, FightHistory, FighterRanking, FighterStatistics
from events.models import Event, Fight
from content.models import Category, Tag, Article, ArticleFighter, ArticleEvent, ArticleOrganization
from users.models import UserProfile, EditorialWorkflowLog, AssignmentNotification

User = get_user_model()

def create_organizations():
    """Create major MMA organizations"""
    orgs_data = [
        {
            'name': 'Ultimate Fighting Championship',
            'abbreviation': 'UFC',
            'founded_date': date(1993, 11, 12),
            'headquarters': 'Las Vegas, Nevada, USA',
            'website': 'https://www.ufc.com',
            'is_active': True
        },
        {
            'name': 'Konfrontacja Sztuk Walki',
            'abbreviation': 'KSW',
            'founded_date': date(2004, 5, 1),
            'headquarters': 'Warsaw, Poland',
            'website': 'https://www.ksw.pl',
            'is_active': True
        },
        {
            'name': 'Oktagon MMA',
            'abbreviation': 'OKTAGON',
            'founded_date': date(2016, 1, 1),
            'headquarters': 'Prague, Czech Republic',
            'website': 'https://www.oktagonmma.com',
            'is_active': True
        },
        {
            'name': 'Professional Fighters League',
            'abbreviation': 'PFL',
            'founded_date': date(2017, 12, 31),
            'headquarters': 'New York, USA',
            'website': 'https://www.pflmma.com',
            'is_active': True
        },
        {
            'name': 'ONE Championship',
            'abbreviation': 'ONE',
            'founded_date': date(2011, 7, 14),
            'headquarters': 'Singapore',
            'website': 'https://www.onefc.com',
            'is_active': True
        }
    ]
    
    organizations = []
    for org_data in orgs_data:
        org, created = Organization.objects.get_or_create(
            name=org_data['name'],
            defaults=org_data
        )
        organizations.append(org)
        if created:
            print(f"Created organization: {org.name}")
    
    return organizations

def create_weight_classes(organizations):
    """Create weight classes for organizations"""
    ufc = organizations[0]  # UFC
    ksw = organizations[1]  # KSW
    
    weight_classes_data = [
        # UFC Men's divisions
        {'name': 'Flyweight', 'weight_limit_lbs': 125, 'gender': 'male', 'org': ufc},
        {'name': 'Bantamweight', 'weight_limit_lbs': 135, 'gender': 'male', 'org': ufc},
        {'name': 'Featherweight', 'weight_limit_lbs': 145, 'gender': 'male', 'org': ufc},
        {'name': 'Lightweight', 'weight_limit_lbs': 155, 'gender': 'male', 'org': ufc},
        {'name': 'Welterweight', 'weight_limit_lbs': 170, 'gender': 'male', 'org': ufc},
        {'name': 'Middleweight', 'weight_limit_lbs': 185, 'gender': 'male', 'org': ufc},
        {'name': 'Light Heavyweight', 'weight_limit_lbs': 205, 'gender': 'male', 'org': ufc},
        {'name': 'Heavyweight', 'weight_limit_lbs': 265, 'gender': 'male', 'org': ufc},
        
        # UFC Women's divisions
        {'name': 'Strawweight', 'weight_limit_lbs': 115, 'gender': 'female', 'org': ufc},
        {'name': 'Flyweight', 'weight_limit_lbs': 125, 'gender': 'female', 'org': ufc},
        {'name': 'Bantamweight', 'weight_limit_lbs': 135, 'gender': 'female', 'org': ufc},
        {'name': 'Featherweight', 'weight_limit_lbs': 145, 'gender': 'female', 'org': ufc},
        
        # KSW divisions
        {'name': 'Lightweight', 'weight_limit_lbs': 155, 'gender': 'male', 'org': ksw},
        {'name': 'Welterweight', 'weight_limit_lbs': 170, 'gender': 'male', 'org': ksw},
        {'name': 'Middleweight', 'weight_limit_lbs': 185, 'gender': 'male', 'org': ksw},
        {'name': 'Heavyweight', 'weight_limit_lbs': 265, 'gender': 'male', 'org': ksw},
    ]
    
    weight_classes = []
    for wc_data in weight_classes_data:
        org = wc_data.pop('org')
        wc_data['organization'] = org
        wc_data['weight_limit_kg'] = round(wc_data['weight_limit_lbs'] * 0.453592, 1)
        
        wc, created = WeightClass.objects.get_or_create(
            name=wc_data['name'],
            gender=wc_data['gender'],
            organization=org,
            defaults=wc_data
        )
        weight_classes.append(wc)
        if created:
            print(f"Created weight class: {wc.name} ({wc.gender}) - {org.abbreviation}")
    
    return weight_classes

def create_fighters():
    """Create diverse roster of fighters"""
    fighters_data = [
        # Current UFC Champions and Stars
        {
            'first_name': 'Islam', 'last_name': 'Makhachev', 'nickname': '',
            'nationality': 'Russian', 'date_of_birth': date(1991, 9, 27),
            'height_cm': 180, 'weight_kg': Decimal('70.0'), 'reach_cm': 178,
            'stance': 'orthodox', 'team': 'Eagles MMA', 'fighting_out_of': 'Makhachkala, Russia',
            'wins': 25, 'losses': 1, 'draws': 0, 'wins_by_submission': 11, 'wins_by_ko': 4, 'wins_by_decision': 10
        },
        {
            'first_name': 'Alexander', 'last_name': 'Volkanovski', 'nickname': 'The Great',
            'nationality': 'Australian', 'date_of_birth': date(1988, 9, 29),
            'height_cm': 168, 'weight_kg': Decimal('66.0'), 'reach_cm': 171,
            'stance': 'orthodox', 'team': 'Freestyle Fighting Gym', 'fighting_out_of': 'Windang, Australia',
            'wins': 26, 'losses': 3, 'draws': 0, 'wins_by_ko': 12, 'wins_by_decision': 14
        },
        {
            'first_name': 'Israel', 'last_name': 'Adesanya', 'nickname': 'The Last Stylebender',
            'nationality': 'New Zealand', 'date_of_birth': date(1989, 7, 22),
            'height_cm': 193, 'weight_kg': Decimal('84.0'), 'reach_cm': 203,
            'stance': 'orthodox', 'team': 'City Kickboxing', 'fighting_out_of': 'Auckland, New Zealand',
            'wins': 24, 'losses': 3, 'draws': 0, 'wins_by_ko': 15, 'wins_by_decision': 9
        },
        {
            'first_name': 'Francis', 'last_name': 'Ngannou', 'nickname': 'The Predator',
            'nationality': 'Cameroonian', 'date_of_birth': date(1986, 9, 5),
            'height_cm': 193, 'weight_kg': Decimal('118.0'), 'reach_cm': 211,
            'stance': 'orthodox', 'team': 'MMA Factory', 'fighting_out_of': 'Paris, France',
            'wins': 17, 'losses': 3, 'draws': 0, 'wins_by_ko': 12, 'wins_by_decision': 5
        },
        {
            'first_name': 'Valentina', 'last_name': 'Shevchenko', 'nickname': 'Bullet',
            'nationality': 'Kyrgyzstani', 'date_of_birth': date(1988, 3, 7),
            'height_cm': 165, 'weight_kg': Decimal('57.0'), 'reach_cm': 167,
            'stance': 'orthodox', 'team': 'Tiger Muay Thai', 'fighting_out_of': 'Las Vegas, Nevada',
            'wins': 23, 'losses': 4, 'draws': 0, 'wins_by_ko': 8, 'wins_by_submission': 7, 'wins_by_decision': 8
        },
        {
            'first_name': 'Rose', 'last_name': 'Namajunas', 'nickname': 'Thug',
            'nationality': 'American', 'date_of_birth': date(1992, 6, 29),
            'height_cm': 165, 'weight_kg': Decimal('52.0'), 'reach_cm': 165,
            'stance': 'orthodox', 'team': 'Trevor Wittman ONX Sports', 'fighting_out_of': 'Denver, Colorado',
            'wins': 12, 'losses': 6, 'draws': 0, 'wins_by_ko': 3, 'wins_by_submission': 5, 'wins_by_decision': 4
        },
        # European fighters for KSW/Oktagon
        {
            'first_name': 'Mateusz', 'last_name': 'Gamrot', 'nickname': 'Gamer',
            'nationality': 'Polish', 'date_of_birth': date(1991, 12, 11),
            'height_cm': 175, 'weight_kg': Decimal('70.3'), 'reach_cm': 183,
            'stance': 'orthodox', 'team': 'American Top Team', 'fighting_out_of': 'Sanford, Florida',
            'wins': 24, 'losses': 2, 'draws': 1, 'wins_by_ko': 6, 'wins_by_submission': 12, 'wins_by_decision': 6
        },
        {
            'first_name': 'Jiří', 'last_name': 'Procházka', 'nickname': 'BJP',
            'nationality': 'Czech', 'date_of_birth': date(1992, 7, 14),
            'height_cm': 193, 'weight_kg': Decimal('93.0'), 'reach_cm': 203,
            'stance': 'orthodox', 'team': 'Penta Gym', 'fighting_out_of': 'Hostěradice, Czech Republic',
            'wins': 29, 'losses': 4, 'draws': 1, 'wins_by_ko': 25, 'wins_by_submission': 2, 'wins_by_decision': 2
        },
        # Asian fighters for ONE Championship
        {
            'first_name': 'Chatri', 'last_name': 'Sityodtong', 'nickname': 'The Chairman',
            'nationality': 'Thai', 'date_of_birth': date(1971, 8, 18),
            'height_cm': 170, 'weight_kg': Decimal('70.0'), 'reach_cm': 172,
            'stance': 'orthodox', 'team': 'Evolve MMA', 'fighting_out_of': 'Singapore',
            'wins': 15, 'losses': 3, 'draws': 0, 'wins_by_ko': 8, 'wins_by_submission': 4, 'wins_by_decision': 3
        },
        # Legends and retired fighters
        {
            'first_name': 'Fedor', 'last_name': 'Emelianenko', 'nickname': 'The Last Emperor',
            'nationality': 'Russian', 'date_of_birth': date(1976, 9, 28),
            'height_cm': 183, 'weight_kg': Decimal('106.0'), 'reach_cm': 185,
            'stance': 'orthodox', 'team': 'Red Devil Sport Club', 'fighting_out_of': 'Stary Oskol, Russia',
            'wins': 40, 'losses': 6, 'draws': 1, 'wins_by_ko': 15, 'wins_by_submission': 16, 'wins_by_decision': 9, 'is_active': False
        }
    ]
    
    fighters = []
    for fighter_data in fighters_data:
        # Set defaults
        fighter_data.setdefault('data_source', 'manual')
        fighter_data.setdefault('data_quality_score', Decimal('0.85'))
        fighter_data.setdefault('is_active', True)
        fighter_data.setdefault('total_fights', fighter_data['wins'] + fighter_data['losses'] + fighter_data.get('draws', 0))
        
        # Create or get fighter
        fighter, created = Fighter.objects.get_or_create(
            first_name=fighter_data['first_name'],
            last_name=fighter_data['last_name'],
            defaults=fighter_data
        )
        fighters.append(fighter)
        if created:
            print(f"Created fighter: {fighter.first_name} {fighter.last_name}")
    
    return fighters

def create_events(organizations):
    """Create major MMA events"""
    ufc = organizations[0]
    ksw = organizations[1]
    oktagon = organizations[2]
    
    events_data = [
        # Recent UFC events
        {
            'name': 'UFC 292', 'organization': ufc, 'date': date(2023, 8, 19),
            'location': 'Boston, Massachusetts, USA', 'venue': 'TD Garden',
            'city': 'Boston', 'state': 'Massachusetts', 'country': 'USA',
            'attendance': 19580, 'status': 'completed'
        },
        {
            'name': 'UFC 291', 'organization': ufc, 'date': date(2023, 7, 29),
            'location': 'Salt Lake City, Utah, USA', 'venue': 'Delta Center',
            'city': 'Salt Lake City', 'state': 'Utah', 'country': 'USA',
            'attendance': 18537, 'status': 'completed'
        },
        {
            'name': 'UFC 290', 'organization': ufc, 'date': date(2023, 7, 8),
            'location': 'Las Vegas, Nevada, USA', 'venue': 'T-Mobile Arena',
            'city': 'Las Vegas', 'state': 'Nevada', 'country': 'USA',
            'attendance': 19365, 'ppv_buys': 850000, 'status': 'completed'
        },
        # KSW Events
        {
            'name': 'KSW 88', 'organization': ksw, 'date': date(2023, 11, 25),
            'location': 'Warsaw, Poland', 'venue': 'COS Torwar',
            'city': 'Warsaw', 'country': 'Poland',
            'attendance': 5000, 'status': 'completed'
        },
        {
            'name': 'KSW 87', 'organization': ksw, 'date': date(2023, 10, 14),
            'location': 'Gdansk, Poland', 'venue': 'Ergo Arena',
            'city': 'Gdansk', 'country': 'Poland',
            'attendance': 8500, 'status': 'completed'
        },
        # Oktagon Events
        {
            'name': 'OKTAGON 49', 'organization': oktagon, 'date': date(2023, 12, 30),
            'location': 'Prague, Czech Republic', 'venue': 'O2 Arena',
            'city': 'Prague', 'country': 'Czech Republic',
            'attendance': 15000, 'status': 'completed'
        }
    ]
    
    events = []
    for event_data in events_data:
        event, created = Event.objects.get_or_create(
            name=event_data['name'],
            organization=event_data['organization'],
            defaults=event_data
        )
        events.append(event)
        if created:
            print(f"Created event: {event.name}")
    
    return events

def create_content_categories():
    """Create content categories for articles"""
    categories_data = [
        {'name': 'News', 'slug': 'news', 'description': 'Latest MMA news and updates'},
        {'name': 'Fight Previews', 'slug': 'fight-previews', 'description': 'Upcoming fight analysis and predictions'},
        {'name': 'Fight Results', 'slug': 'fight-results', 'description': 'Post-fight coverage and results'},
        {'name': 'Fighter Profiles', 'slug': 'fighter-profiles', 'description': 'In-depth fighter features'},
        {'name': 'Interviews', 'slug': 'interviews', 'description': 'Exclusive fighter and industry interviews'},
        {'name': 'Training', 'slug': 'training', 'description': 'Training tips and techniques'},
        {'name': 'Industry News', 'slug': 'industry-news', 'description': 'Business and industry developments'},
        {'name': 'Event Coverage', 'slug': 'event-coverage', 'description': 'Live event coverage and highlights'}
    ]
    
    categories = []
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        categories.append(category)
        if created:
            print(f"Created category: {category.name}")
    
    return categories

def create_tags():
    """Create content tags"""
    tags_data = [
        'UFC', 'KSW', 'Oktagon', 'ONE Championship', 'PFL',
        'Lightweight', 'Welterweight', 'Middleweight', 'Heavyweight',
        'Title Fight', 'Main Event', 'Knockout', 'Submission', 'Decision',
        'Breaking News', 'Exclusive', 'Interview', 'Analysis', 'Preview',
        'European MMA', 'Asian MMA', 'Women\'s MMA', 'Rising Star'
    ]
    
    tags = []
    for tag_name in tags_data:
        tag, created = Tag.objects.get_or_create(
            name=tag_name,
            defaults={'slug': tag_name.lower().replace(' ', '-').replace('\'', '')}
        )
        tags.append(tag)
        if created:
            print(f"Created tag: {tag.name}")
    
    return tags

def create_editorial_users():
    """Create editorial users for workflow demonstration"""
    users_data = [
        {
            'username': 'editor_chief', 'email': 'editor@mma-backend.com',
            'first_name': 'Sarah', 'last_name': 'Editor',
            'is_staff': True, 'password': 'editorial123'
        },
        {
            'username': 'writer_john', 'email': 'john@mma-backend.com',
            'first_name': 'John', 'last_name': 'Writer',
            'is_staff': True, 'password': 'writer123'
        },
        {
            'username': 'reviewer_jane', 'email': 'jane@mma-backend.com',
            'first_name': 'Jane', 'last_name': 'Reviewer',
            'is_staff': True, 'password': 'reviewer123'
        }
    ]
    
    users = []
    for user_data in users_data:
        password = user_data.pop('password')
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults=user_data
        )
        if created:
            user.set_password(password)
            user.save()
            print(f"Created editorial user: {user.first_name} {user.last_name}")
        users.append(user)
    
    return users

def create_articles(categories, tags, fighters, events, users):
    """Create sample articles with various statuses"""
    main_user = users[0] if users else User.objects.first()
    
    articles_data = [
        {
            'title': 'Islam Makhachev Dominates at UFC 294: A New Era for Lightweight Division',
            'slug': 'islam-makhachev-dominates-ufc-294',
            'excerpt': 'Islam Makhachev showcased his elite skills once again, cementing his position as the undisputed lightweight champion.',
            'content': '''Islam Makhachev's performance at UFC 294 was nothing short of spectacular. The Dagestani champion demonstrated why he's considered one of the most complete fighters in the lightweight division.

The fight showcased Makhachev's incredible grappling prowess, but it was his improved striking that caught everyone's attention. Working with his team at Eagles MMA, he has developed into a truly well-rounded champion.

This victory marks another milestone in his remarkable career, and fans are already speculating about his next potential opponents.''',
            'status': 'published',
            'category': categories[0],  # News
            'featured_image': 'https://example.com/makhachev-ufc294.jpg',
            'published_at': timezone.now() - timedelta(days=5)
        },
        {
            'title': 'Volkanovski vs. Topuria: The Featherweight Title Fight We\'ve Been Waiting For',
            'slug': 'volkanovski-vs-topuria-preview',
            'excerpt': 'Alexander Volkanovski faces his toughest challenge yet in rising star Ilia Topuria.',
            'content': '''The featherweight division is heating up as Alexander Volkanovski prepares to defend his title against the undefeated Ilia Topuria.

Volkanovski has been dominant in the division, but Topuria brings a unique set of skills that could pose serious problems for the champion. The Georgian-Spanish fighter has shown incredible knockout power and grappling skills.

This fight represents a changing of the guard potentially, with the veteran champion facing one of the most promising prospects in the sport.''',
            'status': 'published',
            'category': categories[1],  # Fight Previews
            'featured_image': 'https://example.com/volkanovski-topuria.jpg',
            'published_at': timezone.now() - timedelta(days=2)
        },
        {
            'title': 'The Rise of European MMA: KSW and Oktagon Leading the Charge',
            'slug': 'rise-of-european-mma',
            'excerpt': 'European MMA promotions are producing world-class talent and putting on spectacular shows.',
            'content': '''European MMA has never been stronger. Promotions like KSW in Poland and Oktagon in Czech Republic are not just surviving but thriving, producing fighters who compete at the highest levels globally.

The success of fighters like Jiří Procházka and Mateusz Gamrot in the UFC has shown that European training camps and promotions are world-class.

These promotions offer a different style of presentation and have built incredibly loyal fan bases across Europe.''',
            'status': 'published',
            'category': categories[6],  # Industry News
            'featured_image': 'https://example.com/european-mma.jpg',
            'published_at': timezone.now() - timedelta(days=7)
        },
        {
            'title': 'DRAFT: Upcoming UFC 300 Card Analysis',
            'slug': 'ufc-300-card-analysis-draft',
            'excerpt': 'A preliminary look at what could be the card of the century.',
            'content': '''This is a draft article analyzing the potential UFC 300 card...

(Draft content - needs review)''',
            'status': 'draft',
            'category': categories[1],  # Fight Previews
        },
        {
            'title': 'PENDING: Interview with Rising Contender',
            'slug': 'interview-rising-contender-pending',
            'excerpt': 'Exclusive interview with one of MMA\'s most promising prospects.',
            'content': '''Interview content pending approval...''',
            'status': 'pending_review',
            'category': categories[4],  # Interviews
        }
    ]
    
    articles = []
    for i, article_data in enumerate(articles_data):
        article_data['author'] = main_user
        article_data['meta_description'] = article_data['excerpt'][:150]
        
        article, created = Article.objects.get_or_create(
            slug=article_data['slug'],
            defaults=article_data
        )
        
        if created:
            # Add some tags
            relevant_tags = random.sample(tags, random.randint(2, 5))
            article.tags.set(relevant_tags)
            
            print(f"Created article: {article.title}")
        
        articles.append(article)
    
    return articles

def create_article_relationships(articles, fighters, events, organizations):
    """Create relationships between articles and other entities"""
    relationships_created = 0
    
    for article in articles:
        # Randomly associate some articles with fighters
        if random.choice([True, False]):
            fighter = random.choice(fighters)
            ArticleFighter.objects.get_or_create(
                article=article,
                fighter=fighter,
                defaults={'relationship_type': random.choice(['about', 'mentions', 'features', 'interview'])}
            )
            relationships_created += 1
        
        # Randomly associate some articles with events
        if random.choice([True, False]):
            event = random.choice(events)
            ArticleEvent.objects.get_or_create(
                article=article,
                event=event,
                defaults={'relationship_type': random.choice(['preview', 'recap', 'coverage', 'analysis'])}
            )
            relationships_created += 1
        
        # Randomly associate some articles with organizations
        if random.choice([True, False]):
            org = random.choice(organizations)
            ArticleOrganization.objects.get_or_create(
                article=article,
                organization=org,
                defaults={'relationship_type': random.choice(['news', 'announcement', 'analysis', 'mentions'])}
            )
            relationships_created += 1
    
    print(f"Created {relationships_created} article relationships")

def main():
    print("🚀 Creating comprehensive sample data for MMA Backend...")
    print("=" * 60)
    
    # Create organizations and weight classes
    print("\n📋 Creating Organizations...")
    organizations = create_organizations()
    
    print("\n⚖️ Creating Weight Classes...")
    weight_classes = create_weight_classes(organizations)
    
    # Create fighters
    print("\n🥊 Creating Fighters...")
    fighters = create_fighters()
    
    # Create events
    print("\n🎪 Creating Events...")
    events = create_events(organizations)
    
    # Create content system
    print("\n📝 Creating Content Categories...")
    categories = create_content_categories()
    
    print("\n🏷️ Creating Tags...")
    tags = create_tags()
    
    print("\n👥 Creating Editorial Users...")
    editorial_users = create_editorial_users()
    
    print("\n📰 Creating Articles...")
    articles = create_articles(categories, tags, fighters, events, editorial_users)
    
    print("\n🔗 Creating Article Relationships...")
    create_article_relationships(articles, fighters, events, organizations)
    
    print("\n" + "=" * 60)
    print("✅ Sample data creation completed!")
    print("\n📊 Summary:")
    print(f"   • Organizations: {Organization.objects.count()}")
    print(f"   • Weight Classes: {WeightClass.objects.count()}")
    print(f"   • Fighters: {Fighter.objects.count()}")
    print(f"   • Events: {Event.objects.count()}")
    print(f"   • Categories: {Category.objects.count()}")
    print(f"   • Tags: {Tag.objects.count()}")
    print(f"   • Articles: {Article.objects.count()}")
    print(f"   • Users: {User.objects.count()}")
    
    print("\n🌐 You can now explore the Django admin at:")
    print("   http://localhost:8000/admin/")
    print("\n🔑 Login with: nikolamitrovic@example.com / %Mitro%@1994")

if __name__ == '__main__':
    main()