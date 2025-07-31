from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from .models import Fighter, FighterStatistics, FighterRanking, PendingFighter
from .ranking_service import RankingCalculationService
from organizations.models import Organization, WeightClass

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_fighter_details(self, fighter_id):
    """
    Scrape detailed fighter information from Wikipedia and other sources.
    """
    try:
        fighter = Fighter.objects.get(id=fighter_id)
        
        logger.info(f"Scraping details for fighter: {fighter.get_full_name()}")
        
        # Implementation would scrape from Wikipedia
        # This is a placeholder for actual scraping logic
        
        # Update data quality score
        fighter.data_quality_score = fighter.calculate_data_quality()
        fighter.last_data_update = timezone.now()
        fighter.save()
        
        # Trigger statistics recalculation
        recalculate_fighter_stats.delay(fighter_id)
        
        return {'status': 'success', 'fighter': str(fighter)}
        
    except Fighter.DoesNotExist:
        logger.error(f"Fighter {fighter_id} not found")
        return {'status': 'error', 'message': 'Fighter not found'}
    except Exception as exc:
        logger.error(f"Error scraping fighter {fighter_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=2)
def recalculate_fighter_stats(self, fighter_id):
    """
    Recalculate all statistics for a fighter based on their fight history.
    """
    try:
        fighter = Fighter.objects.get(id=fighter_id)
        
        logger.info(f"Recalculating stats for: {fighter.get_full_name()}")
        
        # Get or create statistics object
        stats, created = FighterStatistics.objects.get_or_create(fighter=fighter)
        
        # Recalculate all statistics
        stats.calculate_all_statistics()
        
        # Update main fighter model stats for quick access
        fighter.total_fights = stats.total_fights
        fighter.wins = stats.wins
        fighter.losses = stats.losses
        fighter.draws = stats.draws
        fighter.no_contests = stats.no_contests
        fighter.wins_by_ko = stats.wins_ko
        fighter.wins_by_tko = stats.wins_tko
        fighter.wins_by_submission = stats.wins_submission
        fighter.wins_by_decision = stats.wins_decision
        fighter.save()
        
        return {'status': 'success', 'fighter': str(fighter), 'created': created}
        
    except Fighter.DoesNotExist:
        logger.error(f"Fighter {fighter_id} not found")
        return {'status': 'error', 'message': 'Fighter not found'}
    except Exception as exc:
        logger.error(f"Error calculating stats for fighter {fighter_id}: {exc}")
        raise self.retry(exc=exc, countdown=180)


@shared_task
def recalculate_all_fighter_stats():
    """
    Batch task to recalculate statistics for all fighters.
    Run periodically to ensure data consistency.
    """
    try:
        # Get fighters that need recalculation
        fighters = Fighter.objects.filter(
            statistics__needs_recalculation=True
        ) | Fighter.objects.filter(
            statistics__isnull=True
        )
        
        count = 0
        for fighter in fighters[:100]:  # Process 100 at a time
            recalculate_fighter_stats.delay(fighter.id)
            count += 1
        
        logger.info(f"Triggered stats recalculation for {count} fighters")
        return {'processed': count}
        
    except Exception as exc:
        logger.error(f"Error in batch stats recalculation: {exc}")
        raise


@shared_task(bind=True, max_retries=2)
def update_fighter_ranking(self, weight_class_id, organization_id=None):
    """
    Update rankings for a specific weight class and organization.
    """
    try:
        weight_class = WeightClass.objects.get(id=weight_class_id)
        
        if organization_id:
            organization = Organization.objects.get(id=organization_id)
        else:
            organization = weight_class.organization
        
        logger.info(f"Updating rankings for {weight_class} in {organization}")
        
        # Use ranking service to calculate rankings
        service = RankingCalculationService()
        updated = service.calculate_divisional_rankings(weight_class, organization)
        
        logger.info(f"Updated rankings for {updated} fighters")
        return {'status': 'success', 'updated': updated}
        
    except (WeightClass.DoesNotExist, Organization.DoesNotExist) as e:
        logger.error(f"Entity not found: {e}")
        return {'status': 'error', 'message': str(e)}
    except Exception as exc:
        logger.error(f"Error updating rankings: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def update_all_rankings():
    """
    Update rankings for all active weight classes across all organizations.
    """
    try:
        # Get all active weight classes
        weight_classes = WeightClass.objects.filter(
            is_active=True,
            organization__is_active=True
        )
        
        count = 0
        for wc in weight_classes:
            update_fighter_ranking.delay(wc.id)
            count += 1
        
        # Also update P4P rankings
        update_p4p_rankings.delay()
        
        logger.info(f"Triggered ranking updates for {count} weight classes")
        return {'weight_classes': count}
        
    except Exception as exc:
        logger.error(f"Error in batch ranking update: {exc}")
        raise


@shared_task
def update_p4p_rankings():
    """
    Update pound-for-pound rankings across all organizations.
    """
    try:
        organizations = Organization.get_active_organizations()
        
        for org in organizations:
            service = RankingCalculationService()
            updated = service.calculate_p4p_rankings(org)
            logger.info(f"Updated P4P rankings for {org}: {updated} fighters")
        
        return {'status': 'success'}
        
    except Exception as exc:
        logger.error(f"Error updating P4P rankings: {exc}")
        raise


@shared_task
def process_pending_fighters():
    """
    Process pending fighters discovered during event scraping.
    Attempt to find or create proper fighter records.
    """
    try:
        # Get unprocessed pending fighters
        pending = PendingFighter.objects.filter(
            is_processed=False,
            processing_attempts__lt=3
        )[:50]  # Process 50 at a time
        
        processed = 0
        created = 0
        
        for pf in pending:
            with transaction.atomic():
                pf.processing_attempts += 1
                
                # Try to find existing fighter
                fighter = pf.find_or_create_fighter()
                
                if fighter:
                    pf.matched_fighter = fighter
                    pf.is_processed = True
                    pf.processed_at = timezone.now()
                    processed += 1
                    
                    if pf.processing_notes.get('created'):
                        created += 1
                        # Trigger detail scraping for new fighters
                        scrape_fighter_details.delay(fighter.id)
                
                pf.save()
        
        logger.info(f"Processed {processed} pending fighters, created {created} new")
        return {'processed': processed, 'created': created}
        
    except Exception as exc:
        logger.error(f"Error processing pending fighters: {exc}")
        raise


@shared_task
def cleanup_old_pending_entities():
    """
    Clean up old pending entities that couldn't be processed.
    """
    try:
        # Delete pending entities older than 30 days with 3+ attempts
        cutoff_date = timezone.now() - timedelta(days=30)
        
        deleted = PendingFighter.objects.filter(
            created_at__lt=cutoff_date,
            processing_attempts__gte=3,
            is_processed=False
        ).delete()
        
        logger.info(f"Cleaned up {deleted[0]} old pending fighters")
        return {'deleted': deleted[0]}
        
    except Exception as exc:
        logger.error(f"Error cleaning up pending entities: {exc}")
        raise


@shared_task(bind=True, max_retries=3)
def complete_fighter_data_with_ai(self, fighter_id):
    """
    Use AI to complete missing fighter data.
    """
    try:
        fighter = Fighter.objects.get(id=fighter_id)
        
        # Check if fighter has sufficient data
        if fighter.data_quality_score >= 0.8:
            logger.info(f"Fighter {fighter} already has good data quality")
            return {'status': 'already_complete'}
        
        logger.info(f"Completing data for fighter: {fighter.get_full_name()}")
        
        # AI completion logic would go here
        # This is a placeholder
        
        # Update data source
        fighter.data_source = 'ai_completion'
        fighter.last_data_update = timezone.now()
        fighter.save()
        
        return {'status': 'success', 'fighter': str(fighter)}
        
    except Fighter.DoesNotExist:
        logger.error(f"Fighter {fighter_id} not found")
        return {'status': 'error', 'message': 'Fighter not found'}
    except Exception as exc:
        logger.error(f"Error completing fighter data: {exc}")
        raise self.retry(exc=exc, countdown=600)