"""
AI-assisted data completion service for fighter profiles.
Integrates with external AI services to suggest data completion.
"""

import json
import requests
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from ..models import PendingFighter, Fighter
from ..templates import JSONTemplateGenerator, JSONImportProcessor


class AICompletionService:
    """
    Service for AI-assisted data completion of fighter profiles.
    Provides integration points for external AI services.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'AI_COMPLETION_API_KEY', None)
        self.api_url = getattr(settings, 'AI_COMPLETION_API_URL', None)
        self.cache_timeout = 3600  # 1 hour
    
    def complete_pending_fighter(self, pending_fighter: PendingFighter) -> Dict[str, Any]:
        """
        Complete fighter data using AI assistance.
        
        Args:
            pending_fighter: PendingFighter instance to complete
            
        Returns:
            Dictionary with completion results and suggested data
        """
        # Generate input template for AI
        template = self.generate_completion_prompt(pending_fighter)
        
        # Call AI service (placeholder implementation)
        ai_suggestions = self.call_ai_service(template)
        
        # Process and validate AI response
        validated_suggestions = self.validate_ai_suggestions(ai_suggestions, pending_fighter)
        
        # Update pending fighter with AI suggestions
        pending_fighter.ai_suggested_data = validated_suggestions
        pending_fighter.save()
        
        return {
            'success': True,
            'suggestions': validated_suggestions,
            'confidence_score': validated_suggestions.get('completion_confidence', 0.0),
            'fields_completed': self.count_completed_fields(validated_suggestions)
        }
    
    def generate_completion_prompt(self, pending_fighter: PendingFighter) -> Dict[str, Any]:
        """
        Generate structured prompt for AI completion service.
        """
        prompt_data = {
            'task': 'complete_fighter_profile',
            'context': {
                'fighter_name': pending_fighter.full_name_raw,
                'first_name': pending_fighter.first_name,
                'last_name': pending_fighter.last_name,
                'nickname': pending_fighter.nickname,
                'nationality': pending_fighter.nationality,
                'weight_class': pending_fighter.weight_class_name,
                'record_text': pending_fighter.record_text,
                'source_event': pending_fighter.source_event.name if pending_fighter.source_event else None,
                'source_url': pending_fighter.source_url,
                'source_data': pending_fighter.source_data
            },
            'required_fields': [
                'date_of_birth', 'birth_place', 'height_cm', 'weight_kg', 
                'reach_cm', 'stance', 'fighting_out_of', 'team'
            ],
            'instructions': [
                'Research the fighter using available information',
                'Provide accurate biographical and physical data',
                'Include confidence scores for each field',
                'Cite sources where possible',
                'Flag any uncertain information'
            ],
            'output_format': {
                'fighter_data': {
                    'date_of_birth': 'YYYY-MM-DD or null',
                    'birth_place': 'City, Country or empty string',
                    'height_cm': 'integer or null',
                    'weight_kg': 'decimal or null',
                    'reach_cm': 'integer or null',
                    'stance': 'orthodox|southpaw|switch or empty',
                    'fighting_out_of': 'Location or empty string',
                    'team': 'Team name or empty string',
                    'wikipedia_url': 'URL or empty string',
                    'profile_image_url': 'URL or empty string'
                },
                'confidence_scores': {
                    'field_name': 'confidence_0_to_1'
                },
                'sources': ['list', 'of', 'sources'],
                'completion_confidence': 'overall_confidence_0_to_1',
                'notes': 'Additional notes or warnings'
            }
        }
        
        return prompt_data
    
    def call_ai_service(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call external AI service for data completion.
        This is a placeholder implementation.
        """
        # Check cache first
        cache_key = f"ai_completion_{hash(json.dumps(prompt_data, sort_keys=True))}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # In a real implementation, this would call an actual AI service
        if self.api_key and self.api_url:
            try:
                response = requests.post(
                    self.api_url,
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    json=prompt_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    cache.set(cache_key, result, self.cache_timeout)
                    return result
                else:
                    return self.generate_fallback_suggestions(prompt_data)
                    
            except requests.RequestException:
                return self.generate_fallback_suggestions(prompt_data)
        
        # Fallback: return mock suggestions for development
        return self.generate_mock_suggestions(prompt_data)
    
    def generate_mock_suggestions(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock AI suggestions for development/testing.
        """
        context = prompt_data.get('context', {})
        fighter_name = context.get('fighter_name', '')
        
        # Create realistic but fictional suggestions
        mock_suggestions = {
            'fighter_data': {
                'date_of_birth': None,  # Would need real research
                'birth_place': '',
                'height_cm': None,
                'weight_kg': None,
                'reach_cm': None,
                'stance': 'orthodox',  # Most common
                'fighting_out_of': '',
                'team': '',
                'wikipedia_url': '',
                'profile_image_url': ''
            },
            'confidence_scores': {
                'stance': 0.6,  # Conservative guess
                'date_of_birth': 0.0,
                'birth_place': 0.0,
                'height_cm': 0.0,
                'weight_kg': 0.0,
                'reach_cm': 0.0,
                'fighting_out_of': 0.0,
                'team': 0.0
            },
            'sources': ['Mock AI Service - Development Mode'],
            'completion_confidence': 0.3,
            'notes': f'Mock suggestions for {fighter_name}. Real AI service not configured.'
        }
        
        # Add weight class-based weight estimate if available
        weight_class = context.get('weight_class', '').lower()
        if 'lightweight' in weight_class:
            mock_suggestions['fighter_data']['weight_kg'] = 70.0
            mock_suggestions['confidence_scores']['weight_kg'] = 0.5
        elif 'welterweight' in weight_class:
            mock_suggestions['fighter_data']['weight_kg'] = 77.0
            mock_suggestions['confidence_scores']['weight_kg'] = 0.5
        elif 'middleweight' in weight_class:
            mock_suggestions['fighter_data']['weight_kg'] = 84.0
            mock_suggestions['confidence_scores']['weight_kg'] = 0.5
        elif 'heavyweight' in weight_class:
            mock_suggestions['fighter_data']['weight_kg'] = 110.0
            mock_suggestions['confidence_scores']['weight_kg'] = 0.5
        
        return mock_suggestions
    
    def generate_fallback_suggestions(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fallback suggestions when AI service is unavailable.
        """
        return {
            'fighter_data': {},
            'confidence_scores': {},
            'sources': ['Fallback - AI service unavailable'],
            'completion_confidence': 0.0,
            'notes': 'AI completion service unavailable. Manual research required.'
        }
    
    def validate_ai_suggestions(self, ai_suggestions: Dict[str, Any], pending_fighter: PendingFighter) -> Dict[str, Any]:
        """
        Validate and clean AI suggestions before storing.
        """
        validated = {
            'fighter_data': {},
            'confidence_scores': {},
            'sources': [],
            'completion_confidence': 0.0,
            'notes': '',
            'validated_at': timezone.now().isoformat()
        }
        
        # Validate fighter data fields
        fighter_data = ai_suggestions.get('fighter_data', {})
        confidence_scores = ai_suggestions.get('confidence_scores', {})
        
        # Height validation
        height = fighter_data.get('height_cm')
        if height and isinstance(height, (int, float)) and 120 <= height <= 250:
            validated['fighter_data']['height_cm'] = int(height)
            validated['confidence_scores']['height_cm'] = confidence_scores.get('height_cm', 0.0)
        
        # Weight validation
        weight = fighter_data.get('weight_kg')
        if weight and isinstance(weight, (int, float)) and 40 <= weight <= 200:
            validated['fighter_data']['weight_kg'] = float(weight)
            validated['confidence_scores']['weight_kg'] = confidence_scores.get('weight_kg', 0.0)
        
        # Reach validation
        reach = fighter_data.get('reach_cm')
        if reach and isinstance(reach, (int, float)) and 120 <= reach <= 250:
            validated['fighter_data']['reach_cm'] = int(reach)
            validated['confidence_scores']['reach_cm'] = confidence_scores.get('reach_cm', 0.0)
        
        # Stance validation
        stance = fighter_data.get('stance', '').lower()
        if stance in ['orthodox', 'southpaw', 'switch']:
            validated['fighter_data']['stance'] = stance
            validated['confidence_scores']['stance'] = confidence_scores.get('stance', 0.0)
        
        # Date of birth validation
        dob = fighter_data.get('date_of_birth')
        if dob and self.validate_date_format(dob):
            validated['fighter_data']['date_of_birth'] = dob
            validated['confidence_scores']['date_of_birth'] = confidence_scores.get('date_of_birth', 0.0)
        
        # String fields (with length limits)
        string_fields = {
            'birth_place': 255,
            'fighting_out_of': 255,
            'team': 255,
            'wikipedia_url': 500,
            'profile_image_url': 500
        }
        
        for field, max_length in string_fields.items():
            value = fighter_data.get(field, '').strip()
            if value and len(value) <= max_length:
                validated['fighter_data'][field] = value
                validated['confidence_scores'][field] = confidence_scores.get(field, 0.0)
        
        # Copy metadata
        validated['sources'] = ai_suggestions.get('sources', [])
        validated['completion_confidence'] = min(max(ai_suggestions.get('completion_confidence', 0.0), 0.0), 1.0)
        validated['notes'] = ai_suggestions.get('notes', '')
        
        return validated
    
    def validate_date_format(self, date_string: str) -> bool:
        """Validate date string format (YYYY-MM-DD)"""
        try:
            from datetime import datetime
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def count_completed_fields(self, suggestions: Dict[str, Any]) -> int:
        """Count how many fields were completed with suggestions"""
        fighter_data = suggestions.get('fighter_data', {})
        return len([v for v in fighter_data.values() if v is not None and v != ''])
    
    def bulk_complete_pending_fighters(self, pending_fighters: List[PendingFighter]) -> Dict[str, Any]:
        """
        Complete multiple pending fighters in batch.
        """
        results = {
            'total_processed': 0,
            'successful_completions': 0,
            'failed_completions': 0,
            'errors': []
        }
        
        for pending_fighter in pending_fighters:
            try:
                completion_result = self.complete_pending_fighter(pending_fighter)
                results['total_processed'] += 1
                
                if completion_result['success']:
                    results['successful_completions'] += 1
                else:
                    results['failed_completions'] += 1
                    
            except Exception as e:
                results['failed_completions'] += 1
                results['errors'].append({
                    'pending_fighter_id': str(pending_fighter.id),
                    'error': str(e)
                })
        
        return results
    
    def suggest_improvements_for_fighter(self, fighter: Fighter) -> Dict[str, Any]:
        """
        Suggest improvements for existing fighter profiles.
        """
        # Calculate current data completeness
        missing_fields = []
        quality_issues = []
        
        # Check for missing critical fields
        if not fighter.date_of_birth:
            missing_fields.append('date_of_birth')
        if not fighter.height_cm:
            missing_fields.append('height_cm')
        if not fighter.weight_kg:
            missing_fields.append('weight_kg')
        if not fighter.nationality:
            missing_fields.append('nationality')
        if not fighter.stance:
            missing_fields.append('stance')
        
        # Check for quality issues
        if fighter.height_cm and (fighter.height_cm < 150 or fighter.height_cm > 220):
            quality_issues.append('Height seems unrealistic for MMA fighter')
        
        if fighter.reach_cm and fighter.height_cm:
            reach_height_ratio = fighter.reach_cm / fighter.height_cm
            if reach_height_ratio < 0.9 or reach_height_ratio > 1.15:
                quality_issues.append('Reach to height ratio seems unusual')
        
        return {
            'current_quality_score': fighter.data_quality_score,
            'missing_fields': missing_fields,
            'quality_issues': quality_issues,
            'improvement_priority': 'high' if len(missing_fields) > 3 else 'medium' if missing_fields else 'low',
            'suggestions': self.generate_improvement_suggestions(fighter, missing_fields)
        }
    
    def generate_improvement_suggestions(self, fighter: Fighter, missing_fields: List[str]) -> List[Dict[str, Any]]:
        """Generate specific improvement suggestions for a fighter"""
        suggestions = []
        
        if 'date_of_birth' in missing_fields:
            suggestions.append({
                'field': 'date_of_birth',
                'suggestion': 'Research fighter\'s birth date from official sources or interviews',
                'priority': 'high',
                'data_sources': ['Wikipedia', 'UFC.com', 'Official fighter websites', 'MMA databases']
            })
        
        if 'height_cm' in missing_fields or 'weight_kg' in missing_fields or 'reach_cm' in missing_fields:
            suggestions.append({
                'field': 'physical_stats',
                'suggestion': 'Look up official fight statistics or pre-fight measurements',
                'priority': 'high',
                'data_sources': ['UFCStats.com', 'Official event records', 'Broadcast graphics']
            })
        
        if not fighter.wikipedia_url:
            suggestions.append({
                'field': 'wikipedia_url',
                'suggestion': 'Search for Wikipedia page and verify information accuracy',
                'priority': 'medium',
                'data_sources': ['Wikipedia search']
            })
        
        return suggestions


# Singleton instance
ai_completion_service = AICompletionService()