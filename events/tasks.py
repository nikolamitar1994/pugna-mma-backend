from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.db import transaction
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

from .models import Event, Fight, FightStatistics, Scorecard
from organizations.models import Organization
from fighters.models import Fighter, PendingFighter

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def discover_new_events(self, organization_id=None):
    """
    Discover new events from Wikipedia for specified organization(s).
    This is Phase 1 of the two-phase scraping approach.
    """
    try:
        if organization_id:
            organizations = Organization.objects.filter(id=organization_id, is_active=True)
        else:
            organizations = Organization.get_active_organizations()
        
        total_discovered = 0
        for org in organizations:
            logger.info(f"Discovering events for {org.name}")
            
            # Implementation would scrape Wikipedia category pages
            # This is a placeholder for the actual scraping logic
            discovered = discover_organization_events(org)
            total_discovered += discovered
            
        logger.info(f"Total events discovered: {total_discovered}")
        return {'discovered': total_discovered}
        
    except Exception as exc:
        logger.error(f"Error discovering events: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def scrape_event_details(self, event_id):
    """
    Scrape detailed event information from Wikipedia.
    This is Phase 2 of the two-phase scraping approach.
    """
    try:
        event = Event.objects.get(id=event_id)
        
        if event.processing_status == 'completed':
            logger.info(f"Event {event.name} already processed")
            return {'status': 'already_processed'}
        
        # Mark as processing
        event.processing_status = 'processing'
        event.save()
        
        # Scraping logic would go here
        # This is a placeholder
        logger.info(f"Processing event: {event.name}")
        
        # Simulate processing
        # In real implementation, this would:
        # 1. Scrape Wikipedia page
        # 2. Parse fight card
        # 3. Create Fight objects
        # 4. Create PendingFighter entries for unknown fighters
        
        # Mark as completed
        event.processing_status = 'completed'
        event.last_processed_at = timezone.now()
        event.save()
        
        # Trigger statistics scraping for completed events
        if event.status == 'completed':
            for fight in event.fights.filter(status='completed'):
                scrape_fight_statistics.delay(fight.id)
        
        return {'status': 'success', 'event': str(event)}
        
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return {'status': 'error', 'message': 'Event not found'}
    except Exception as exc:
        logger.error(f"Error processing event {event_id}: {exc}")
        
        # Mark as failed
        event.processing_status = 'failed'
        event.last_processing_error = str(exc)
        event.processing_attempts += 1
        event.save()
        
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True, max_retries=3)
def scrape_fight_statistics(self, fight_id):
    """
    Scrape detailed fight statistics from ufcstats.com or similar sources.
    """
    try:
        fight = Fight.objects.select_related('event__organization').get(id=fight_id)
        
        # Check if statistics already exist
        if hasattr(fight, 'statistics'):
            logger.info(f"Statistics already exist for fight {fight}")
            return {'status': 'already_exists'}
        
        logger.info(f"Scraping statistics for {fight}")
        
        # Implementation would scrape from ufcstats.com
        # This is a placeholder
        stats_data = scrape_stats_for_fight(fight)
        
        if stats_data:
            with transaction.atomic():
                # Create or update fight statistics
                stats, created = FightStatistics.objects.update_or_create(
                    fight=fight,
                    defaults=stats_data
                )
                
                # Calculate accuracies
                stats.calculate_accuracies()
                stats.save()
            
            return {'status': 'success', 'created': created}
        
        return {'status': 'no_data'}
        
    except Fight.DoesNotExist:
        logger.error(f"Fight {fight_id} not found")
        return {'status': 'error', 'message': 'Fight not found'}
    except Exception as exc:
        logger.error(f"Error scraping statistics for fight {fight_id}: {exc}")
        raise self.retry(exc=exc, countdown=600)  # Retry after 10 minutes


@shared_task(bind=True, max_retries=3)
def scrape_scorecards(self, fight_id):
    """
    Scrape judge scorecards from mmadecisions.com for decision fights.
    """
    try:
        fight = Fight.objects.select_related('event__organization').get(id=fight_id)
        
        # Only scrape for decision fights
        if not fight.is_decision():
            logger.info(f"Fight {fight} is not a decision, skipping scorecard scraping")
            return {'status': 'not_decision'}
        
        # Check if scorecards already exist
        if fight.scorecards.exists():
            logger.info(f"Scorecards already exist for fight {fight}")
            return {'status': 'already_exists'}
        
        logger.info(f"Scraping scorecards for {fight}")
        
        # Implementation would scrape from mmadecisions.com
        # This is a placeholder
        scorecard_data = scrape_scorecards_for_fight(fight)
        
        if scorecard_data:
            with transaction.atomic():
                created_count = 0
                for card_data in scorecard_data:
                    scorecard = Scorecard.objects.create(
                        fight=fight,
                        **card_data
                    )
                    created_count += 1
                
                # Update fight decision type based on scorecards
                update_fight_decision_type(fight)
            
            return {'status': 'success', 'created': created_count}
        
        return {'status': 'no_data'}
        
    except Fight.DoesNotExist:
        logger.error(f"Fight {fight_id} not found")
        return {'status': 'error', 'message': 'Fight not found'}
    except Exception as exc:
        logger.error(f"Error scraping scorecards for fight {fight_id}: {exc}")
        raise self.retry(exc=exc, countdown=600)


@shared_task
def update_recent_fight_results():
    """
    Check and update results for recent events that may have just completed.
    """
    try:
        # Look for events in the last 7 days that might need updates
        recent_date = timezone.now().date() - timedelta(days=7)
        recent_events = Event.objects.filter(
            date__gte=recent_date,
            status__in=['scheduled', 'live']
        )
        
        updated_count = 0
        for event in recent_events:
            # Check if event has completed
            if event.date < timezone.now().date():
                # Trigger full event scraping
                scrape_event_details.delay(event.id)
                updated_count += 1
        
        logger.info(f"Triggered updates for {updated_count} recent events")
        return {'updated': updated_count}
        
    except Exception as exc:
        logger.error(f"Error updating recent fight results: {exc}")
        raise


# Placeholder functions for actual scraping implementation
def discover_organization_events(org):
    """Placeholder for Wikipedia category scraping"""
    # In real implementation, this would:
    # 1. Scrape Wikipedia category page for the organization
    # 2. Extract event names and dates
    # 3. Create Event objects with status='discovered'
    return 0


def scrape_stats_for_fight(fight):
    """Placeholder for UFCStats scraping"""
    # In real implementation, this would:
    # 1. Build URL based on fight and organization
    # 2. Scrape the statistics page
    # 3. Parse and return statistics data
    return None


def scrape_scorecards_for_fight(fight):
    """Placeholder for MMADecisions scraping"""
    # In real implementation, this would:
    # 1. Search for the fight on mmadecisions.com
    # 2. Parse the scorecard data
    # 3. Return list of scorecard dictionaries
    return None


def update_fight_decision_type(fight):
    """Update fight decision type based on scorecards"""
    scorecards = fight.scorecards.all()
    if not scorecards:
        return
    
    # Count winner votes
    winner_votes = {}
    for card in scorecards:
        winner = card.scorecard_winner
        if winner:
            winner_votes[winner.id] = winner_votes.get(winner.id, 0) + 1
    
    total_judges = len(scorecards)
    if total_judges == 0:
        return
    
    # Determine decision type
    max_votes = max(winner_votes.values()) if winner_votes else 0
    
    if max_votes == total_judges:
        fight.decision_type = "Unanimous Decision"
        fight.is_unanimous_decision = True
    elif max_votes == total_judges - 1:
        fight.decision_type = "Majority Decision"
        fight.is_majority_decision = True
    else:
        fight.decision_type = "Split Decision"
        fight.is_split_decision = True
    
    fight.save()