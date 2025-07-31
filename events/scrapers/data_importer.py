"""
Data Import Service for UFC Wikipedia Scraper
Handles importing structured UFC event data into Django models
"""
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from events.models import (
    Event, EventNameVariation, Fight, FightParticipant
)
from organizations.models import Organization, WeightClass
from fighters.models import Fighter
from .schemas import UFCEventSchema, FightResultSchema, BonusAwardSchema
from .fighter_service import FighterService

logger = logging.getLogger(__name__)


def clean_text_field(text: str, max_length: int = 255) -> str:
    """Clean and truncate text field to prevent database errors"""
    if not text:
        return ''
    
    # Strip HTML tags
    cleaned = strip_tags(text)
    
    # Remove excessive whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Truncate to max length if needed
    if len(cleaned) > max_length:
        logger.warning(f"Truncating text field from {len(cleaned)} to {max_length} characters: {cleaned[:50]}...")
        cleaned = cleaned[:max_length].strip()
    
    return cleaned


def clean_fight_section(section: str) -> str:
    """Clean fight section name by removing broadcast network suffixes"""
    if not section:
        return ''
    
    # Remove all broadcast network suffixes - more comprehensive patterns
    broadcast_patterns = [
        r'\s*\([^)]*ESPN[^)]*\)',           # Any parentheses containing ESPN
        r'\s*\([^)]*PPV[^)]*\)',            # Any parentheses containing PPV
        r'\s*\([^)]*Fight Pass[^)]*\)',     # Any parentheses containing Fight Pass
        r'\s*\([^)]*Fox[^)]*\)',            # Any parentheses containing Fox
        r'\s*\([^)]*FS1[^)]*\)',            # Any parentheses containing FS1
        r'\s*\([^)]*FX[^)]*\)',             # Any parentheses containing FX
        r'\s*\([^)]*ESPNews[^)]*\)',        # Any parentheses containing ESPNews
        r'\s*\([^)]*ESPN2[^)]*\)',          # Any parentheses containing ESPN2
        r'\s*\([^)]*Spike[^)]*\)',          # Any parentheses containing Spike
        r'\s*\([^)]*Versus[^)]*\)',         # Any parentheses containing Versus
        r'\s*\([^)]*WEC[^)]*\)',            # Any parentheses containing WEC
        r'\s*\([^)]*UFC TV[^)]*\)',         # Any parentheses containing UFC TV
    ]
    
    cleaned = section.strip()
    for pattern in broadcast_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up any remaining whitespace and trailing commas
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r',\s*$', '', cleaned)  # Remove trailing commas
    
    return cleaned


class DataImporter:
    """Service for importing UFC Wikipedia data into Django models"""
    
    def __init__(self, dry_run: bool = False, update_existing: bool = True):
        """
        Initialize data importer
        
        Args:
            dry_run: If True, don't save data to database
            update_existing: If True, update existing events
        """
        self.dry_run = dry_run
        self.update_existing = update_existing
        self.fighter_service = FighterService()
        
        # Get or create UFC organization
        self.ufc_org = self._get_or_create_ufc()
        
        # Import statistics
        self.stats = {
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fights_created': 0,
            'participants_created': 0,
            'bonus_awards_created': 0,
            'errors': []
        }
    
    def _get_or_create_ufc(self) -> Organization:
        """Get or create UFC organization"""
        try:
            ufc, created = Organization.objects.get_or_create(
                abbreviation='UFC',
                defaults={
                    'name': 'Ultimate Fighting Championship',
                    'founded_date': '1993-11-12',
                    'headquarters': 'Las Vegas, Nevada, USA',
                    'website': 'https://www.ufc.com',
                    'is_active': True
                }
            )
            
            if created:
                logger.info("Created UFC organization")
            
            return ufc
            
        except Exception as e:
            logger.error(f"Error getting/creating UFC organization: {e}")
            raise
    
    def import_ufc_event(self, ufc_event_data: UFCEventSchema) -> Dict[str, Any]:
        """
        Import a single UFC event into the database
        
        Args:
            ufc_event_data: Structured UFC event data from Gemini
            
        Returns:
            Import result with statistics and created objects
        """
        result = {
            'success': False,
            'event': None,
            'fights': [],
            'statistics': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            logger.info(f"Importing UFC event: {ufc_event_data.event.name}")
            
            if self.dry_run:
                logger.info("DRY RUN MODE - No data will be saved")
            
            with transaction.atomic():
                # Step 1: Import event
                event, event_created = self._import_event(ufc_event_data.event)
                result['event'] = event
                
                if event_created:
                    self.stats['events_created'] += 1
                    logger.info(f"✅ Created event: {event.name}")
                elif self.update_existing:
                    self.stats['events_updated'] += 1
                    logger.info(f"🔄 Updated event: {event.name}")
                else:
                    self.stats['events_skipped'] += 1
                    logger.info(f"⏭️ Skipped existing event: {event.name}")
                    result['warnings'].append("Event already exists and update_existing=False")
                    return result
                
                # Step 2: Import name variations
                self._import_event_name_variations(event, ufc_event_data.event.name_variations)
                
                # Step 3: Import fights
                if ufc_event_data.fights:
                    fights_result = self._import_fights(event, ufc_event_data.fights)
                    result['fights'] = fights_result['fights']
                    result['errors'].extend(fights_result['errors'])
                
                # Step 4: Import bonus awards
                if ufc_event_data.bonus_awards:
                    bonus_result = self._import_bonus_awards(event, ufc_event_data.bonus_awards)
                    result['errors'].extend(bonus_result['errors'])
                
                # Step 5: Finalize import
                if not self.dry_run:
                    # Ensure transaction commits
                    pass
                else:
                    # In dry run, rollback the transaction
                    transaction.set_rollback(True)
                    logger.info("DRY RUN: Transaction rolled back")
                
                result['success'] = True
                result['statistics'] = self.stats.copy()
                
                logger.info(f"✅ Successfully imported {ufc_event_data.event.name}")
                
        except Exception as e:
            error_msg = f"Error importing event {ufc_event_data.event.name}: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            self.stats['errors'].append(error_msg)
        
        return result
    
    def _import_event(self, event_data) -> Tuple[Event, bool]:
        """Import event data into Event model"""
        
        # Check if event already exists
        existing_event = Event.find_by_name_variation(event_data.name)
        
        if existing_event and not self.update_existing:
            return existing_event, False
        
        # Prepare event data
        # Handle different date formats from Gemini
        try:
            # Try YYYY-MM-DD format first
            event_date = datetime.strptime(event_data.date, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try "Month DD, YYYY" format
                event_date = datetime.strptime(event_data.date, '%B %d, %Y').date()
            except ValueError:
                try:
                    # Try "Mon DD, YYYY" format
                    event_date = datetime.strptime(event_data.date, '%b %d, %Y').date()
                except ValueError:
                    logger.warning(f"Could not parse date '{event_data.date}', using default")
                    event_date = datetime.now().date()
        
        event_fields = {
            'organization': self.ufc_org,
            'name': clean_text_field(event_data.name, 255),
            'date': event_date,
            'location': clean_text_field(event_data.location or '', 255),
            'venue': clean_text_field(event_data.venue or '', 255),
            'city': clean_text_field(event_data.city or '', 100),
            'state': clean_text_field(event_data.state or '', 100),
            'country': clean_text_field(event_data.country or '', 100),
            'status': 'completed',  # Wikipedia events are completed
            'wikipedia_url': event_data.wikipedia_url,
        }
        
        # Add optional numeric fields
        if event_data.event_number:
            event_fields['event_number'] = event_data.event_number
        
        if event_data.attendance:
            event_fields['attendance'] = event_data.attendance
        
        if event_data.gate_revenue:
            event_fields['gate_revenue'] = Decimal(str(event_data.gate_revenue))
        
        if event_data.ppv_buys:
            event_fields['ppv_buys'] = event_data.ppv_buys
        
        if event_data.broadcast_info:
            event_fields['broadcast_info'] = event_data.broadcast_info
        
        if event_data.poster_url:
            event_fields['poster_url'] = event_data.poster_url
        
        # Create or update event
        if existing_event:
            # Update existing event
            for field, value in event_fields.items():
                if field != 'organization':  # Don't change organization
                    setattr(existing_event, field, value)
            
            existing_event.updated_at = timezone.now()
            if not self.dry_run:
                existing_event.save()
            
            return existing_event, False
        else:
            # Create new event
            event_fields['created_at'] = timezone.now()
            event_fields['updated_at'] = timezone.now()
            
            if not self.dry_run:
                event = Event.objects.create(**event_fields)
            else:
                # Create instance without saving for dry run
                event = Event(**event_fields)
                event.id = "dry-run-event-id"
            
            return event, True
    
    def _import_event_name_variations(self, event: Event, name_variations: List[str]):
        """Import event name variations"""
        logger.info(f"Event name variations received from Gemini: {name_variations}")
        logger.info(f"Total variations: {len(name_variations)}")
        
        if not name_variations:
            logger.warning("No name variations provided by Gemini!")
            return
            
        for i, variation in enumerate(name_variations):
            logger.info(f"  Variation {i+1}: '{variation}'")
            if variation.strip() and variation != event.name:
                try:
                    if not self.dry_run:
                        variation_obj, created = EventNameVariation.objects.get_or_create(
                            event=event,
                            name_variation=variation.strip(),
                            defaults={
                                'variation_type': 'wikipedia',
                                'source': 'wikipedia_scraper'
                            }
                        )
                        if created:
                            logger.info(f"  ✅ Created name variation: {variation}")
                        else:
                            logger.info(f"  ⏭️ Name variation already exists: {variation}")
                    else:
                        logger.info(f"  [DRY RUN] Would create name variation: {variation}")
                    
                except Exception as e:
                    logger.warning(f"Error adding name variation '{variation}': {e}")
            else:
                if variation == event.name:
                    logger.info(f"  ⏭️ Skipping variation identical to main name: {variation}")
                else:
                    logger.info(f"  ⏭️ Skipping empty variation: '{variation}'")
    
    def _import_fights(self, event: Event, fights_data: List[FightResultSchema]) -> Dict[str, Any]:
        """Import fight data"""
        result = {
            'fights': [],
            'errors': []
        }
        
        logger.info(f"Importing {len(fights_data)} fights for {event.name}")
        
        for fight_data in fights_data:
            try:
                fight_result = self._import_single_fight(event, fight_data)
                result['fights'].append(fight_result['fight'])
                result['errors'].extend(fight_result['errors'])
                
            except Exception as e:
                error_msg = f"Error importing fight {fight_data.fight_order}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
        
        return result
    
    def _import_single_fight(self, event: Event, fight_data: FightResultSchema) -> Dict[str, Any]:
        """Import a single fight"""
        result = {
            'fight': None,
            'participants': [],
            'errors': []
        }
        
        try:
            # Get or create weight class
            weight_class = self._get_or_create_weight_class(fight_data.weight_class)
            
            # Get or create fighters
            fighter1, _, f1_confidence = self.fighter_service.get_or_create_fighter(
                fight_data.fighter1, event_date=event.date
            )
            fighter2, _, f2_confidence = self.fighter_service.get_or_create_fighter(
                fight_data.fighter2, event_date=event.date
            )
            
            # Determine winner
            winner = None
            
            # Debug logging for winner determination
            logger.info(f"Fight {fight_data.fight_order}: {fighter1.get_full_name()} vs {fighter2.get_full_name()}")
            logger.info(f"  Winner name from Gemini: '{fight_data.winner_name}'")
            logger.info(f"  Fighter1 result: '{fight_data.fighter1.result}'")
            logger.info(f"  Fighter2 result: '{fight_data.fighter2.result}'")
            
            # Check if this is an upcoming fight (no results yet)
            is_upcoming_fight = (
                not fight_data.fighter1.result or fight_data.fighter1.result.strip() == '' or
                not fight_data.fighter2.result or fight_data.fighter2.result.strip() == '' or
                not fight_data.method or fight_data.method.strip() == ''
            )
            
            if is_upcoming_fight:
                logger.info(f"  This is an upcoming/scheduled fight - no winner assigned")
            elif fight_data.winner_name:
                if fight_data.winner_name.lower() in fighter1.get_full_name().lower():
                    winner = fighter1
                    logger.info(f"  Winner assigned via winner_name: {fighter1.get_full_name()}")
                elif fight_data.winner_name.lower() in fighter2.get_full_name().lower():
                    winner = fighter2
                    logger.info(f"  Winner assigned via winner_name: {fighter2.get_full_name()}")
                else:
                    logger.warning(f"  Winner name '{fight_data.winner_name}' doesn't match either fighter!")
            elif fight_data.fighter1.result == 'win':
                winner = fighter1
                logger.info(f"  Winner assigned via fighter1.result: {fighter1.get_full_name()}")
            elif fight_data.fighter2.result == 'win':
                winner = fighter2
                logger.info(f"  Winner assigned via fighter2.result: {fighter2.get_full_name()}")
            else:
                logger.warning(f"  No winner could be determined! Method: {fight_data.method}")
            
            logger.info(f"  Final winner: {winner.get_full_name() if winner else 'None (upcoming fight)' if is_upcoming_fight else 'None'}")
            
            # Create fight
            fight_fields = {
                'event': event,
                'weight_class': weight_class,
                'fight_order': fight_data.fight_order,
                'fight_section': clean_fight_section(fight_data.fight_section or ''),
                'is_main_event': fight_data.is_main_event,
                'is_title_fight': fight_data.is_title_fight,
                'scheduled_rounds': fight_data.scheduled_rounds,
                'status': 'completed',
                'winner': winner,
                'method': clean_text_field(fight_data.method or '', 50),
                'method_details': clean_text_field(fight_data.method_details or '', 255),
                'ending_round': fight_data.ending_round,
                'ending_time': clean_text_field(fight_data.ending_time or '', 15),
                'referee': clean_text_field(fight_data.referee or '', 100),
                'notes': fight_data.notes or ''  # TextField, no length limit
            }
            
            if not self.dry_run:
                fight = Fight.objects.create(**fight_fields)
            else:
                fight = Fight(**fight_fields)
                fight.id = f"dry-run-fight-{fight_data.fight_order}"
            
            result['fight'] = fight
            self.stats['fights_created'] += 1
            
            # Create fight participants
            participants_data = [
                (fighter1, 'red', fight_data.fighter1.result),
                (fighter2, 'blue', fight_data.fighter2.result)
            ]
            
            for fighter, corner, fight_result in participants_data:
                try:
                    participant_fields = {
                        'fight': fight,
                        'fighter': fighter,
                        'corner': corner,
                        'result': fight_result
                    }
                    
                    if not self.dry_run:
                        participant = FightParticipant.objects.create(**participant_fields)
                    else:
                        participant = FightParticipant(**participant_fields)
                    
                    result['participants'].append(participant)
                    self.stats['participants_created'] += 1
                    
                    logger.debug(f"Created participant: {fighter.get_full_name()} ({corner}, {fight_result})")
                    
                except Exception as e:
                    error_msg = f"Error creating participant for {fighter.get_full_name()}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
            
            logger.debug(f"Created fight: {fighter1.get_full_name()} vs {fighter2.get_full_name()}")
            
        except Exception as e:
            error_msg = f"Error creating fight: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
    
    def _import_bonus_awards(self, event: Event, bonus_data: List[BonusAwardSchema]) -> Dict[str, Any]:
        """Import bonus awards (placeholder - would need BonusAward model)"""
        result = {'errors': []}
        
        # Note: BonusAward model doesn't exist in current schema
        # This is a placeholder for future implementation
        logger.info(f"Would import {len(bonus_data)} bonus awards (model not implemented)")
        
        for bonus in bonus_data:
            logger.debug(f"Bonus: {bonus.award_type} - {bonus.fighter_name} (${bonus.amount})")
        
        return result
    
    def _get_or_create_weight_class(self, weight_class_name: str) -> Optional[WeightClass]:
        """Get or create weight class for UFC"""
        if not weight_class_name:
            return None
        
        try:
            # Try to find existing weight class
            weight_class = WeightClass.objects.filter(
                organization=self.ufc_org,
                name__iexact=weight_class_name
            ).first()
            
            if weight_class:
                return weight_class
            
            # Create new weight class with default weights
            weight_mappings = {
                'Flyweight': (125, 56.7),
                'Bantamweight': (135, 61.2),
                'Featherweight': (145, 65.8),
                'Lightweight': (155, 70.3),
                'Welterweight': (170, 77.1),
                'Middleweight': (185, 83.9),
                'Light Heavyweight': (205, 93.0),
                'Heavyweight': (265, 120.2),
                "Women's Strawweight": (115, 52.2),
                "Women's Flyweight": (125, 56.7),
                "Women's Bantamweight": (135, 61.2),
                "Women's Featherweight": (145, 65.8),
                'Openweight': (None, None),  # No weight limits for openweight
            }
            
            weight_lbs, weight_kg = weight_mappings.get(weight_class_name, (185, 83.9))
            gender = 'female' if "Women's" in weight_class_name else 'male'
            
            # Special handling for Openweight (no weight limits)
            if weight_class_name == 'Openweight':
                if not self.dry_run:
                    weight_class = WeightClass.objects.create(
                        organization=self.ufc_org,
                        name=weight_class_name,
                        weight_limit_lbs=None,
                        weight_limit_kg=None,
                        gender=gender,
                        is_active=False  # Openweight is inactive for modern events
                    )
                else:
                    weight_class = WeightClass(
                        organization=self.ufc_org,
                        name=weight_class_name,
                        weight_limit_lbs=None,
                        weight_limit_kg=None,
                        gender=gender,
                        is_active=False
                    )
            else:
                # Standard weight class with limits
                if not self.dry_run:
                    weight_class = WeightClass.objects.create(
                        organization=self.ufc_org,
                        name=weight_class_name,
                        weight_limit_lbs=weight_lbs,
                        weight_limit_kg=Decimal(str(weight_kg)),
                        gender=gender,
                        is_active=True
                    )
                else:
                    weight_class = WeightClass(
                        organization=self.ufc_org,
                        name=weight_class_name,
                        weight_limit_lbs=weight_lbs,
                        weight_limit_kg=Decimal(str(weight_kg)),
                        gender=gender,
                        is_active=True
                    )
            
            logger.info(f"Created weight class: {weight_class_name}")
            return weight_class
            
        except Exception as e:
            logger.error(f"Error getting/creating weight class '{weight_class_name}': {e}")
            return None
    
    def batch_import_events(self, events_data: List[UFCEventSchema]) -> Dict[str, Any]:
        """
        Import multiple UFC events in batch
        
        Args:
            events_data: List of structured UFC event data
            
        Returns:
            Batch import results and statistics
        """
        batch_result = {
            'total_events': len(events_data),
            'successful_imports': 0,
            'failed_imports': 0,
            'events': [],
            'overall_statistics': {},
            'errors': []
        }
        
        logger.info(f"Starting batch import of {len(events_data)} UFC events")
        
        for i, event_data in enumerate(events_data, 1):
            logger.info(f"Importing event {i}/{len(events_data)}: {event_data.event.name}")
            
            import_result = self.import_ufc_event(event_data)
            batch_result['events'].append(import_result)
            
            if import_result['success']:
                batch_result['successful_imports'] += 1
                logger.info(f"✅ Event {i} imported successfully")
            else:
                batch_result['failed_imports'] += 1
                logger.error(f"❌ Event {i} import failed")
                batch_result['errors'].extend(import_result['errors'])
        
        # Compile overall statistics
        batch_result['overall_statistics'] = self.stats.copy()
        batch_result['overall_statistics']['fighter_stats'] = self.fighter_service.get_statistics()
        
        success_rate = batch_result['successful_imports'] / len(events_data) * 100
        logger.info(
            f"Batch import completed: {batch_result['successful_imports']}/{len(events_data)} "
            f"events imported ({success_rate:.1f}% success rate)"
        )
        
        return batch_result
    
    def get_import_statistics(self) -> Dict[str, Any]:
        """Get current import statistics"""
        stats = self.stats.copy()
        stats['fighter_stats'] = self.fighter_service.get_statistics()
        return stats
    
    def reset_statistics(self):
        """Reset import statistics"""
        self.stats = {
            'events_created': 0,
            'events_updated': 0,
            'events_skipped': 0,
            'fights_created': 0,
            'participants_created': 0,
            'bonus_awards_created': 0,
            'errors': []
        }
        self.fighter_service.reset_statistics()