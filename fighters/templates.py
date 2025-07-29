"""
JSON import/export templates for fighters, events, and articles.
Used for AI-assisted data completion and manual import workflows.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder


class JSONTemplateGenerator:
    """Generate JSON templates for different entity types"""
    
    @staticmethod
    def generate_fighter_template(partial_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate JSON template for fighter import/completion.
        
        Args:
            partial_data: Any existing data to pre-populate
            
        Returns:
            Complete fighter template with instructions
        """
        template = {
            "entity_type": "fighter",
            "template_version": "1.0",
            "generation_date": datetime.now().isoformat(),
            "instructions": {
                "purpose": "Complete fighter profile for import into MMA database",
                "required_fields": ["first_name", "last_name"],
                "highly_recommended": ["nationality", "date_of_birth", "height_cm", "weight_kg"],
                "data_sources": [
                    "Official fighter websites",
                    "Wikipedia entries",
                    "UFC/organization profiles", 
                    "MMA databases (Sherdog, etc.)",
                    "Social media profiles"
                ],
                "validation_rules": {
                    "date_of_birth": "YYYY-MM-DD format, must be realistic fighting age",
                    "height_cm": "Integer between 120-250 cm",
                    "weight_kg": "Decimal between 40-200 kg",
                    "reach_cm": "Integer between 120-250 cm, typically close to height",
                    "stance": "One of: orthodox, southpaw, switch",
                    "nationality": "Full country name or ISO code"
                },
                "completion_notes": "Verify all information from multiple sources. Leave unknown fields empty rather than guessing."
            },
            "fighter_data": {
                "personal_info": {
                    "first_name": partial_data.get('first_name', '') if partial_data else '',
                    "last_name": partial_data.get('last_name', '') if partial_data else '',
                    "display_name": partial_data.get('display_name', '') if partial_data else '',
                    "nickname": partial_data.get('nickname', '') if partial_data else '',
                    "birth_first_name": partial_data.get('birth_first_name', '') if partial_data else '',
                    "birth_last_name": partial_data.get('birth_last_name', '') if partial_data else '',
                    "date_of_birth": partial_data.get('date_of_birth', '') if partial_data else '',
                    "birth_place": partial_data.get('birth_place', '') if partial_data else '',
                    "nationality": partial_data.get('nationality', '') if partial_data else ''
                },
                "physical_attributes": {
                    "height_cm": partial_data.get('height_cm', None) if partial_data else None,
                    "weight_kg": partial_data.get('weight_kg', None) if partial_data else None,
                    "reach_cm": partial_data.get('reach_cm', None) if partial_data else None,
                    "stance": partial_data.get('stance', '') if partial_data else ''
                },
                "career_info": {
                    "fighting_out_of": partial_data.get('fighting_out_of', '') if partial_data else '',
                    "team": partial_data.get('team', '') if partial_data else '',
                    "years_active": partial_data.get('years_active', '') if partial_data else '',
                    "is_active": partial_data.get('is_active', True) if partial_data else True
                },
                "media_links": {
                    "profile_image_url": partial_data.get('profile_image_url', '') if partial_data else '',
                    "wikipedia_url": partial_data.get('wikipedia_url', '') if partial_data else '',
                    "social_media": {
                        "instagram": "",
                        "twitter": "",
                        "facebook": "",
                        "tiktok": ""
                    }
                },
                "data_quality": {
                    "data_source": "ai_completion",
                    "completion_confidence": 0.0,
                    "verification_notes": "",
                    "sources_used": []
                }
            },
            "source_context": partial_data.get('source_context', {}) if partial_data else {},
            "ai_suggestions": partial_data.get('ai_suggestions', {}) if partial_data else {}
        }
        
        return template
    
    @staticmethod
    def generate_event_template(partial_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate JSON template for event import/completion.
        """
        template = {
            "entity_type": "event",
            "template_version": "1.0", 
            "generation_date": datetime.now().isoformat(),
            "instructions": {
                "purpose": "Complete event details for import into MMA database",
                "required_fields": ["name", "date", "organization", "location"],
                "highly_recommended": ["venue", "city", "country", "main_event"],
                "data_sources": [
                    "Official organization websites",
                    "Wikipedia event pages",
                    "MMA news sites",
                    "Event posters and promotional materials"
                ],
                "validation_rules": {
                    "date": "YYYY-MM-DD format",
                    "organization": "Must match existing organization in database",
                    "status": "One of: scheduled, live, completed, cancelled, postponed",
                    "attendance": "Integer if known",
                    "gate_revenue": "Decimal amount in USD"
                }
            },
            "event_data": {
                "basic_info": {
                    "name": partial_data.get('name', '') if partial_data else '',
                    "event_number": partial_data.get('event_number', None) if partial_data else None,
                    "date": partial_data.get('date', '') if partial_data else '',
                    "organization": partial_data.get('organization', '') if partial_data else '',
                    "status": partial_data.get('status', 'scheduled') if partial_data else 'scheduled'
                },
                "location_info": {
                    "location": partial_data.get('location', '') if partial_data else '',
                    "venue": partial_data.get('venue', '') if partial_data else '',
                    "city": partial_data.get('city', '') if partial_data else '',
                    "state": partial_data.get('state', '') if partial_data else '',
                    "country": partial_data.get('country', '') if partial_data else ''
                },
                "business_metrics": {
                    "attendance": partial_data.get('attendance', None) if partial_data else None,
                    "gate_revenue": partial_data.get('gate_revenue', None) if partial_data else None,
                    "ppv_buys": partial_data.get('ppv_buys', None) if partial_data else None,
                    "broadcast_info": {
                        "main_broadcaster": "",
                        "ppv_provider": "",
                        "streaming_platforms": [],
                        "international_broadcasters": {}
                    }
                },
                "media": {
                    "poster_url": partial_data.get('poster_url', '') if partial_data else '',
                    "wikipedia_url": partial_data.get('wikipedia_url', '') if partial_data else ''
                },
                "fight_card": {
                    "main_event": {
                        "fighter1": "",
                        "fighter2": "",
                        "weight_class": "",
                        "title_fight": False,
                        "interim_title": False
                    },
                    "co_main_event": {
                        "fighter1": "",
                        "fighter2": "",
                        "weight_class": "",
                        "title_fight": False
                    },
                    "preliminary_fights": [],
                    "early_preliminary_fights": []
                }
            },
            "source_context": partial_data.get('source_context', {}) if partial_data else {},
            "completion_status": {
                "completed_sections": [],
                "pending_verification": [],
                "data_quality_score": 0.0
            }
        }
        
        return template
    
    @staticmethod
    def generate_article_template(partial_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate JSON template for article import/completion.
        """
        template = {
            "entity_type": "article",
            "template_version": "1.0",
            "generation_date": datetime.now().isoformat(),
            "instructions": {
                "purpose": "Complete article content for import into MMA content management system",
                "required_fields": ["title", "content", "category"],
                "highly_recommended": ["summary", "tags", "featured_image", "seo_data"],
                "content_guidelines": [
                    "Use clear, engaging headlines",
                    "Include relevant MMA terminology",
                    "Add fighter/event relationships where appropriate",
                    "Optimize for SEO with meta descriptions",
                    "Include credible sources and references"
                ],
                "seo_requirements": {
                    "title_length": "50-60 characters optimal",
                    "meta_description": "150-160 characters",
                    "slug": "URL-friendly, include main keywords",
                    "tags": "3-8 relevant tags maximum"
                }
            },
            "article_data": {
                "content": {
                    "title": partial_data.get('title', '') if partial_data else '',
                    "slug": partial_data.get('slug', '') if partial_data else '',
                    "summary": partial_data.get('summary', '') if partial_data else '',
                    "content": partial_data.get('content', '') if partial_data else '',
                    "excerpt": partial_data.get('excerpt', '') if partial_data else ''
                },
                "categorization": {
                    "category": partial_data.get('category', '') if partial_data else '',
                    "tags": partial_data.get('tags', []) if partial_data else [],
                    "content_type": partial_data.get('content_type', 'article') if partial_data else 'article'
                },
                "media": {
                    "featured_image": partial_data.get('featured_image', '') if partial_data else '',
                    "featured_image_alt": partial_data.get('featured_image_alt', '') if partial_data else '',
                    "gallery_images": [],
                    "video_embeds": []
                },
                "seo_data": {
                    "meta_title": partial_data.get('meta_title', '') if partial_data else '',
                    "meta_description": partial_data.get('meta_description', '') if partial_data else '',
                    "focus_keyword": partial_data.get('focus_keyword', '') if partial_data else '',
                    "canonical_url": partial_data.get('canonical_url', '') if partial_data else ''
                },
                "publishing": {
                    "status": partial_data.get('status', 'draft') if partial_data else 'draft',
                    "author": partial_data.get('author', '') if partial_data else '',
                    "publish_date": partial_data.get('publish_date', '') if partial_data else '',
                    "is_featured": partial_data.get('is_featured', False) if partial_data else False,
                    "is_breaking_news": partial_data.get('is_breaking_news', False) if partial_data else False
                },
                "relationships": {
                    "related_fighters": [],
                    "related_events": [],
                    "related_organizations": [],
                    "internal_links": [],
                    "external_sources": []
                }
            },
            "editorial_workflow": {
                "completion_checklist": [
                    "Content accuracy verified",
                    "Fighter/event relationships added", 
                    "SEO optimization completed",
                    "Images and media added",
                    "Editorial review completed",
                    "Fact-checking completed"
                ],
                "review_notes": "",
                "editor_assignments": {
                    "content_editor": "",
                    "copy_editor": "",
                    "seo_specialist": "",
                    "fact_checker": ""
                }
            },
            "source_context": partial_data.get('source_context', {}) if partial_data else {}
        }
        
        return template
    
    @staticmethod
    def export_fighter_to_template(fighter) -> Dict[str, Any]:
        """
        Export existing Fighter to JSON template format.
        Useful for creating templates from existing data.
        """
        return JSONTemplateGenerator.generate_fighter_template({
            'first_name': fighter.first_name,
            'last_name': fighter.last_name,
            'display_name': fighter.display_name,
            'nickname': fighter.nickname,
            'birth_first_name': fighter.birth_first_name,
            'birth_last_name': fighter.birth_last_name,
            'date_of_birth': fighter.date_of_birth.isoformat() if fighter.date_of_birth else '',
            'birth_place': fighter.birth_place,
            'nationality': fighter.nationality,
            'height_cm': fighter.height_cm,
            'weight_kg': float(fighter.weight_kg) if fighter.weight_kg else None,
            'reach_cm': fighter.reach_cm,
            'stance': fighter.stance,
            'fighting_out_of': fighter.fighting_out_of,
            'team': fighter.team,
            'years_active': fighter.years_active,
            'is_active': fighter.is_active,
            'profile_image_url': fighter.profile_image_url,
            'wikipedia_url': fighter.wikipedia_url,
            'social_media': fighter.social_media
        })
    
    @staticmethod
    def export_event_to_template(event) -> Dict[str, Any]:
        """Export existing Event to JSON template format"""
        return JSONTemplateGenerator.generate_event_template({
            'name': event.name,
            'event_number': event.event_number,
            'date': event.date.isoformat(),
            'organization': event.organization.name,
            'status': event.status,
            'location': event.location,
            'venue': event.venue,
            'city': event.city,
            'state': event.state,
            'country': event.country,
            'attendance': event.attendance,
            'gate_revenue': float(event.gate_revenue) if event.gate_revenue else None,
            'ppv_buys': event.ppv_buys,
            'poster_url': event.poster_url,
            'wikipedia_url': event.wikipedia_url
        })


class JSONImportProcessor:
    """Process JSON templates for import into Django models"""
    
    @staticmethod
    def process_fighter_template(template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process fighter JSON template and prepare for model creation.
        
        Returns:
            Dictionary ready for Fighter.objects.create()
        """
        fighter_data = template_data.get('fighter_data', {})
        
        # Extract and flatten data for model creation
        model_data = {}
        
        # Personal info
        personal = fighter_data.get('personal_info', {})
        model_data.update({
            'first_name': personal.get('first_name', ''),
            'last_name': personal.get('last_name', ''),
            'display_name': personal.get('display_name', ''),
            'nickname': personal.get('nickname', ''),
            'birth_first_name': personal.get('birth_first_name', ''),
            'birth_last_name': personal.get('birth_last_name', ''),
            'date_of_birth': personal.get('date_of_birth') or None,
            'birth_place': personal.get('birth_place', ''),
            'nationality': personal.get('nationality', '')
        })
        
        # Physical attributes
        physical = fighter_data.get('physical_attributes', {})
        model_data.update({
            'height_cm': physical.get('height_cm'),
            'weight_kg': physical.get('weight_kg'),
            'reach_cm': physical.get('reach_cm'),
            'stance': physical.get('stance', '')
        })
        
        # Career info
        career = fighter_data.get('career_info', {})
        model_data.update({
            'fighting_out_of': career.get('fighting_out_of', ''),
            'team': career.get('team', ''),
            'years_active': career.get('years_active', ''),
            'is_active': career.get('is_active', True)
        })
        
        # Media links
        media = fighter_data.get('media_links', {})
        model_data.update({
            'profile_image_url': media.get('profile_image_url', ''),
            'wikipedia_url': media.get('wikipedia_url', ''),
            'social_media': media.get('social_media', {})
        })
        
        # Data quality
        quality = fighter_data.get('data_quality', {})
        model_data.update({
            'data_source': quality.get('data_source', 'manual')
        })
        
        # Remove empty values to use model defaults
        return {k: v for k, v in model_data.items() if v is not None and v != ''}
    
    @staticmethod
    def validate_fighter_template(template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate fighter template data and return validation results.
        
        Returns:
            Dictionary with validation results and any errors
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'completeness_score': 0.0
        }
        
        fighter_data = template_data.get('fighter_data', {})
        
        # Check required fields
        personal = fighter_data.get('personal_info', {})
        if not personal.get('first_name'):
            validation_result['errors'].append('first_name is required')
            validation_result['is_valid'] = False
        
        # Check data format validity
        if personal.get('date_of_birth'):
            try:
                from datetime import datetime
                # Try parsing the date
                datetime.strptime(personal['date_of_birth'], '%Y-%m-%d')
            except (ValueError, TypeError):
                validation_result['errors'].append('date_of_birth must be in YYYY-MM-DD format')
                validation_result['is_valid'] = False
        
        # Check physical attribute ranges
        physical = fighter_data.get('physical_attributes', {})
        height = physical.get('height_cm')
        if height and (height < 120 or height > 250):
            validation_result['warnings'].append('height_cm outside typical range (120-250)')
        
        weight = physical.get('weight_kg')
        if weight and (weight < 40 or weight > 200):
            validation_result['warnings'].append('weight_kg outside typical range (40-200)')
        
        # Calculate completeness score
        total_fields = 20  # Approximate number of important fields
        completed_fields = 0
        
        for section in fighter_data.values():
            if isinstance(section, dict):
                completed_fields += sum(1 for v in section.values() if v and v != '')
        
        validation_result['completeness_score'] = min(completed_fields / total_fields, 1.0)
        
        return validation_result