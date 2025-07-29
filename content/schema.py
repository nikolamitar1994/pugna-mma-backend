"""
Schema.org structured data generation for SEO optimization.

This module provides functions to generate JSON-LD structured data
for articles, organizations, people, and events according to Schema.org standards.
"""

import json
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from typing import Dict, List, Optional, Any


class SchemaGenerator:
    """
    Generate Schema.org structured data for various content types.
    """
    
    def __init__(self, request=None):
        """Initialize with optional request object for absolute URLs."""
        self.request = request
        self.site_url = self._get_site_url()
    
    def _get_site_url(self) -> str:
        """Get the base site URL."""
        if self.request:
            return f"{self.request.scheme}://{self.request.get_host()}"
        return getattr(settings, 'SITE_URL', 'https://mmadatabase.com')
    
    def _get_absolute_url(self, path: str) -> str:
        """Convert relative path to absolute URL."""
        return f"{self.site_url}{path}"
    
    def generate_article_schema(self, article) -> Dict[str, Any]:
        """
        Generate Schema.org Article or NewsArticle structured data.
        
        Args:
            article: Article model instance
            
        Returns:
            Dictionary containing Schema.org JSON-LD data
        """
        # Determine schema type based on article type
        schema_type = self._get_article_schema_type(article.article_type)
        
        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "headline": article.title,
            "description": article.get_seo_description(),
            "url": self._get_absolute_url(article.get_absolute_url()),
            "datePublished": article.published_at.isoformat() if article.published_at else None,
            "dateModified": article.updated_at.isoformat(),
            "wordCount": self._calculate_word_count(article.content),
            "timeRequired": f"PT{article.reading_time}M",  # ISO 8601 duration format
            "inLanguage": "en-US",
        }
        
        # Author information
        if article.author:
            schema["author"] = self._generate_person_schema(article.author)
        
        # Publisher information
        schema["publisher"] = self._generate_organization_schema()
        
        # Main entity (what the article is about)
        main_entity = self._get_article_main_entity(article)
        if main_entity:
            schema["mainEntity"] = main_entity
        
        # Featured image
        if article.featured_image:
            schema["image"] = self._generate_image_schema(article)
        
        # Category and tags
        keywords = []
        if article.category:
            keywords.append(article.category.name)
        keywords.extend([tag.name for tag in article.tags.all()])
        
        if keywords:
            schema["keywords"] = keywords
        
        # Article section/category
        if article.category:
            schema["articleSection"] = article.category.name
        
        # Related entities (fighters, events, organizations)
        mentions = self._get_article_mentions(article)
        if mentions:
            schema["mentions"] = mentions
        
        # Remove None values
        return {k: v for k, v in schema.items() if v is not None}
    
    def generate_person_schema(self, fighter) -> Dict[str, Any]:
        """
        Generate Schema.org Person structured data for fighters.
        
        Args:
            fighter: Fighter model instance
            
        Returns:
            Dictionary containing Schema.org Person data
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": fighter.get_full_name(),
            "url": self._get_absolute_url(fighter.get_absolute_url()),
            "jobTitle": "Mixed Martial Arts Fighter",
            "description": f"Professional MMA fighter with a record of {fighter.wins}-{fighter.losses}-{fighter.draws}",
        }
        
        # Additional names
        if fighter.nickname:
            schema["alternateName"] = fighter.nickname
        
        # Birth information
        if fighter.date_of_birth:
            schema["birthDate"] = fighter.date_of_birth.isoformat()
        
        if fighter.birth_place:
            schema["birthPlace"] = {
                "@type": "Place",
                "name": fighter.birth_place
            }
        
        # Nationality
        if fighter.nationality:
            schema["nationality"] = {
                "@type": "Country",
                "name": fighter.nationality
            }
        
        # Physical attributes
        if fighter.height_cm:
            schema["height"] = {
                "@type": "QuantitativeValue",
                "value": fighter.height_cm,
                "unitCode": "CMT"
            }
        
        if fighter.weight_kg:
            schema["weight"] = {
                "@type": "QuantitativeValue", 
                "value": fighter.weight_kg,
                "unitCode": "KGM"
            }
        
        # Professional information
        if fighter.gym:
            schema["worksFor"] = {
                "@type": "Organization",
                "name": fighter.gym
            }
        
        # Image
        if hasattr(fighter, 'image') and fighter.image:
            schema["image"] = self._get_absolute_url(fighter.image.url)
        
        # Awards/achievements (could be added based on rankings)
        awards = self._get_fighter_awards(fighter)
        if awards:
            schema["award"] = awards
        
        return {k: v for k, v in schema.items() if v is not None}
    
    def generate_sports_event_schema(self, event) -> Dict[str, Any]:
        """
        Generate Schema.org SportsEvent structured data for MMA events.
        
        Args:
            event: Event model instance
            
        Returns:
            Dictionary containing Schema.org SportsEvent data
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            "name": event.name,
            "description": f"Mixed Martial Arts event organized by {event.organization.name}",
            "url": self._get_absolute_url(event.get_absolute_url()),
            "startDate": event.date.isoformat(),
            "sport": "Mixed Martial Arts",
        }
        
        # Location
        if event.venue and event.location:
            schema["location"] = {
                "@type": "Place",
                "name": event.venue,
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": event.location
                }
            }
        
        # Organizer
        if event.organization:
            schema["organizer"] = {
                "@type": "Organization",
                "name": event.organization.name,
                "url": self._get_absolute_url(event.organization.get_absolute_url()) if hasattr(event.organization, 'get_absolute_url') else None
            }
        
        # Competitors (main event fighters)
        competitors = self._get_event_main_competitors(event)
        if competitors:
            schema["competitor"] = competitors
        
        # Event status
        if event.date > timezone.now().date():
            schema["eventStatus"] = "https://schema.org/EventScheduled"
        else:
            schema["eventStatus"] = "https://schema.org/EventPostponed"  # Could be more specific
        
        return {k: v for k, v in schema.items() if v is not None}
    
    def generate_organization_schema(self, organization=None) -> Dict[str, Any]:
        """
        Generate Schema.org Organization structured data.
        
        Args:
            organization: Organization model instance (optional, defaults to site org)
            
        Returns:
            Dictionary containing Schema.org Organization data
        """
        if organization:
            return {
                "@type": "Organization",
                "name": organization.name,
                "url": self._get_absolute_url(organization.get_absolute_url()) if hasattr(organization, 'get_absolute_url') else None,
                "description": getattr(organization, 'description', f"{organization.name} - Mixed Martial Arts Organization"),
            }
        else:
            # Default to site organization (publisher)
            return {
                "@type": "Organization",
                "name": "MMA Database",
                "url": self.site_url,
                "description": "Comprehensive Mixed Martial Arts Database and News Platform",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{self.site_url}/static/images/logo.png",
                    "width": 200,
                    "height": 200
                }
            }
    
    def generate_breadcrumb_schema(self, breadcrumbs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate Schema.org BreadcrumbList structured data.
        
        Args:
            breadcrumbs: List of {"name": "Page Name", "url": "/page/url/"} dictionaries
            
        Returns:
            Dictionary containing Schema.org BreadcrumbList data
        """
        breadcrumb_items = []
        
        for i, crumb in enumerate(breadcrumbs, 1):
            breadcrumb_items.append({
                "@type": "ListItem",
                "position": i,
                "name": crumb["name"],
                "item": self._get_absolute_url(crumb["url"])
            })
        
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": breadcrumb_items
        }
    
    def _get_article_schema_type(self, article_type: str) -> str:
        """Determine the appropriate Schema.org type for an article."""
        type_mapping = {
            'news': 'NewsArticle',
            'analysis': 'Article',
            'interview': 'Article',
            'preview': 'Article', 
            'recap': 'Article',
            'profile': 'ProfilePage',
            'ranking': 'Article',
            'technical': 'Article',
        }
        return type_mapping.get(article_type, 'Article')
    
    def _generate_person_schema(self, user) -> Dict[str, Any]:
        """Generate basic person schema for article authors."""
        return {
            "@type": "Person",
            "name": user.get_full_name() or user.username,
            "url": f"{self.site_url}/author/{user.username}/" if hasattr(user, 'username') else None
        }
    
    def _generate_image_schema(self, article) -> Dict[str, Any]:
        """Generate image schema for article featured images."""
        return {
            "@type": "ImageObject",
            "url": self._get_absolute_url(article.featured_image.url),
            "caption": article.featured_image_caption or article.title,
            "description": article.featured_image_alt or article.title
        }
    
    def _calculate_word_count(self, content: str) -> int:
        """Calculate approximate word count from HTML content."""
        import re
        # Remove HTML tags and count words
        plain_text = re.sub(r'<[^>]+>', '', content)
        return len(plain_text.split())
    
    def _get_article_main_entity(self, article) -> Optional[Dict[str, Any]]:
        """Get the main entity that the article is about."""
        # Check for primary fighter relationship
        primary_fighter = article.fighter_relationships.filter(
            relationship_type__in=['about', 'interview', 'profile']
        ).first()
        
        if primary_fighter:
            return {
                "@type": "Person",
                "name": primary_fighter.fighter.get_full_name(),
                "url": self._get_absolute_url(primary_fighter.fighter.get_absolute_url())
            }
        
        # Check for primary event relationship
        primary_event = article.event_relationships.filter(
            relationship_type__in=['preview', 'recap', 'coverage']
        ).first()
        
        if primary_event:
            return {
                "@type": "SportsEvent",
                "name": primary_event.event.name,
                "url": self._get_absolute_url(primary_event.event.get_absolute_url())
            }
        
        return None
    
    def _get_article_mentions(self, article) -> List[Dict[str, Any]]:
        """Get entities mentioned in the article."""
        mentions = []
        
        # Add mentioned fighters
        for fighter_rel in article.fighter_relationships.filter(relationship_type='mentions'):
            mentions.append({
                "@type": "Person",
                "name": fighter_rel.fighter.get_full_name(),
                "url": self._get_absolute_url(fighter_rel.fighter.get_absolute_url())
            })
        
        # Add mentioned events
        for event_rel in article.event_relationships.filter(relationship_type='mentions'):
            mentions.append({
                "@type": "SportsEvent", 
                "name": event_rel.event.name,
                "url": self._get_absolute_url(event_rel.event.get_absolute_url())
            })
        
        # Add mentioned organizations
        for org_rel in article.organization_relationships.filter(relationship_type='mentions'):
            mentions.append({
                "@type": "Organization",
                "name": org_rel.organization.name,
                "url": self._get_absolute_url(org_rel.organization.get_absolute_url()) if hasattr(org_rel.organization, 'get_absolute_url') else None
            })
        
        return mentions
    
    def _get_fighter_awards(self, fighter) -> List[str]:
        """Get fighter awards/achievements."""
        awards = []
        
        # Check for championship status (would need to be implemented)
        # if hasattr(fighter, 'is_champion') and fighter.is_champion:
        #     awards.append("Champion")
        
        # Check for notable rankings
        # if hasattr(fighter, 'current_ranking') and fighter.current_ranking <= 5:
        #     awards.append(f"Top {fighter.current_ranking} Ranked Fighter")
        
        return awards
    
    def _get_event_main_competitors(self, event) -> List[Dict[str, Any]]:
        """Get main event competitors."""
        competitors = []
        
        # Get main event fight
        main_fight = getattr(event, 'fights', None)
        if main_fight:
            main_fight = main_fight.filter(is_main_event=True).first()
            if main_fight:
                # Add competitors from main fight
                for participant in main_fight.participants.all():
                    competitors.append({
                        "@type": "Person",
                        "name": participant.fighter.get_full_name(),
                        "url": self._get_absolute_url(participant.fighter.get_absolute_url())
                    })
        
        return competitors


def generate_schema_json(schema_data: Dict[str, Any]) -> str:
    """
    Convert schema dictionary to JSON-LD string for HTML embedding.
    
    Args:
        schema_data: Schema.org data dictionary
        
    Returns:
        JSON-LD string ready for HTML <script> tag
    """
    return json.dumps(schema_data, indent=2, ensure_ascii=False)


def get_article_schema_json(article, request=None) -> str:
    """
    Convenience function to get article schema as JSON string.
    
    Args:
        article: Article model instance
        request: Django request object (optional)
        
    Returns:
        JSON-LD string for the article
    """
    generator = SchemaGenerator(request)
    schema = generator.generate_article_schema(article)
    return generate_schema_json(schema)


def get_fighter_schema_json(fighter, request=None) -> str:
    """
    Convenience function to get fighter schema as JSON string.
    
    Args:
        fighter: Fighter model instance
        request: Django request object (optional)
        
    Returns:
        JSON-LD string for the fighter
    """
    generator = SchemaGenerator(request)
    schema = generator.generate_person_schema(fighter)
    return generate_schema_json(schema)


def get_event_schema_json(event, request=None) -> str:
    """
    Convenience function to get event schema as JSON string.
    
    Args:
        event: Event model instance
        request: Django request object (optional)
        
    Returns:
        JSON-LD string for the event
    """
    generator = SchemaGenerator(request)
    schema = generator.generate_sports_event_schema(event)
    return generate_schema_json(schema)