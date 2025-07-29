"""
Test data creation utilities for comprehensive content testing.

This module provides utilities to create realistic test data for all aspects
of the content management system including sample articles, categories, tags,
relationships, and users with proper roles.
"""

import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from fighters.models import Fighter
from events.models import Event
from organizations.models import Organization
from content.models import (
    Category, Tag, Article, ArticleFighter, ArticleEvent, 
    ArticleOrganization, ArticleView
)

User = get_user_model()


class ContentTestDataFactory:
    """Factory class for creating comprehensive test data"""
    
    def __init__(self):
        """Initialize the factory"""
        self.users = {}
        self.groups = {}
        self.categories = {}
        self.tags = {}
        self.fighters = {}
        self.organizations = {}
        self.events = {}
        self.articles = {}
        
    def create_all_test_data(self):
        """Create complete test data set"""
        print("Creating comprehensive test data...")
        
        # Create in dependency order
        self.create_user_groups()
        self.create_test_users()
        self.create_organizations()
        self.create_fighters()
        self.create_events()
        self.create_categories()
        self.create_tags()
        self.create_articles()
        self.create_relationships()
        self.create_analytics_data()
        
        print("Test data creation completed!")
        return self.get_summary()
        
    def create_user_groups(self):
        """Create editorial user groups with permissions"""
        groups_data = [
            {
                'name': 'Editorial Admin',
                'permissions': [
                    'add_article', 'change_article', 'delete_article', 'view_article',
                    'add_category', 'change_category', 'delete_category', 'view_category',
                    'add_tag', 'change_tag', 'delete_tag', 'view_tag',
                ]
            },
            {
                'name': 'Editorial Editor',
                'permissions': [
                    'add_article', 'change_article', 'view_article',
                    'view_category', 'view_tag',
                ]
            },
            {
                'name': 'Editorial Author',
                'permissions': [
                    'add_article', 'change_article', 'view_article',
                    'view_category', 'view_tag',
                ]
            }
        ]
        
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            self.groups[group_data['name']] = group
            
            if created:
                print(f"Created group: {group.name}")
        
    def create_test_users(self):
        """Create users with different roles"""
        users_data = [
            {
                'username': 'admin_user',
                'email': 'admin@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'group': 'Editorial Admin'
            },
            {
                'username': 'editor_john',
                'email': 'john.editor@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'John',
                'last_name': 'Editor',
                'is_staff': True,
                'group': 'Editorial Editor'
            },
            {
                'username': 'editor_sarah',
                'email': 'sarah.editor@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'Sarah',
                'last_name': 'Wilson',
                'is_staff': True,
                'group': 'Editorial Editor'
            },
            {
                'username': 'author_mike',
                'email': 'mike.author@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'Mike',
                'last_name': 'Thompson',
                'is_staff': True,
                'group': 'Editorial Author'
            },
            {
                'username': 'author_lisa',
                'email': 'lisa.author@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'Lisa',
                'last_name': 'Rodriguez',
                'is_staff': True,
                'group': 'Editorial Author'
            },
            {
                'username': 'author_david',
                'email': 'david.author@mmadatabase.com',
                'password': 'testpass123',
                'first_name': 'David',
                'last_name': 'Chen',
                'is_staff': True,
                'group': 'Editorial Author'
            }
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_staff': user_data['is_staff'],
                    'is_superuser': user_data.get('is_superuser', False)
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                print(f"Created user: {user.username}")
                
            # Add to group
            if user_data['group'] in self.groups:
                user.groups.add(self.groups[user_data['group']])
                
            self.users[user_data['username']] = user
            
    def create_organizations(self):
        """Create test organizations"""
        orgs_data = [
            {
                'name': 'Ultimate Fighting Championship',
                'abbreviation': 'UFC',
                'description': 'Premier mixed martial arts organization',
                'website': 'https://ufc.com',
                'founded_year': 1993,
                'headquarters': 'Las Vegas, Nevada, USA'
            },
            {
                'name': 'Professional Fighters League',
                'abbreviation': 'PFL',
                'description': 'Season-based MMA organization',
                'website': 'https://pflmma.com',
                'founded_year': 2017,
                'headquarters': 'New York, New York, USA'
            },
            {
                'name': 'Konfrontacja Sztuk Walki',
                'abbreviation': 'KSW',
                'description': 'European MMA organization',
                'website': 'https://ksw.pl',
                'founded_year': 2004,
                'headquarters': 'Warsaw, Poland'
            }
        ]
        
        for org_data in orgs_data:
            org, created = Organization.objects.get_or_create(
                abbreviation=org_data['abbreviation'],
                defaults=org_data
            )
            
            if created:
                print(f"Created organization: {org.name}")
                
            self.organizations[org_data['abbreviation']] = org
            
    def create_fighters(self):
        """Create test fighters"""
        fighters_data = [
            {
                'first_name': 'Jon',
                'last_name': 'Jones',
                'nickname': 'Bones',
                'nationality': 'USA',
                'date_of_birth': '1987-07-19',
                'wins': 26,
                'losses': 1,
                'draws': 0,
                'height_cm': 193,
                'weight_kg': 93,
                'reach_cm': 213
            },
            {
                'first_name': 'Daniel',
                'last_name': 'Cormier',
                'nickname': 'DC',
                'nationality': 'USA',
                'date_of_birth': '1979-03-20',
                'wins': 22,
                'losses': 3,
                'draws': 1,
                'height_cm': 180,
                'weight_kg': 93,
                'reach_cm': 183
            },
            {
                'first_name': 'Anderson',
                'last_name': 'Silva',
                'nickname': 'The Spider',
                'nationality': 'Brazil',
                'date_of_birth': '1975-04-14',
                'wins': 34,
                'losses': 11,
                'draws': 0,
                'height_cm': 188,
                'weight_kg': 84,
                'reach_cm': 196
            },
            {
                'first_name': 'Conor',
                'last_name': 'McGregor',
                'nickname': 'The Notorious',
                'nationality': 'Ireland',
                'date_of_birth': '1988-07-14',
                'wins': 22,
                'losses': 6,
                'draws': 0,
                'height_cm': 175,
                'weight_kg': 70,
                'reach_cm': 188
            },
            {
                'first_name': 'Khabib',
                'last_name': 'Nurmagomedov',
                'nickname': 'The Eagle',
                'nationality': 'Russia',
                'date_of_birth': '1988-09-20',
                'wins': 29,
                'losses': 0,
                'draws': 0,
                'height_cm': 178,
                'weight_kg': 70,
                'reach_cm': 178
            },
            {
                'first_name': 'Amanda',
                'last_name': 'Nunes',
                'nickname': 'The Lioness',
                'nationality': 'Brazil',
                'date_of_birth': '1988-05-30',
                'wins': 22,
                'losses': 5,
                'draws': 0,
                'height_cm': 173,
                'weight_kg': 61,
                'reach_cm': 175
            }
        ]
        
        for fighter_data in fighters_data:
            # Convert date string to date object
            if 'date_of_birth' in fighter_data:
                fighter_data['date_of_birth'] = datetime.strptime(
                    fighter_data['date_of_birth'], '%Y-%m-%d'
                ).date()
            
            fighter, created = Fighter.objects.get_or_create(
                first_name=fighter_data['first_name'],
                last_name=fighter_data['last_name'],
                defaults=fighter_data
            )
            
            if created:
                print(f"Created fighter: {fighter.get_full_name()}")
                
            key = f"{fighter_data['first_name']}_{fighter_data['last_name']}"
            self.fighters[key] = fighter
            
    def create_events(self):
        """Create test events"""
        events_data = [
            {
                'name': 'UFC 300: Historic Night',
                'date': timezone.now().date() + timedelta(days=30),
                'location': 'Las Vegas, Nevada',
                'venue': 'T-Mobile Arena',
                'organization': 'UFC',
                'status': 'scheduled'
            },
            {
                'name': 'UFC 299: Championship Night',
                'date': timezone.now().date() - timedelta(days=7),
                'location': 'Miami, Florida',
                'venue': 'Kaseya Center',
                'organization': 'UFC',
                'status': 'completed'
            },
            {
                'name': 'UFC 298: Title Defenses',
                'date': timezone.now().date() - timedelta(days=21),
                'location': 'Anaheim, California',
                'venue': 'Honda Center',
                'organization': 'UFC',
                'status': 'completed'
            },
            {
                'name': 'PFL Championship 2024',
                'date': timezone.now().date() + timedelta(days=60),
                'location': 'New York, New York',
                'venue': 'Madison Square Garden',
                'organization': 'PFL',
                'status': 'scheduled'
            }
        ]
        
        for event_data in events_data:
            org = self.organizations.get(event_data.pop('organization'))
            
            event, created = Event.objects.get_or_create(
                name=event_data['name'],
                defaults={**event_data, 'organization': org}
            )
            
            if created:
                print(f"Created event: {event.name}")
                
            self.events[event_data['name']] = event
            
    def create_categories(self):
        """Create content categories"""
        categories_data = [
            {
                'name': 'News',
                'description': 'Latest MMA news and updates',
                'meta_title': 'MMA News - Latest Updates',
                'meta_description': 'Stay updated with the latest MMA news'
            },
            {
                'name': 'Fight Analysis',
                'description': 'In-depth fight breakdowns and analysis',
                'parent': 'News'
            },
            {
                'name': 'Fighter Profiles',
                'description': 'Comprehensive fighter profiles and interviews',
                'meta_title': 'Fighter Profiles - MMA Database',
                'meta_description': 'Complete profiles of MMA fighters'
            },
            {
                'name': 'Event Previews',
                'description': 'Upcoming event previews and predictions'
            },
            {
                'name': 'Event Recaps',
                'description': 'Post-event analysis and results'
            },
            {
                'name': 'Rankings',
                'description': 'Fighter rankings and pound-for-pound lists'
            },
            {
                'name': 'Technique',
                'description': 'Technical analysis and martial arts instruction'
            },
            {
                'name': 'Industry News',
                'description': 'MMA business and industry updates'
            }
        ]
        
        # Create parent categories first
        for cat_data in categories_data:
            if 'parent' not in cat_data:
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={k: v for k, v in cat_data.items() if k != 'parent'}
                )
                
                if created:
                    print(f"Created category: {category.name}")
                    
                self.categories[cat_data['name']] = category
                
        # Create child categories
        for cat_data in categories_data:
            if 'parent' in cat_data:
                parent = self.categories.get(cat_data['parent'])
                
                category, created = Category.objects.get_or_create(
                    name=cat_data['name'],
                    defaults={
                        **{k: v for k, v in cat_data.items() if k not in ['parent']},
                        'parent': parent
                    }
                )
                
                if created:
                    print(f"Created child category: {category.name}")
                    
                self.categories[cat_data['name']] = category
                
    def create_tags(self):
        """Create content tags"""
        tags_data = [
            {'name': 'UFC', 'color': '#dc3545', 'description': 'Ultimate Fighting Championship'},
            {'name': 'PFL', 'color': '#007bff', 'description': 'Professional Fighters League'},
            {'name': 'KSW', 'color': '#28a745', 'description': 'Konfrontacja Sztuk Walki'},
            {'name': 'Lightweight', 'color': '#ffc107', 'description': 'Lightweight division'},
            {'name': 'Welterweight', 'color': '#6f42c1', 'description': 'Welterweight division'},
            {'name': 'Middleweight', 'color': '#fd7e14', 'description': 'Middleweight division'},
            {'name': 'Light Heavyweight', 'color': '#20c997', 'description': 'Light heavyweight division'},
            {'name': 'Heavyweight', 'color': '#6c757d', 'description': 'Heavyweight division'},
            {'name': 'Title Fight', 'color': '#dc3545', 'description': 'Championship fights'},
            {'name': 'Main Event', 'color': '#007bff', 'description': 'Main event fights'},
            {'name': 'Knockout', 'color': '#dc3545', 'description': 'Knockout finishes'},
            {'name': 'Submission', 'color': '#28a745', 'description': 'Submission finishes'},
            {'name': 'Decision', 'color': '#6c757d', 'description': 'Decision victories'},
            {'name': 'Breaking News', 'color': '#dc3545', 'description': 'Breaking news stories'},
            {'name': 'Interview', 'color': '#007bff', 'description': 'Fighter interviews'},
        ]
        
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_data['name'],
                defaults=tag_data
            )
            
            if created:
                print(f"Created tag: {tag.name}")
                
            self.tags[tag_data['name']] = tag
            
    def create_articles(self):
        """Create sample articles with different statuses and types"""
        articles_data = [
            {
                'title': 'Jon Jones Returns: Championship Legacy Continues',
                'content': self._get_sample_content('jones_legacy'),
                'excerpt': 'Jon Jones prepares for his next title defense in what could be a historic night.',
                'category': 'Fighter Profiles',
                'tags': ['UFC', 'Light Heavyweight', 'Title Fight'],
                'author': 'author_mike',
                'status': 'published',
                'article_type': 'profile',
                'is_featured': True,
                'published_days_ago': 2
            },
            {
                'title': 'UFC 300 Preview: Historic Card Breakdown',
                'content': self._get_sample_content('ufc300_preview'),
                'excerpt': 'Complete breakdown of the historic UFC 300 card featuring multiple title fights.',
                'category': 'Event Previews',
                'tags': ['UFC', 'UFC 300', 'Title Fight', 'Main Event'],
                'author': 'author_lisa',
                'status': 'published',
                'article_type': 'preview',
                'is_breaking': True,
                'published_days_ago': 1
            },
            {
                'title': 'Anderson Silva: The Greatest Middleweight Ever?',
                'content': self._get_sample_content('silva_analysis'),
                'excerpt': 'Analyzing Anderson Silva\'s incredible middleweight title reign and legacy.',
                'category': 'Fight Analysis',
                'tags': ['UFC', 'Middleweight', 'GOAT'],
                'author': 'author_david',
                'status': 'published',
                'article_type': 'analysis',
                'published_days_ago': 5
            },
            {
                'title': 'Conor McGregor Training Camp Update',
                'content': self._get_sample_content('mcgregor_camp'),
                'excerpt': 'Latest updates from Conor McGregor\'s training camp ahead of his return.',
                'category': 'News',
                'tags': ['UFC', 'Lightweight', 'Breaking News'],
                'author': 'author_mike',
                'status': 'review',
                'article_type': 'news'
            },
            {
                'title': 'Khabib Nurmagomedov Retirement Analysis',
                'content': self._get_sample_content('khabib_retirement'),
                'excerpt': 'Examining Khabib\'s perfect record and reasons for early retirement.',
                'category': 'Fighter Profiles',
                'tags': ['UFC', 'Lightweight', 'Retirement'],
                'author': 'author_lisa',
                'status': 'draft',
                'article_type': 'analysis'
            },
            {
                'title': 'Amanda Nunes: Double Champion Dominance',
                'content': self._get_sample_content('nunes_dominance'),
                'excerpt': 'How Amanda Nunes became the most dominant female fighter in MMA history.',
                'category': 'Fighter Profiles',
                'tags': ['UFC', 'Women\'s MMA', 'Champion'],
                'author': 'author_david',
                'status': 'published',
                'article_type': 'profile',
                'published_days_ago': 10
            },
            {
                'title': 'PFL Season Format: Innovation in MMA',
                'content': self._get_sample_content('pfl_format'),
                'excerpt': 'How PFL\'s season-based format is changing the MMA landscape.',
                'category': 'Industry News',
                'tags': ['PFL', 'Innovation', 'Tournament'],
                'author': 'author_mike',
                'status': 'published',
                'article_type': 'news',
                'published_days_ago': 3
            },
            {
                'title': 'European MMA: KSW\'s Rising Influence',
                'content': self._get_sample_content('ksw_influence'),
                'excerpt': 'Examining how KSW has become Europe\'s premier MMA organization.',
                'category': 'Industry News',
                'tags': ['KSW', 'European MMA', 'Growth'],
                'author': 'author_lisa',
                'status': 'published',
                'article_type': 'analysis',
                'published_days_ago': 7
            }
        ]
        
        for article_data in articles_data:
            # Get category and author
            category = self.categories.get(article_data['category'])
            author = self.users.get(article_data['author'])
            
            # Calculate published date
            published_at = None
            if article_data['status'] == 'published' and 'published_days_ago' in article_data:
                published_at = timezone.now() - timedelta(days=article_data['published_days_ago'])
            
            # Create article
            article, created = Article.objects.get_or_create(
                title=article_data['title'],
                defaults={
                    'content': article_data['content'],
                    'excerpt': article_data['excerpt'],
                    'category': category,
                    'author': author,
                    'status': article_data['status'],
                    'article_type': article_data['article_type'],
                    'is_featured': article_data.get('is_featured', False),
                    'is_breaking': article_data.get('is_breaking', False),
                    'published_at': published_at,
                    'view_count': random.randint(50, 5000)
                }
            )
            
            if created:
                # Add tags
                for tag_name in article_data['tags']:
                    if tag_name in self.tags:
                        article.tags.add(self.tags[tag_name])
                
                print(f"Created article: {article.title}")
                
            self.articles[article_data['title']] = article
            
    def create_relationships(self):
        """Create article-fighter and article-event relationships"""
        relationships_data = [
            {
                'article': 'Jon Jones Returns: Championship Legacy Continues',
                'fighter': 'Jon_Jones',
                'relationship_type': 'about'
            },
            {
                'article': 'Anderson Silva: The Greatest Middleweight Ever?',
                'fighter': 'Anderson_Silva',
                'relationship_type': 'about'
            },
            {
                'article': 'Conor McGregor Training Camp Update',
                'fighter': 'Conor_McGregor',
                'relationship_type': 'features'
            },
            {
                'article': 'Khabib Nurmagomedov Retirement Analysis',
                'fighter': 'Khabib_Nurmagomedov',
                'relationship_type': 'about'
            },
            {
                'article': 'Amanda Nunes: Double Champion Dominance',
                'fighter': 'Amanda_Nunes',
                'relationship_type': 'about'
            },
            {
                'article': 'UFC 300 Preview: Historic Card Breakdown',
                'event': 'UFC 300: Historic Night',
                'relationship_type': 'preview'
            }
        ]
        
        for rel_data in relationships_data:
            article = self.articles.get(rel_data['article'])
            
            if 'fighter' in rel_data:
                fighter = self.fighters.get(rel_data['fighter'])
                if article and fighter:
                    ArticleFighter.objects.get_or_create(
                        article=article,
                        fighter=fighter,
                        defaults={'relationship_type': rel_data['relationship_type']}
                    )
                    
            elif 'event' in rel_data:
                event = self.events.get(rel_data['event'])
                if article and event:
                    ArticleEvent.objects.get_or_create(
                        article=article,
                        event=event,
                        defaults={'relationship_type': rel_data['relationship_type']}
                    )
                    
    def create_analytics_data(self):
        """Create analytics and view tracking data"""
        # Create article views for popular articles
        popular_articles = [
            article for article in self.articles.values() 
            if article.status == 'published'
        ]
        
        for article in popular_articles[:5]:  # Top 5 articles
            # Create multiple views
            for i in range(random.randint(10, 50)):
                ArticleView.objects.create(
                    article=article,
                    ip_address=f"192.168.1.{random.randint(1, 255)}",
                    user_agent="Test Browser",
                    viewed_at=timezone.now() - timedelta(
                        hours=random.randint(1, 72)
                    )
                )
        
        print("Created analytics data")
        
    def _get_sample_content(self, content_type):
        """Get sample content based on type"""
        contents = {
            'jones_legacy': """
            <h2>The Undisputed Champion</h2>
            <p>Jon Jones has long been considered one of the greatest mixed martial artists of all time. With a record that speaks for itself, Jones has dominated the light heavyweight division for over a decade.</p>
            
            <h3>Career Highlights</h3>
            <ul>
                <li>Youngest UFC champion in history</li>
                <li>Most title defenses in light heavyweight division</li>
                <li>Victories over multiple Hall of Fame fighters</li>
            </ul>
            
            <p>As Jones prepares for his next challenge, fans around the world are eager to see if he can add another chapter to his legendary career.</p>
            """,
            
            'ufc300_preview': """
            <h2>A Historic Night in Las Vegas</h2>
            <p>UFC 300 promises to be one of the most significant events in the organization's history. With multiple title fights on the card, this event has something for every MMA fan.</p>
            
            <h3>Main Card Highlights</h3>
            <p>The main event features a highly anticipated championship bout that has been years in the making. Both fighters are at the peak of their careers and have everything to prove.</p>
            
            <h3>What to Expect</h3>
            <p>Expect fireworks from the very first fight. The preliminary card is stacked with rising contenders and established veterans looking to make a statement.</p>
            """,
            
            'silva_analysis': """
            <h2>The Spider's Web</h2>
            <p>Anderson Silva's reign as middleweight champion was nothing short of spectacular. For over six years, Silva defended his title with a combination of precision, creativity, and devastating power that the division had never seen before.</p>
            
            <h3>Technical Mastery</h3>
            <p>Silva's striking was poetry in motion. His ability to counter-attack while moving backward, his precise timing, and his creative combinations set him apart from every other fighter in the division.</p>
            
            <h3>Legacy Questions</h3>
            <p>While Silva's achievements are undeniable, the question remains: is he the greatest middleweight of all time? The numbers certainly suggest so.</p>
            """,
            
            'mcgregor_camp': """
            <h2>The Notorious Returns</h2>
            <p>Reports from Conor McGregor's training camp suggest the former two-division champion is in the best shape of his career. Sources close to the team indicate that McGregor has been working on specific aspects of his game.</p>
            
            <h3>Training Focus</h3>
            <p>This camp has emphasized wrestling and grappling defense, areas that have been identified as crucial for McGregor's success in his upcoming bout.</p>
            """,
            
            'khabib_retirement': """
            <h2>The Eagle's Final Flight</h2>
            <p>Khabib Nurmagomedov's retirement at the peak of his career shocked the MMA world. With a perfect 29-0 record, Khabib walked away from the sport as the undisputed lightweight champion.</p>
            
            <h3>Unparalleled Dominance</h3>
            <p>Throughout his career, Khabib's grappling was simply on another level. His ability to control fights and dominate opponents was unlike anything the lightweight division had ever seen.</p>
            """,
            
            'nunes_dominance': """
            <h2>The Lioness Roars</h2>
            <p>Amanda Nunes has established herself as the greatest female fighter in MMA history. Her victories over every top contender in two divisions have cemented her legacy.</p>
            
            <h3>Two-Division Champion</h3>
            <p>Holding titles in both the bantamweight and featherweight divisions, Nunes has proven she can compete and dominate at multiple weight classes.</p>
            """,
            
            'pfl_format': """
            <h2>Revolutionary Tournament Format</h2>
            <p>The Professional Fighters League has introduced a unique season-based format that sets it apart from other MMA organizations. This innovative approach has attracted both fighters and fans.</p>
            
            <h3>How It Works</h3>
            <p>The PFL season consists of regular season fights, playoffs, and championship bouts, with winners taking home substantial prize money.</p>
            """,
            
            'ksw_influence': """
            <h2>European MMA Powerhouse</h2>
            <p>Konfrontacja Sztuk Walki (KSW) has grown from a regional Polish organization to become Europe's premier MMA promotion. Their events regularly sell out large venues and attract international attention.</p>
            
            <h3>Building Stars</h3>
            <p>KSW has been instrumental in developing European MMA talent and providing a platform for fighters to showcase their skills on a global stage.</p>
            """
        }
        
        return contents.get(content_type, "<p>Sample content for testing purposes.</p>")
        
    def get_summary(self):
        """Get summary of created test data"""
        return {
            'users': len(self.users),
            'groups': len(self.groups),
            'organizations': len(self.organizations),
            'fighters': len(self.fighters),
            'events': len(self.events),
            'categories': len(self.categories),
            'tags': len(self.tags),
            'articles': len(self.articles),
            'relationships': ArticleFighter.objects.count() + ArticleEvent.objects.count(),
            'article_views': ArticleView.objects.count()
        }


def create_comprehensive_test_data():
    """Convenience function to create all test data"""
    factory = ContentTestDataFactory()
    return factory.create_all_test_data()


def cleanup_test_data():
    """Clean up all test data"""
    print("Cleaning up test data...")
    
    # Delete in reverse dependency order
    ArticleView.objects.all().delete()
    ArticleFighter.objects.all().delete()
    ArticleEvent.objects.all().delete()
    ArticleOrganization.objects.all().delete()
    Article.objects.all().delete()
    Tag.objects.all().delete()
    Category.objects.all().delete()
    Event.objects.all().delete()
    Fighter.objects.all().delete()
    Organization.objects.all().delete()
    
    # Delete users (except admin)
    User.objects.filter(is_superuser=False).delete()
    Group.objects.all().delete()
    
    print("Test data cleanup completed!")


if __name__ == '__main__':
    # This allows the script to be run directly
    import django
    import os
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings.development')
    django.setup()
    
    summary = create_comprehensive_test_data()
    print("\nTest Data Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")