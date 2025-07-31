import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings')

# Create the Celery app
app = Celery('mma_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Check for new events every day at 2 AM
    'discover-new-events': {
        'task': 'events.tasks.discover_new_events',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
    # Update fighter rankings every week on Sunday at 3 AM
    'update-fighter-rankings': {
        'task': 'fighters.tasks.update_all_rankings',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {
            'expires': 7200,
        }
    },
    # Check for fight result updates every 6 hours
    'update-recent-fight-results': {
        'task': 'events.tasks.update_recent_fight_results',
        'schedule': crontab(minute=0, hour='*/6'),
        'options': {
            'expires': 3600,
        }
    },
    # Clean up old pending entities weekly
    'cleanup-pending-entities': {
        'task': 'fighters.tasks.cleanup_old_pending_entities',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),
        'options': {
            'expires': 3600,
        }
    },
    # Update fighter statistics daily at 4 AM
    'update-fighter-statistics': {
        'task': 'fighters.tasks.recalculate_all_fighter_stats',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'expires': 7200,
        }
    },
}

# Celery configuration
app.conf.update(
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task routing for different queues
    task_routes={
        'events.tasks.scrape_event_details': {'queue': 'scraping'},
        'events.tasks.scrape_fight_statistics': {'queue': 'scraping'},
        'fighters.tasks.scrape_fighter_details': {'queue': 'scraping'},
        'events.tasks.scrape_scorecards': {'queue': 'scraping'},
        'fighters.tasks.update_fighter_ranking': {'queue': 'calculations'},
        'fighters.tasks.recalculate_fighter_stats': {'queue': 'calculations'},
        'content.tasks.process_ai_completion': {'queue': 'ai_processing'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'exchange_type': 'direct',
            'binding_key': 'default',
        },
        'scraping': {
            'exchange': 'scraping',
            'exchange_type': 'direct',
            'binding_key': 'scraping',
        },
        'calculations': {
            'exchange': 'calculations',
            'exchange_type': 'direct',
            'binding_key': 'calculations',
        },
        'ai_processing': {
            'exchange': 'ai_processing',
            'exchange_type': 'direct',
            'binding_key': 'ai_processing',
        },
    },
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """A debug task to test Celery is working."""
    print(f'Request: {self.request!r}')